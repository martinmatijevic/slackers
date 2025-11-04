import os
import re

import discord
from discord import app_commands
from discord.ext import commands
import aiohttp

from utils.db_helper import add_run, remove_run
from utils.format_helper import format_date_time, format_mentions_dawn, format_mentions_obc
from utils.helper import get_booster_ids, get_difficulty, get_gc_string, is_raidleader, parse_co_leaders, parse_raid_helper_embeds, purge_channel
from utils.renaming_helper import loot_to_type

LOGS = int(os.getenv("LOGS"))
OWNER = int(os.getenv("OWNER"))
SLACKERS_SERVER = int(os.getenv("SLACKERS_SERVER"))
SLACKERS_CATEGORY = int(os.getenv("SLACKERS_CATEGORY"))


class RaidLeader(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @is_raidleader(must_have=True)
    @commands.command(name="parse")
    async def parse(self, ctx, gc_id, *, block: str):
        # --- clean up accidental backticks or language hints ---
        block = block.strip()
        block = re.sub(r"^```[a-zA-Z0-9]*\n?", "", block)  # remove opening ```
        block = re.sub(r"```$", "", block)  # remove closing ```
        block = block.strip()

        lines = [line.strip() for line in block.splitlines() if line.strip()]

        try:
            date = lines[0]
            time = lines[1]
            difficulty = lines[2]
            raid_type = lines[3]
            pot = lines[4]
            boosters_line = lines[5]
            gc_id = lines[6]
            run_id = lines[7]
        except IndexError:
            await ctx.send("❌ Invalid block format, missing some lines.")
            return

        # --- parse boosters ---
        boosters = {}
        rl_id = None
        rl_cut_shared = True

        for entry in boosters_line.split(","):
            entry = entry.strip()
            if not entry:
                continue

            parts = entry.split(":")
            try:
                user_id = int(parts[0])
                number = int(parts[1]) if parts[1].isdigit() else 0
                boosters[user_id] = number

                if len(parts) > 2 and "lead" in parts[2]:
                    rl_id = user_id
                    rl_cut_shared = False
            except (ValueError, IndexError):
                continue

        # --- fallback GC ID ---
        gc_cut_shared = False
        if gc_id.upper() == "X":
            gc_cut_shared = True
        else:
            try:
                gc_id = int(gc_id)
            except ValueError:
                gc_id = None

        booster_cut = add_run(
            self.bot,
            run_id,
            date,
            time,
            difficulty,
            raid_type,
            int(pot),
            rl_id,
            gc_id,
            boosters,
            "Dawn",
            rl_cut_shared,
            gc_cut_shared,
        )
        if booster_cut:
            print(booster_cut)
    
    @is_raidleader(must_have=True)
    @app_commands.command(name="atd", description="Creates ATD and updates balances.")
    @app_commands.describe(
        run_id="Raid ID from community website",
        pot="Pot of the run from community website (you can write it as 1000k or 1000000)",
        gold_collector="Slacker that collected gold",
        rl_cut="What does RL want to do with RL cut?",
        gc_cut="What does GC want to do with GC cut?",
        co_leaders="Slacker you want to mark as your co-leader (20% more cut)",
        booster_count="Manually set Slackers boss count",
    )
    @app_commands.choices(
        rl_cut=[
            app_commands.Choice(name="Keep RL cut", value="keep"),
            app_commands.Choice(name="Share RL cut", value="share"),
        ],
        gc_cut=[
            app_commands.Choice(name="Keep GC cut", value="keep"),
            app_commands.Choice(name="Share GC cut", value="share"),
        ],
    )
    @app_commands.guilds(SLACKERS_SERVER)
    async def atd_slash(
        self,
        interaction: discord.Interaction,
        run_id: str,
        pot: str,
        gold_collector: discord.Member,
        rl_cut: str = "keep",
        gc_cut: str = "keep",
        co_leaders: str = None,
        booster_count: str = None,
    ):
        try:
            await interaction.response.defer(thinking=True)
            await interaction.guild.chunk()
            leader, run_date, run_time, diff, type_, community, booster_names = await parse_raid_helper_embeds(interaction.channel)
            booster_ids = get_booster_ids(booster_names, interaction.guild)

            rl_cut_bool = rl_cut == "keep"
            gc_cut_bool = gc_cut == "keep"

            co_leaders_ids = parse_co_leaders(co_leaders)
            if co_leaders_ids:
                rl_cut_bool = False

            difficulty = get_difficulty(diff, community)
            run_type = loot_to_type(type_.lower())
            date_str, time_str = format_date_time(run_date, run_time, community)

            pot_value = int(pot.lower().replace("k", "")) * 1000 if "k" in pot.lower() else int(pot)
            mention_dict = {mention_id: 8 for mention_id in booster_ids}

            changed_cuts = {}
            if booster_count:
                matches = re.findall(r"<@!?(\d+)>\s+(\d+)", booster_count)
                changed_cuts = {int(uid): int(value) for uid, value in matches}

            merged_dict = {**mention_dict, **changed_cuts}

            if community.lower() == "dawn":
                mentions_str = format_mentions_dawn(merged_dict, co_leaders_ids, leader, rl_cut_bool)
                for key in co_leaders_ids:
                    if key in merged_dict:
                        merged_dict[key] *= 1.2
            else:
                mentions_str = format_mentions_obc(merged_dict, leader, rl_cut_bool)

            gc_str = get_gc_string(gc_cut_bool, gold_collector, community, run_type)

            # Final formatted message
            if community.lower() == "obc":
                title = f"Type of Boost: Slackers {difficulty} {run_type}"
                leader_cut = "LeaderCut: TO_POT" if not rl_cut_bool else "LeaderCut: TO_LEADER"
                logs = "Logs: https://www.warcraftlogs.com/"
                pot_str = f"Pot: {pot_value // 1000}k" if pot_value % 1000 == 0 else str(pot_value)
                formatted_message = f"```\n{title}\n{date_str}\n{time_str}\n{pot_str}\n{leader_cut}\n{logs}\n" f"Run ID: {run_id}\n{mentions_str}\n{gc_str}```"
            else:
                formatted_message = f"```\n{date_str}\n{time_str}\n{difficulty}\n{run_type}\n{pot_value}\n" f"{mentions_str}\n{gc_str}\n{run_id}```"

            mention_details = []
            for mention, value in merged_dict.items():
                user = await self.bot.fetch_user(int(mention))
                if user:
                    mention_details.append(f"{user.id} - {user.mention} - {value}")
                else:
                    mention_details.append(f"{mention} - (Unknown User) - {value}")

            discord_channel = "https://discord.com/channels/1129393746123964476/1231972793139331246"
            if community == "OBC":
                discord_channel = "https://discord.com/channels/817565728965525534/1177052051939795036"
            mention_message = "\n".join(mention_details)
            if interaction.user.id != OWNER:
                await interaction.user.send(f"**Mentioned Users:**\n{mention_message}\n**ATD for {discord_channel}:**\n{formatted_message}")

            # Send DM to you (always)
            owner = await self.bot.fetch_user(OWNER)
            if owner:
                await owner.send(
                    f"**Mentioned Users:**\n{mention_message}\n**Invoked by:** {interaction.user.mention}\n**ATD for {discord_channel}:**\n{formatted_message}"
                )

            if interaction.channel.category_id == SLACKERS_CATEGORY:
                booster_cut = add_run(
                    self.bot,
                    run_id,
                    run_date,
                    run_time,
                    difficulty,
                    run_type,
                    pot_value,
                    leader,
                    gold_collector.id,
                    merged_dict,
                    community,
                    rl_cut_shared=not rl_cut_bool,
                    gc_cut_shared=not gc_cut_bool,
                )
                if booster_cut:
                    channel = self.bot.get_channel(LOGS)
                    if channel:
                        await channel.send(
                            f"Cut for {run_date} {run_time} {difficulty} {run_type} in {community} was roughly {f'{booster_cut:,}'.replace(',', '.')} gold."
                        )
                    await interaction.followup.send(f"Cut for this run was roughly {f'{booster_cut:,}'.replace(',', '.')} gold.")
            else:
                await interaction.followup.send(f"ATD for {run_date} {run_time} {difficulty} {run_type} in {community} posted.")
        except Exception as e:
            await interaction.followup.send(f"Error: {e}")

    @is_raidleader(must_have=True)
    @app_commands.command(name="purge", description="Delete messages in this channel.")
    @app_commands.describe(count="How many messages to delete (default 10)")
    @app_commands.guilds(SLACKERS_SERVER)
    async def purge_slash(self, interaction: discord.Interaction, count: int = 10):
        await interaction.response.defer(ephemeral=True)

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.followup.send("This command can only be used in text channels.", ephemeral=True)
            return

        deleted_count = await purge_channel(channel, limit=count)
        await interaction.followup.send(f"Deleted {deleted_count} messages.", ephemeral=True)

    @is_raidleader(must_have=True)
    @app_commands.command(name="removerun", description="Removes a run from the database and removes balances.")
    @app_commands.describe(id="Raid ID from community website")
    @app_commands.guilds(SLACKERS_SERVER)
    async def removerun_slash(self, interaction: discord.Interaction, id: str):
        success = remove_run(id, self.bot)

        if success:
            await interaction.response.send_message(f"✅ Run with ID `{id}` has been removed.")
        else:
            await interaction.response.send_message(f"❌ No run found with ID: `{id}`")

    @is_raidleader(must_have=True)
    @app_commands.command(name="yoink", description="Yoink an emote from a URL and add it to the server.")
    @app_commands.describe(
        name="Name for the new emote",
        url="Direct URL to the emoji (supports animated .gif or .webp)"
    )
    @app_commands.guilds(SLACKERS_SERVER)
    async def yoink_slash(self, interaction: discord.Interaction, name: str, url: str):
        await interaction.response.defer(thinking=True)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return await interaction.followup.send("❌ Could not download image from the URL.")
                    data = await response.read()

            is_animated = url.lower().endswith(".gif") or "animated=true" in url.lower()

            emoji = await interaction.guild.create_custom_emoji(name=name, image=data, reason=f"Added by {interaction.user}")

            emoji_display = f"<a:{emoji.name}:{emoji.id}>" if is_animated else f"<:{emoji.name}:{emoji.id}>"
            await interaction.followup.send(f"✅ Added emote {emoji_display}")

        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to add emojis.")
        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ Failed to create emoji: {e}")
        except Exception as e:
            await interaction.followup.send(f"⚠️ Unexpected error: {e}")

    # Add more raid leader related commands here...


async def setup(bot):
    cog = RaidLeader(bot)
    await bot.add_cog(cog)
