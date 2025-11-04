import os
import re
from collections import defaultdict
from datetime import datetime

import aiohttp
import discord
from discord import app_commands

from utils.renaming_helper import diff_to_type_dawn, diff_to_type_obc

SLACKERS = int(os.getenv("SLACKERS_CATEGORY"))
SLACK = int(os.getenv("SLACK_CATEGORY"))
RL = int(os.getenv("RL"))
RH = int(os.getenv("RH"))
DEBUG_CHANNEL_ID = int(os.getenv("DEBUG_CHANNEL_ID"))
RL2 = int(os.getenv("RL2"))
RL3 = int(os.getenv("RL3"))
RL4 = int(os.getenv("RL4"))
OWNER = int(os.getenv("OWNER"))

category_id = {
    "slackers": SLACKERS,
    #"slack": SLACK,
}


def is_raidleader(must_have: bool = True):
    def predicate(interaction: discord.Interaction) -> bool:

        has_role = any(role.id == RL for role in interaction.user.roles)
        return has_role == must_have

    return app_commands.check(predicate)


def is_raidleader_bam(must_have: bool = True):
    def predicate(interaction: discord.Interaction) -> bool:

        has_role = any(role.id == RL2 for role in interaction.user.roles)
        if interaction.user.id == OWNER:
            has_role = True
        return has_role == must_have

    return app_commands.check(predicate)


def is_raidleader_raw(must_have: bool = True):
    def predicate(interaction: discord.Interaction) -> bool:

        has_role = any(role.id in [RL3, RL4] for role in interaction.user.roles)
        if interaction.user.id == OWNER:
            has_role = True
        return has_role == must_have

    return app_commands.check(predicate)


def is_app_owner():
    async def predicate(interaction: discord.Interaction) -> bool:
        return await interaction.client.is_owner(interaction.user)

    return app_commands.check(predicate)


async def log_debug(bot, message: str):
    channel = bot.get_channel(DEBUG_CHANNEL_ID)
    if channel:
        await channel.send(f"[DEBUG] {message}")


async def send_batched_logs(bot, log_func, log_lines, max_length=2000):
    if not log_lines:
        return

    batch = ""
    for line in log_lines:
        if len(batch) + len(line) + 1 > max_length:
            await log_func(bot, batch)
            batch = line
        else:
            batch += ("\n" if batch else "") + line

    if batch:
        await log_func(bot, batch)


def format_slash_args(interaction):
    if not hasattr(interaction, "namespace") or not interaction.namespace:
        return ""
    params = [f"{name}={value}" for name, value in vars(interaction.namespace).items() if value is not None]
    return " " + " ".join(params) if params else ""


def get_gc_cut_obc_str(raid_type: str) -> str:
    gc_cut_mapping = {"Saved": "3/10", "Unsaved": "2/10", "VIP": "2/10"}
    return gc_cut_mapping.get(raid_type, "2/10")  # Default to 2/10 if not found


def extract_mentions(message):
    mention_pattern = r"<@(\d+)>"
    mentions = re.findall(mention_pattern, message)
    return [int(mention) for mention in mentions]


async def fetch_current():
    url = "https://data.wowtoken.app/v2/current/retail.json"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()


