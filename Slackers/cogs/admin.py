import io

import discord
from discord.ext import commands

from utils.db_helper import get_all_runs, get_all_users, reset_dbs, reset_sc
from utils.format_helper import format_runs, format_users


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def resetdb(self, ctx):
        """Reset the databases."""
        reset_dbs()
        await ctx.send("Database has been fully reset!")

    @commands.command()
    @commands.is_owner()
    async def resetschedule(self, ctx):
        """Reset the schedule database."""
        reset_sc()
        await ctx.send("Schedule has been fully reset!")

    @commands.command()
    @commands.is_owner()
    async def allusers(self, ctx):
        """Show all user stats. If too long, sends as a .txt file."""
        users_data = get_all_users()
        if not users_data:
            await ctx.send("No users found in the database.")
            return

        users_list = await format_users(self.bot, ctx.guild.id, users_data)

        if len(users_list) > 2000:
            users_list = users_list.strip("```")
            file = io.StringIO(users_list)  # Use in-memory file
            await ctx.send(
                "📂 The users list is too long. Here's a file instead:",
                file=discord.File(file, filename="all_users.txt"),
            )
        else:
            await ctx.send(users_list)

    @commands.command()
    @commands.is_owner()
    async def allruns(self, ctx):
        """Displays all stored runs. If too long, sends as a .txt file."""
        runs = get_all_runs()
        if not runs:
            await ctx.send("No runs found in the database.")
            return

        response = format_runs(runs)

        if len(response) > 2000:
            file = io.StringIO(response)  # Use in-memory file
            await ctx.send(
                "📂 The run list is too long. Here's a file instead:",
                file=discord.File(file, filename="all_runs.txt"),
            )
        else:
            await ctx.send(f"```yaml\n{response}\n```")

    # Add more admin-related commands here...


async def setup(bot):
    await bot.add_cog(Admin(bot))
