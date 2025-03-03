import io
import json

import discord
from discord.ext import commands

from utils.db_helper import get_all_runs, get_all_users, reset_dbs


class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def wakey(self, ctx):
        """Wakey wakey."""
        await ctx.send("Work work work!")

    @commands.command()
    @commands.is_owner()
    async def resetdb(self, ctx):
        """Reset the databases."""
        reset_dbs()
        await ctx.send("Database has been fully reset!")

    @commands.command()
    @commands.is_owner()
    async def allusers(self, ctx):
        """Show all user stats."""
        users = get_all_users()
        if not users:
            await ctx.send("No users found in the database.")
            return

        table = "```User ID            | Balance | Runs\n" + "-" * 35 + "\n"
        for user_id, balance, runs in users:
            table += f"{user_id:<15} | {balance:<7} | {runs}\n"
        table += "```"

        # Ensure message doesn't exceed Discord's 2000-character limit
        if len(table) < 1490:
            return await ctx.send(table)

        # Otherwise, save to a text file and send as an attachment
        file_path = "all_users.txt"
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(table)
        await ctx.send(
            "📂 The users list is too long. Here's a file instead:",
            file=discord.File(file_path),
        )

    @commands.command()
    @commands.is_owner()
    async def allruns(self, ctx):
        """Displays all stored runs."""
        runs = get_all_runs()
        if not runs:
            await ctx.send("No runs found in the database.")
            return

        formatted_runs = []
        for run in runs:
            (
                run_id,
                run_date,
                run_time,
                difficulty,
                rtype,
                pot,
                rl_id,
                gc_id,
                user_ids,
            ) = run
            user_ids = json.loads(user_ids)  # Convert JSON string back to a list

            formatted_runs.append(
                f"📌 Run ID: {run_id}\n"
                f"📅 Date: {run_date} | ⏰ Time: {run_time}\n"
                f"🎮 Difficulty: {difficulty} | Type: {rtype}\n"
                f"💰 Pot: {pot}\n"
                f"🆔 RL ID: {rl_id} | GC ID: {gc_id}\n"
                f"👥 Users: {', '.join(map(str, user_ids))}\n"
                f"{'-'*40}"
            )
        # Join all runs together
        response = "\n".join(formatted_runs)

        # Ensure message doesn't exceed Discord's 2000-character limit
        if len(response) < 1490:
            return await ctx.send(f"```yaml\n{response}\n```")

        # Otherwise, save to a text file and send as an attachment
        file = io.StringIO(response)
        await ctx.send(
            "📂 The run list is too long. Here's a file instead:",
            file=discord.File(file, filename="all_runs.txt"),
        )

    # Add more admin-related commands here...


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