async def parse_raid_helper_embeds(channel: discord.TextChannel, bot_id: int = RH):
    first_msg = None
    latest_msg = None
    async for message in channel.history(limit=2000, oldest_first=True):
        if message.author.id == bot_id:
            if not first_msg:
                first_msg = message
            if message.mentions:
                latest_msg = message

    if not first_msg or not latest_msg:
        raise ValueError("No messages from target bot found.")

    # Extract from first message
    embed = first_msg.embeds[0]
    leader = None
    date = None
    time = None
    title = None
    if not embed.title and embed.description:
        bold_match = re.search(r"\*\*(.*?)\*\*", embed.description)
        if bold_match:
            bold_content = bold_match.group(1)
            emote_names = re.findall(r"<:([^:]+):\d+>", bold_content)
            result = [name if name != "empty" else " " for name in emote_names]
            title = "".join(result)
    else:
        title = embed.title
    parts = title.strip().split()
    difficulty = parts[0] if len(parts) >= 1 else "Unknown"
    run_type = parts[1] if len(parts) >= 2 else "Unknown"
    community = parts[2] if len(parts) >= 3 and parts[2].lower() in ["dawn", "obc"] else "Dawn"
    if community.lower() == "dawn":
        community = "Dawn"
    elif community.lower() == "obc":
        community = "OBC"

    for field in embed.fields:
        val = field.value
        if "leaderx" in val.lower() and "date" in val.lower():
            leader_match = re.search(r"<@!?(?P<id>\d+)>", val)
            if leader_match:
                leader = int(leader_match.group("id"))

            date_match = re.search(r"<t:(\d+):d>", val.lower())
            if date_match:
                timestamp = int(date_match.group(1))
                dt = datetime.fromtimestamp(timestamp)
                date = dt.strftime("%d/%m")
                time = dt.strftime("%H:%M")

    # Extract from latest message
    embed = latest_msg.embeds[0]
    booster_names = []

    for field in embed.fields:
        lines = field.value.strip().splitlines()
        for line in lines:
            if "<:emote:1295290973294952468>" in line:
                continue  # skip unwanted emote

            match = re.search(r"<:emote:\d+>\s+(\S+)", line)
            if match:
                booster_names.append(match.group(1))
    return leader, date, time, difficulty, run_type, community, booster_names

# --- regex definitions ---
HEADER_REGEX = re.compile(
    r".*?(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+"
    r"(\d{2}/\d{2})\s+(\d{2}:\d{2})\s+"
    r"(SAVED|UNSAVED|VIP)\s+"
    r"(NORMAL|HEROIC|MYTHIC)"
)

SECTION_REGEX = re.compile(r".*\b(tank|healer|dps)\b", re.IGNORECASE)
STOP_REGEX = re.compile(r".*\b(lb|loot ?body)", re.IGNORECASE)
BOOSTER_REGEX = re.compile(r"<@!?(\d+)>")

async def parse_raw_msg(channel: discord.TextChannel, limit: int = 2000):
    async for message in channel.history(limit=limit):
        if not message.content:
            continue

        lines = message.content.splitlines()
        if not lines:
            continue

        # --- find header line anywhere ---
        header_index = None
        for i, line in enumerate(lines):
            header_match = HEADER_REGEX.search(line)
            if header_match:
                header_index = i
                break

        if header_index is None:
            continue  # no header in this message

        # extract header parts
        _, date, time, type_, difficulty = header_match.groups()

        boosters = []
        in_valid_section = False

        # --- parse boosters only from the header line onward ---
        for line in lines[header_index + 1:]:
            # stop at LB/Lootbody/etc
            if STOP_REGEX.match(line.strip()):
                break

            # check if line is a role section
            if SECTION_REGEX.match(line.strip()):
                in_valid_section = True
                continue

            # grab booster IDs
            if in_valid_section:
                match = BOOSTER_REGEX.search(line)
                if match:
                    boosters.append(int(match.group(1)))

        return date, time, type_, difficulty, boosters

    return None

def get_booster_ids(booster_names: list[str], guild: discord.Guild):
    booster_ids = []

    for name in booster_names:
        lowered_name = name.lower()
        # Try to match by full name first
        member = discord.utils.find(lambda m: m.name.lower() == lowered_name or m.display_name.lower() == lowered_name, guild.members)
        # If not found, try truncated match
        if not member:
            member = discord.utils.find(lambda m: m.name.lower().startswith(lowered_name) or m.display_name.lower().startswith(lowered_name), guild.members)

        if member:
            booster_ids.append(member.id)

    return booster_ids


async def purge_channel(channel: discord.TextChannel, limit: int = 10):
    try:
        deleted = await channel.purge(limit=limit)
        return len(deleted)
    except discord.Forbidden:
        print(f"Missing permissions to purge messages in #{channel.name}")
        return 0
    except Exception as e:
        print(f"Error purging messages in #{channel.name}: {e}")
        return 0


def parse_event_description(event: discord.ScheduledEvent):
    leader_match = re.search(r"<:LeaderX:\d+>\s*<@(\d+)>", event.description)
    leader_id = int(leader_match.group(1)) if leader_match else None
    signups_match = re.search(r"\*\*(\d+)\*\*", event.description)
    signups = int(signups_match.group(1)) if signups_match else None
    return leader_id, signups


