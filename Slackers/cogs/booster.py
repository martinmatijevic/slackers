import io
import json
import locale

import discord
from discord.ext import commands
from discord.utils import get

from utils.db_helper import get_all_runs, get_run_by_date_time, get_top_users, get_user_stats
from utils.format_helper import format_runs
from utils.helper import get_next_date_from_day

locale.setlocale(locale.LC_ALL, "de_DE.UTF-8")


def not_raidleader():
    async def predicate(ctx):
        raidleader_role = get(ctx.guild.roles, name="Raidleader")
        return raidleader_role not in ctx.author.roles  # Ensures user does NOT have the role

    return commands.check(predicate)


class Slacker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def wakey(self, ctx):
        """Wakey wakey."""
        await ctx.send("Work work work!")

    @commands.command()
    @not_raidleader()
    async def ban(self, ctx, member: discord.Member = None):
        """
        Bans booster.

        Arguments:
            member : @booster (optional)
                The member to ban. If not provided, you will ban yourself.

        Example:
            .ban @username
            .ban
        """

        member = member or ctx.author  # Default to command sender if no mention
        if member == ctx.author:
            await ctx.send(f"You trying to ban yourself {ctx.author.display_name}? Your balance is now 0.")
            await ctx.send("<:peepoloser:1353363668003328220>")
        else:
            await ctx.send(f"Naughty boy {ctx.author.display_name}, your balance is now yoinked by {member.display_name}.")
            await ctx.send("<:peepoloser:1353363668003328220>")

    @commands.command(aliases=["balance", "bal"])
    async def b(self, ctx, member: discord.Member = None):
        """
        Displays balance and number of runs the user participated in.

        Arguments:
            member : @booster (optional)
                The member to check balance/runs. If not provided, the command will apply to yourself.

        Example:
            .b @username
            .b
        """

        member = member or ctx.author  # Default to command sender if no mention
        balance, runs = get_user_stats(member.id)
        if member != ctx.author:
            if balance == 0:
                await ctx.send(
                    f"This season {member.display_name} has boosted in {runs} runs and earned {locale.format_string('%.2f', balance, grouping=True)} gold. Slacker!"
                )
                await ctx.send("<:deadgesus:1346463122814402611>")
            else:
                await ctx.send(
                    f"This season {member.display_name} has boosted in {runs} runs and earned {locale.format_string('%.2f', balance, grouping=True)} gold."
                )
        else:
            if balance == 0:
                await ctx.send(f"This season you boosted in {runs} runs and earned {locale.format_string('%.2f', balance, grouping=True)} gold. Slacker!")
                await ctx.send("<:deadgesus:1346463122814402611>")
            else:
                await ctx.send(f"This season you boosted in {runs} runs and earned {locale.format_string('%.2f', balance, grouping=True)} gold.")

    @commands.command(aliases=["runs", "boosts"])
    async def r(self, ctx, member: discord.Member = None):
        """
        Displays runs that the user participated in. If too long, sends as a .txt file.

        Arguments:
            member : @booster (optional)
                The member to check runs. If not provided, the command will apply to yourself.

        Example:
            .r @username
            .r
        """

        member = member or ctx.author  # Default to command sender if no mention

        # Fetch all runs from the database
        runs = get_all_runs()

        # Filter runs where the user is in user_ids
        user_runs = [run for run in runs if str(member.id) in json.loads(run[8]).keys()]  # user_ids is at index 8

        if not user_runs:
            if member != ctx.author:
                await ctx.send(f"⚠️ {member.display_name} has not participated in any runs. Slacker!")
                return await ctx.send("<:deadgesus:1346463122814402611>")
            else:
                await ctx.send("⚠️ you have not participated in any runs. Slacker!")
                return await ctx.send("<:deadgesus:1346463122814402611>")

        response = format_runs(user_runs)

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
        """
        Returns the top users based on balance or runs.

        Arguments:
            stat : str (optional)
                What to rank by. Accepted values:
                - "balance", "bal", or "b" → shows top by gold earned (default)
                - "runs" or "r" → shows top by number of runs
            size : int (optional)
                How many users to show (1–25). Default is 5.

        Example:
            .lb
            .lb balance
            .lb runs 10
            .lb r 25
        """

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
                f"**#{i}** <@{user_id}> with **{locale.format_string('%.2f', value, grouping=True)}** {metric}"
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

    @commands.command()
    async def info(self, ctx):
        """Finds the scheduled run based on the channel name and formats the info."""
        channel_name = ctx.channel.name  # Example: "fri-1700-vip"

        is_raidleader = get(ctx.author.roles, name="Raidleader") is not None

        try:
            parts = channel_name.split("-")
            day_str, time_str = parts[0], parts[1]  # Extract "fri", "1700"

            run_date = get_next_date_from_day(day_str)
            run_time = f"{time_str[:2]}:{time_str[2:]}"  # Convert "1700" -> "17:00"

            if not run_date:
                await ctx.send("Invalid day format in channel name.")
                return

            run = get_run_by_date_time(run_date, run_time)

            if run:
                run_id, _, _, _, _, rl_id, gc_id, community = run

                if is_raidleader:
                    if community == "Dawn":
                        if rl_id in [123823668265615360, 361259804695461889, 780927857907335218]:
                            response = (
                                f"<@{rl_id}> tell <@{gc_id}> to visit https://hub.dawn-boosting.com/bookings/raids/{run_id} "
                                f"find actual_pot and use `.dawn {run_id} actual_pot` since you are banned in Dawn retard"
                            )
                        else:
                            response = (
                                f"<@{rl_id}> visit https://hub.dawn-boosting.com/bookings/raids/{run_id} "
                                f"find actual_pot and use `.dawn {run_id} actual_pot`"
                            )
                    elif community == "OBC":
                        response = (
                            f"<@{rl_id}> visit https://oblivion-marketplace.com/#/booking/raid/overview/leaderandgc "
                            f"find your run, pot and use `.obc {run_id} pot`"
                        )
                    else:
                        response = f"Run found for community {community}, but no specific instructions."
                else:
                    if community == "Dawn":
                        link = "https://discord.com/channels/1006174254284423299/1190322948763025428"
                        partial = "eu"
                    elif community == "OBC":
                        link = "https://discord.com/channels/817565728965525534/817565730530525198"
                        partial = ""
                    response = (
                        f"This is a {community} run and RL is <@{rl_id}>. "
                        f"Make sure to join discord.gg/{community.lower()}{partial} and apply for raider here {link}. "
                        f"After that open ticket here https://discord.com/channels/1095649559738318948/1307830422432120842 "
                        f"so we can sort you out quickly."
                    )
                await ctx.send(response)

            else:
                await ctx.send("No matching run found.")

        except Exception as e:
            await ctx.send(f"Error: {e}")

    # Add more user-related commands here...


async def setup(bot):
    await bot.add_cog(Slacker(bot))
