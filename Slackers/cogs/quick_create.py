import os
from datetime import datetime

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from utils.helper import is_raidleader

RAIDHELPER = os.getenv("RAIDHELPER")
SLACKERS_CATEGORY = int(os.getenv("SLACKERS_CATEGORY"))
SLACK_CATEGORY = int(os.getenv("SLACK_CATEGORY"))
SLACKERS_SERVER = int(os.getenv("SLACKERS_SERVER"))


class QuickCreate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def parse_title(self, title: str) -> tuple[str, str, int]:
        parts = title.lower().split()

        difficulty = None
        raid_type = None

        for diff in ["nm", "hc", "mythic"]:
            if diff in parts:
                difficulty = diff
                break

        for rtype in ["saved", "unsaved", "vip"]:
            if rtype in parts:
                raid_type = rtype
                break

        if not difficulty:
            difficulty = "nm"
        if not raid_type:
            raid_type = "vip"

        if raid_type == "vip" and difficulty in ["nm", "hc"]:
            template_id = 17
        elif raid_type == "unsaved":
            template_id = 18
        elif difficulty == "mythic" or raid_type == "saved":
            template_id = 19
        else:
            template_id = 17

        return difficulty, raid_type, template_id

    def format_channel_name(self, date: str, time: str, raid_type: str, difficulty: str, leader: int) -> str:
        dt = datetime.strptime(f"{date}-2025 {time}", "%d-%m-%Y %H:%M")
        weekday = dt.strftime("%a").lower()
        hhmm = dt.strftime("%H%M")
        leader_map = {780927857907335218: "warvet", 123823668265615360: "lovac", 288007755615436810: "lysaraa", 411655327411339274: "peki", 141634679479599104: "nopsu", 214790971949318144: "prophet", 872131738413985823: "sasha", 217331540810530816: "kyuuba", 251275420392095755: "santa", 174999930572767232: "undress"}
        return f"{weekday}-{hhmm}-{raid_type.lower()}-{difficulty.lower()}-{leader_map[leader]}"

    async def resolve_member(self, guild: discord.Guild, query: str) -> discord.Member | None:
        # Check if it looks like a mention
        if query.startswith("<@") and query.endswith(">"):
            try:
                user_id = int(query.strip("<@!>"))
                member = guild.get_member(user_id)
                if member:
                    return member
            except ValueError:
                pass

        # Try exact username
        for member in guild.members:
            if member.name == query or (member.nick and member.nick == query):
                return member

        # Try case-insensitive match
        lower_query = query.lower()
        for member in guild.members:
            if member.name.lower() == lower_query or (member.nick and member.nick.lower() == lower_query):
                return member

        return None

    async def create_raid_event(
        self,
        guild: discord.Guild,
        category: discord.CategoryChannel,
        title: str,
        date: str,
        time: str,
        leader: discord.Member,
        description: str = "12 UNSAVED boosters, 4 clients, 4 LBs",
    ) -> tuple[discord.TextChannel | None, str | None]:
        """
        Creates the channel and the Raid-Helper event via API.
        Returns (channel, error). If successful, error is None.
        """
        try:
            difficulty, raid_type, template_id = self.parse_title(title)
            channel_name = self.format_channel_name(date, time, raid_type, difficulty, leader.id)
            channel = await category.create_text_channel(channel_name)

            payload = {
                "leaderId": str(leader.id),
                "templateId": str(template_id),
                "date": date + "-2025",
                "time": time,
                "title": title,
                "description": description,
                "channelId": str(channel.id),
                "advancedSettings": {
                    "image": "https://wow.zamimg.com/optimized/guide-header-revamp/images/content/tall-headers/retail/categories/raids-manaforge-omega.jpg",
                },
            }

            headers = {"Authorization": RAIDHELPER, "Content-Type": "application/json"}

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"https://raid-helper.dev/api/v2/servers/{guild.id}/channels/{channel.id}/event",
                    headers=headers,
                    json=payload,
                ) as resp:
                    if resp.status == 200:
                        return channel, None
                    else:
                        error = await resp.text()
                        return None, f"{channel_name} ({resp.status}) {error}"

        except Exception as e:
            return None, str(e)

    @is_raidleader(must_have=True)
    @app_commands.command(name="createraid", description="Create a Raid-Helper event with channel")
    @app_commands.describe(
        title="Title, example: NM VIP",
        date="Date, example: 18-01",
        time="Time, example: 20:00",
        leader="Leader of the run",
        team="Slackers/Slack, default: Slackers",
        description="Description, example and default: 12 UNSAVED boosters, 4 clients, 4 LBs",
    )
    @app_commands.choices(
        team=[
            app_commands.Choice(name="Slackers", value="slackers"),
            app_commands.Choice(name="Slack", value="slack"),
        ],
    )
    @app_commands.guilds(SLACKERS_SERVER)
    async def createraid_slash(
        self,
        interaction: discord.Interaction,
        title: str,
        date: str,
        time: str,
        leader: discord.Member,
        team: str = "slackers",
        description: str = "12 UNSAVED boosters, 4 clients, 4 LBs",
    ):
        await interaction.response.defer(ephemeral=True)

        category = interaction.guild.get_channel(SLACKERS_CATEGORY)
        if team == "slack":
            category = interaction.guild.get_channel(SLACK_CATEGORY)
        if not category or not isinstance(category, discord.CategoryChannel):
            await interaction.followup.send("❌ Invalid category ID.")
            return

        channel, error = await self.create_raid_event(interaction.guild, category, title, date, time, leader, description)
        if channel:
            await interaction.followup.send(f"✅ Event created in {channel.mention}")
        else:
            await interaction.followup.send(f"❌ Failed to create event: {error}")

    @is_raidleader(must_have=True)
    @app_commands.command(name="masscreate", description="Create multiple Raid-Helper events at once")
    @app_commands.describe(
        entries="Multiple raid entries, one per line. Format: title;date;time;leader;description. Example: NM VIP;20-08;19:00;sky;description", team="Slackers/Slack, default: Slackers"
    )
    @app_commands.choices(
        team=[
            app_commands.Choice(name="Slackers", value="slackers"),
            app_commands.Choice(name="Slack", value="slack"),
        ],
    )
    @app_commands.guilds(SLACKERS_SERVER)
    async def masscreate_slash(
        self,
        interaction: discord.Interaction,
        entries: str,
        team: str = "slackers",
    ):
        await interaction.response.defer(ephemeral=True)

        category = interaction.guild.get_channel(SLACKERS_CATEGORY)
        if team == "slack":
            category = interaction.guild.get_channel(SLACK_CATEGORY)
        if not category or not isinstance(category, discord.CategoryChannel):
            await interaction.followup.send("❌ Invalid category ID.")
            return

        created, failed = [], []

        for idx, line in enumerate(entries.split("|"), 1):
            line = line.strip()
            if not line:
                continue
            try:
                parts = [p.strip() for p in line.split(";")]
                if len(parts) < 4:
                    failed.append(f"Line {idx}: Invalid format `{line}`")
                    continue

                title, date, time, leader_query = parts[:4]
                description = parts[4] if len(parts) > 4 else "12 UNSAVED boosters, 4 clients, 4 LBs"

                # Resolve leader
                leader = await self.resolve_member(interaction.guild, leader_query)
                if not leader:
                    failed.append(f"Line {idx}: Could not find leader `{leader_query}`")
                    continue

                channel, error = await self.create_raid_event(interaction.guild, category, title, date, time, leader, description)
                if channel:
                    created.append(channel.mention)
                else:
                    failed.append(f"Line {idx}: ❌ {error}")

            except Exception as e:
                failed.append(f"Line {idx}: ❌ Exception `{line}`: {e}")

        msg = f"✅ Created {len(created)} events.\n" + "\n".join(created)
        if failed:
            msg += f"\n❌ Failed {len(failed)}:\n" + "\n".join(failed)

        await interaction.followup.send(msg)


async def setup(bot):
    await bot.add_cog(QuickCreate(bot))