def create_event_embed_block(events, category_key: str, date: datetime.date = None):
    event_lines = []

    for event in events:
        try:
            name = event.name
            timestamp = f"<t:{int(event.start_time.timestamp())}:F>"
            if date:
                timestamp = f"<t:{int(event.start_time.timestamp())}:t>"
            timestamp2 = f"<t:{int(event.start_time.timestamp())}:R>"
            leader_id, signups = parse_event_description(event)
            leader_tag = f"<@{leader_id}>" if leader_id else "Unknown"

            # Extract channel URL from location
            pattern = r"https://discord\.com/channels/(\d+)/(\d+)"
            match = re.match(pattern, event.location or "")
            channel_url = event.location if match else ""

            line = f"**[{name}]({channel_url})** - {leader_tag} - {timestamp} - {timestamp2} - {signups}"
            event_lines.append(line)

        except Exception as e:
            print(f"Error formatting event {getattr(event, 'name', '?')}: {e}")
            event_lines.append(f"`{event.name}` - ❌ Failed to parse")

    if date:
        formatted_title = f"{date.strftime('%A, %d %B %Y')} - Schedule for {category_key.capitalize()}"
    else:
        formatted_title = f"Schedule for {category_key.capitalize()}"

    embed = discord.Embed(
        title=formatted_title,
        description="\n".join(event_lines) if event_lines else "No runs found.",
        color=discord.Color.gold(),
    )
    embed.set_footer(text="Times shown here are localized to your timezone.")
    return embed


def build_event_embed_from_list(events, category_key: str):
    embeds = []

    if len(events) < 10:
        # Single block embed
        embed = create_event_embed_block(events, category_key)
        embeds.append(embed)
    else:
        # Group by date
        events_by_day = defaultdict(list)
        for event in events:
            try:
                date = event.start_time.date()
                events_by_day[date].append(event)
            except Exception as e:
                print(f"Error grouping event {getattr(event, 'name', '?')}: {e}")

        for event_date in sorted(events_by_day.keys()):
            grouped_events = events_by_day[event_date]
            embed = create_event_embed_block(grouped_events, category_key, date=event_date)
            embeds.append(embed)

    return embeds


def get_category_from_event_location(guild: discord.Guild, event: discord.ScheduledEvent):
    pattern = r"https://discord\.com/channels/(\d+)/(\d+)/(\d+)"
    match = re.match(pattern, event.location) if event.location else None
    if not match:
        return None

    _, channel_id, _ = map(int, match.groups())
    channel = guild.get_channel(channel_id)
    if hasattr(channel, "category") and channel.category:
        return f"{channel.category.id}"
    return None


async def sort_events_by_category(guild: discord.Guild):
    events = await guild.fetch_scheduled_events()

    if not events:
        print("No scheduled events found.")
        return None

    events = sorted(events, key=lambda e: int(e.start_time.timestamp()), reverse=False)

    slackers = []
    slack = []

    for event in events:
        if event.entity_type == discord.EntityType.external:
            value = int(get_category_from_event_location(guild, event)) or "Unknown"
            if value == category_id["slackers"]:
                slackers.append(event)
            elif value == category_id["slack"]:
                slack.append(event)
            else:
                print(f"Event '{event.name}' does not match known categories.")
    return slackers, slack


def parse_co_leaders(co_leaders_str: str):
    """Extract IDs and mention strings for co-leaders."""
    co_leaders_ids = []
    if co_leaders_str:
        user_ids = re.findall(r"<@!?(\d+)>", co_leaders_str)
        co_leaders_ids = [int(uid) for uid in user_ids]
    return co_leaders_ids


def get_difficulty(diff: str, community: str):
    """Get difficulty string based on community type."""
    if community.lower() == "obc":
        return diff_to_type_obc(diff.lower())
    return diff_to_type_dawn(diff.lower())


def get_gc_string(gc_cut_bool, gold_collector: discord.Member, community: str, run_type: str):
    """Format the GC string depending on community."""
    if community.lower() == "obc":
        return "" if not gc_cut_bool else f"<@{gold_collector.id}> {get_gc_cut_obc_str(run_type)}"
    return "X" if not gc_cut_bool else gold_collector.id
