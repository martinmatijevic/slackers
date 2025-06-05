import datetime
import re

import aiohttp

DEBUG_CHANNEL_ID = 1367637512750759987


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


def diff_to_type_dawn(difficulty):
    if difficulty == "NM":
        team_type = "NM Teams"
    elif difficulty == "HC":
        team_type = "HC Teams"
    elif difficulty == "MM":
        team_type = "MythicTeam"
    else:
        team_type = "Unknown Team"  # Default if no match
    return team_type


def diff_to_type_obc(difficulty):
    if difficulty == "NM":
        team_type = "Normal"
    elif difficulty == "HC":
        team_type = "Heroic"
    elif difficulty == "MM":
        team_type = "Mythic"
    else:
        team_type = "Unknown Team"  # Default if no match
    return team_type


def loot_to_type(loot_type):
    if loot_type == "Saved":
        raid_type = "Saved"
    elif loot_type == "Unsaved":
        raid_type = "Unsaved"
    elif loot_type == "VIP":
        raid_type = "VIP"
    else:
        raid_type = "Unknown Loot Type"  # Default if no match
    return raid_type


def get_gc_cut_obc_str(raid_type: str) -> str:
    gc_cut_mapping = {"Saved": "3/10", "Unsaved": "2/10", "VIP": "2/10"}
    return gc_cut_mapping.get(raid_type, "2/10")  # Default to 2/10 if not found


def extract_mentions(message):
    mention_pattern = r"<@(\d+)>"
    mentions = re.findall(mention_pattern, message)
    return [int(mention) for mention in mentions]


# Mapping short day names to full names
DAY_MAPPING = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def get_next_date_from_day(day_str: str) -> str:
    today = datetime.date.today()
    target_weekday = DAY_MAPPING.get(day_str.lower())

    if target_weekday is None:
        return None  # Invalid day abbreviation

    days_until_target = (target_weekday - today.weekday() + 7) % 7
    if days_until_target == 0:  # If today is the same weekday, return today
        days_until_target = 0

    target_date = today + datetime.timedelta(days=days_until_target)
    return target_date.strftime("%d/%m/%Y")


def process_args(args, author_id):
    if not args:  # Handle case when there are no arguments
        return [], {}, False, False  # Default values

    co_lead_boosters = []  # Stores boosters getting co-lead cut (-cl)
    modified_cuts = {}  # Stores {booster_id: new_cut} for -bc
    no_raid_leader_cut = False  # True if there's no RL cut (-rl)
    no_gold_collector_cut = False  # True if there's no GC cut (-gc)
    cl_present = False  # Track if -cl was used

    i = 0
    while i < len(args):
        arg = args[i]

        # Detect -cl and save mentions until another flag appears
        if arg == "-cl":
            cl_present = True  # Mark that -cl was used
            i += 1
            while i < len(args) and not args[i].startswith("-"):
                if args[i].startswith("<@") and args[i].endswith(">"):
                    user_id = args[i].strip("<@!>")  # Extract numeric ID
                    if user_id.isdigit():
                        co_lead_boosters.append(int(user_id))
                i += 1
            continue  # Ensure it doesn't skip processing after exiting loop

        # Detect -bc and save booster_id + new_cut pairs
        elif arg == "-bc":
            i += 1
            while i < len(args) - 1:  # Ensure we have a pair
                if args[i].startswith("<@") and args[i].endswith(">"):
                    user_id = args[i].strip("<@!>")  # Extract numeric ID
                    if user_id.isdigit() and args[i + 1].isdigit():  # Next value must be an integer
                        modified_cuts[int(user_id)] = int(args[i + 1])
                        i += 1  # Skip the integer since it's paired
                elif args[i].startswith("-"):  # Stop at next flag
                    break
                i += 1
            continue  # Ensure it doesn't skip processing after exiting loop

        # Detect -rl (no raid leader cut)
        elif arg == "-rl":
            no_raid_leader_cut = True

        # Detect -gc (no gold collector cut)
        elif arg == "-gc":
            no_gold_collector_cut = True

        i += 1  # Move to the next argument

    # If -cl was used but no mentions, add command author
    if cl_present and not co_lead_boosters:
        co_lead_boosters.append(author_id)

    # Ensure -rl is True if -cl list has boosters
    if co_lead_boosters:
        no_raid_leader_cut = True

    return co_lead_boosters, modified_cuts, no_raid_leader_cut, no_gold_collector_cut


async def fetch_current():
    url = "https://data.wowtoken.app/v2/current/retail.json"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()
