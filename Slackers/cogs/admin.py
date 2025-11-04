import io
import os

import discord
from discord import app_commands
from discord.ext import commands

from utils.db_helper import get_all_runs, get_all_users, reset_dbs
from utils.format_helper import format_runs, format_users
from utils.helper import is_app_owner

SLACKERS_SERVER = int(os.getenv("SLACKERS_SERVER"))


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @is_app_owner()
    @app_commands.command(name="resetdb", description="Reset the databases.")
    @app_commands.guilds(SLACKERS_SERVER)
    async def resetdb_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        reset_dbs()
        await interaction.followup.send("All current season databases have been fully reset!")

    @is_app_owner()
    @app_commands.command(name="allusers", description="Show all user stats. Sends a file if too long.")
    @app_commands.describe(season="Which season to check (defaults to current)")
    @app_commands.choices(season=[app_commands.Choice(name="Current", value="TWW-S3"), app_commands.Choice(name="TWW S2", value="TWW-S2")])
    @app_commands.guilds(SLACKERS_SERVER)
    async def allusers_slash(self, interaction: discord.Interaction, season: app_commands.Choice[str] = None):
        await interaction.response.defer()
        season = season.value if season else "TWW-S3"
        users_data = get_all_users(season)
        if not users_data:
            await interaction.followup.send(f"No users found in the {season} database.")
            return

        users_list = await format_users(self.bot, interaction.guild.id, users_data)

        if len(users_list) > 2000:
            users_list = users_list.strip("```")
            file = io.StringIO(users_list)
            await interaction.followup.send(
                f"📂 The {season} users list is too long. Here's a file instead:",
                file=discord.File(file, filename="all_users.txt"),
            )
        else:
            await interaction.followup.send(users_list)

    @is_app_owner()
    @app_commands.command(name="allruns", description="Displays all stored runs. Sends a file if too long.")
    @app_commands.describe(season="Which season to check (defaults to current)")
    @app_commands.choices(season=[app_commands.Choice(name="Current", value="TWW-S3"), app_commands.Choice(name="TWW S2", value="TWW-S2")])
    @app_commands.guilds(SLACKERS_SERVER)
    async def allruns_slash(self, interaction: discord.Interaction, season: app_commands.Choice[str] = None):
        await interaction.response.defer()
        season = season.value if season else "TWW-S3"
        runs = get_all_runs(season)
        if not runs:
            await interaction.followup.send(f"No runs found in the {season} database.")
            return

        response = format_runs(runs)

        if len(response) > 2000:
            file = io.StringIO(response)
            await interaction.followup.send(
                f"📂 The {season} run list is too long. Here's a file instead:",
                file=discord.File(file, filename="all_runs.txt"),
            )
        else:
            await interaction.followup.send(f"```yaml\n{response}\n```")

    @is_app_owner()
    @app_commands.command(name="deletechannel", description="Delete this channel.")
    @app_commands.guilds(SLACKERS_SERVER)
    async def deletechannel_slash(self, interaction: discord.Interaction):
        channel = interaction.channel
        await interaction.response.send_message("Deleting this channel...", ephemeral=True)
        await channel.delete(reason=f"Deleted by {interaction.user} using /deletechannel")

    # Add more admin related commands here...


async def setup(bot):
    await bot.add_cog(Admin(bot))
