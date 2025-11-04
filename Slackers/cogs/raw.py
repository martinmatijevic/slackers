import os
import re

import discord
from discord import app_commands
from discord.ext import commands

from utils.format_helper import format_mentions_dawn
from utils.helper import parse_raw_msg, is_raidleader_raw
from utils.renaming_helper import loot_to_type, diff_to_type_dawn
from utils.cuts_helper import sort_raw_cuts

LOGS = int(os.getenv("LOGS"))
OWNER = int(os.getenv("OWNER"))
RAW_SERVER = int(os.getenv("RAW_SERVER"))
RL = int(os.getenv("RAW_RL"))
GC = int(os.getenv("RAW_GC"))
ATD = int(os.getenv("ATD"))

class Raw(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @is_raidleader_raw(must_have=True)
    @app_commands.command(name="attendance", description="Attendance Raw.")
    @app_commands.describe(
        run_id="Raid ID from community website",
        pot="Pot of the run from community website (you can write it as 1000k or 1000000)",
        rl_cut="What does RL want to do with RL cut?",
        gc_cut="What does GC want to do with GC cut?",
        booster_count="Manually set boosters boss count",
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
    @app_commands.guilds(RAW_SERVER)
    async def attendance_slash(
        self,
        interaction: discord.Interaction,
        run_id: str,
        pot: str,
        rl_cut: str = "keep",
        gc_cut: str = "keep",
        booster_count: str = None,
    ):
        try:
            await interaction.response.defer(thinking=True)
            await interaction.guild.chunk()
            date_str, time_str, type_, diff, booster_ids = await parse_raw_msg(interaction.channel)

            rl_cut_bool = rl_cut == "keep"
            gc_cut_bool = gc_cut == "keep"

            difficulty = diff_to_type_dawn(diff.lower())
            run_type = loot_to_type(type_.lower())

            pot_value = int(pot.lower().replace("k", "")) * 1000 if "k" in pot.lower() else int(pot)
            mention_dict = {mention_id: 8 for mention_id in booster_ids}

            changed_cuts = {}
            if booster_count:
                matches = re.findall(r"<@!?(\d+)>\s+(\d+)", booster_count)
                changed_cuts = {int(uid): int(value) for uid, value in matches}

            merged_dict = {**mention_dict, **changed_cuts}

            mentions_str = format_mentions_dawn(merged_dict, [], RL, rl_cut_bool)

            gc_str = "X" if not gc_cut_bool else GC

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
                await interaction.user.send(f"**Mentioned Users:**\n{mention_message}\n**Dawn ATD channel:{discord_channel}:**\n{formatted_message}")

            # Send DM to you (always)
            owner = await self.bot.fetch_user(OWNER)
            if owner:
                await owner.send(
                    f"**Mentioned Users:**\n{mention_message}\n**Invoked by:** {interaction.user.mention}\n**ATD for {discord_channel}:**\n{formatted_message}"
                )
            
            channel = self.bot.get_channel(ATD)
            if channel:
                await channel.send(f"{formatted_message}")

            booster_cut = sort_raw_cuts(difficulty, run_type, pot_value, merged_dict, not rl_cut_bool, not gc_cut_bool)
            if booster_cut:
                await interaction.followup.send(f"Cut for this run was roughly {f'{booster_cut:,}'.replace(',', '.')} gold.")

        except Exception as e:
            await interaction.response.send_message(f"Error: {e}")


async def setup(bot):
    cog = Raw(bot)
    await bot.add_cog(cog)
