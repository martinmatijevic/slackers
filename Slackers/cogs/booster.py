import io
import json

import discord
from discord.ext import commands

from utils.db_helper import get_all_runs, get_top_users, get_user_stats


def not_raidleader():
    async def predicate(ctx):
        raidleader_role = discord.utils.get(ctx.guild.roles, name="Raidleader")
        return (
            raidleader_role not in ctx.author.roles
        )  # Ensures user does NOT have the role

    return commands.check(predicate)


class BoosterCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["balance", "bal"])
    async def b(self, ctx, member: discord.Member = None):
        """Check balance and runs."""
        member = member or ctx.author  # Default to command sender if no mention
        balance, runs = get_user_stats(member.id)
        await ctx.send(
            f"This season {member.display_name} has boosted in {runs} runs and earned {balance} gold."
        )

    @commands.command()
    @not_raidleader()
    async def ban(self, ctx):
        """Big no no."""
        member = (
            ctx.message.mentions[0] if ctx.message.mentions else ctx.author
        )  # Use mentioned user or sender
        await ctx.send(
            f"Naughty boy {ctx.author.display_name}, your balance is now yoinked by {member.display_name}."
        )

    @commands.command(aliases=["runs", "boosts"])
    async def r(self, ctx, member: discord.Member = None):
        """Displays runs that the user participated in."""
        member = member or ctx.author  # Default to command sender if no mention
        user_id = str(member.id)  # Convert user ID to string for matching

        # Fetch all runs from the database
        runs = get_all_runs()

        # Filter runs where the user is in user_ids
        user_runs = [
            run
            for run in runs
            if user_id in json.loads(run[8])  # user_ids is at index 8
        ]

        if not user_runs:
            return await ctx.send(
                f"⚠️ {member.display_name}, you have not participated in any runs. Slacker!"
            )

        # Format the filtered runs
        formatted_runs = []
        for run in user_runs:
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

        response = "\n".join(formatted_runs)

        # If message is short, send directly in a code block
        if len(response) < 1490:
            return await ctx.send(f"```yaml\n{response}\n```")

        # Otherwise, save to a text file and send as an attachment
        file = io.StringIO(response)
        await ctx.send(
            f"📂 {member.display_name}, here are your runs:",
            file=discord.File(file, filename="all_runs.txt"),
        )

    @commands.command(aliases=["leaderboard", "top", "rank", "ranking", "rankings"])
    async def lb(self, ctx, stat: str = "balance", size: int = 5):
        """Returns the top users based on balance or runs."""
        # Map aliases
        if stat.lower() in ["b", "bal", "balance"]:
            stat = "balance"
            metric = "gold earned"
        elif stat.lower() in ["r", "runs"]:
            stat = "runs"
            metric = "runs done"
        else:
            await ctx.send("❌ Invalid category! Use `.lb balance` or `.lb runs`.")
            return

        # Ensure size is within a reasonable range
        size = max(1, min(size, 25))  # Limit between 1 and 25

        # Fetch top users
        top_users = get_top_users(stat, limit=size)

        if not top_users:
            await ctx.send("No data found.")
            return

        # Create leaderboard text
        leaderboard_text = "\n".join(
            [
                f"**#{i}** <@{user_id}> with **{value}** {metric}"
                for i, (user_id, value) in enumerate(top_users, start=1)
            ]
        )

        # Create embed
        embed = discord.Embed(
            title=f"🏆 Top {size} Slackers by {stat.capitalize()}",
            description=leaderboard_text,
            color=discord.Color.gold() if stat == "balance" else discord.Color.blue(),
        )

        await ctx.send(embed=embed)

    # Add more user-related commands here...


async def setup(bot):
    await bot.add_cog(BoosterCommands(bot))
