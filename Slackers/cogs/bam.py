import os
import re

import discord
from discord import app_commands
from discord.ext import commands

from utils.format_helper import format_date_time, format_mentions_dawn
from utils.helper import get_booster_ids, get_gc_string, is_raidleader_bam, parse_co_leaders, parse_raid_helper_embeds
from utils.renaming_helper import loot_to_type

LOGS = int(os.getenv("LOGS"))
OWNER = int(os.getenv("OWNER"))
BAM_SERVER = int(os.getenv("BAM_SERVER"))


class Bam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @is_raidleader_bam(must_have=True)
    @app_commands.command(name="bam", description="Attendance Bam.")
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
    @app_commands.guilds(BAM_SERVER)
    async def bam_slash(
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
            leader, run_date, run_time, _, type_, community, booster_names = await parse_raid_helper_embeds(interaction.channel)
            booster_ids = get_booster_ids(booster_names, interaction.guild)

            rl_cut_bool = rl_cut == "keep"
            gc_cut_bool = gc_cut == "keep"

            co_leaders_ids = parse_co_leaders(co_leaders)
            if co_leaders_ids:
                rl_cut_bool = False

            difficulty = "HC Teams"
            run_type = loot_to_type(type_.lower())
            date_str, time_str = format_date_time(run_date, run_time, community)

            pot_value = int(pot.replace("k", "")) * 1000 if "k" in pot.lower() else int(pot)
            mention_dict = {mention_id: 8 for mention_id in booster_ids}

            changed_cuts = {}
            if booster_count:
                matches = re.findall(r"<@!?(\d+)>\s+(\d+)", booster_count)
                changed_cuts = {int(uid): int(value) for uid, value in matches}

            merged_dict = {**mention_dict, **changed_cuts}

            mentions_str = format_mentions_dawn(merged_dict, co_leaders_ids, leader, rl_cut_bool)
            for key in co_leaders_ids:
                if key in merged_dict:
                    merged_dict[key] *= 1.2

            gc_str = get_gc_string(gc_cut_bool, gold_collector, community, run_type)

            # Final formatted message
            formatted_message = f"```\n{date_str}\n{time_str}\n{difficulty}\n{run_type}\n{pot_value}\n" f"{mentions_str}\n{gc_str}\n{run_id}```"

            mention_details = []
            for mention, value in merged_dict.items():
                user = await self.bot.fetch_user(int(mention))
                if user:
                    mention_details.append(f"{user.id} - {user.mention} - {value}")
                else:
                    mention_details.append(f"{mention} - (Unknown User) - {value}")

            discord_channel = "https://discord.com/channels/1129393746123964476/1231972793139331246"
            mention_message = "\n".join(mention_details)
            if interaction.user.id != OWNER:
                await interaction.user.send(f"**Mentioned Users:**\n{mention_message}\n**ATD for {discord_channel}:**\n{formatted_message}")

            # Send DM to you (always)
            owner = await self.bot.fetch_user(OWNER)
            if owner:
                await owner.send(
                    f"**Mentioned Users:**\n{mention_message}\n**Invoked by:** {interaction.user.mention}\n**ATD for {discord_channel}:**\n{formatted_message}"
                )
            await interaction.followup.send("ATD posted.")

        except Exception as e:
            await interaction.response.send_message(f"Error: {e}")


async def setup(bot):
    cog = Bam(bot)
    await bot.add_cog(cog)
