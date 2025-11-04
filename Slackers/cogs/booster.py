import io
import json
import os
from datetime import datetime
import random
import discord
from discord import app_commands
from discord.ext import commands
from io import StringIO

from utils.db_helper import get_all_runs, get_top_users, get_user_stats
from utils.emojis import LOSER_EMOTE, NO_RUNS_EMOTE, NOT_STONKS_EMOTE, STONKS_EMOTE, WAITING_EMOTE
from utils.format_helper import format_duration, format_runs
from utils.helper import fetch_current, is_raidleader
from utils.aliases import ALIASES
from utils.wa import liquid_wa, liquid_anchors, liquid_manaforge, ns_addon, ns_anchors, ns_anchors1080, ns_manaforge

old_price = 0
old_time = None

SLACKERS_SERVER = int(os.getenv("SLACKERS_SERVER"))


class Booster(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="avatar", description="Get a Slacker avatar")
    @app_commands.describe(user="Slacker to check (optional, defaults to yourself)")
    @app_commands.guilds(SLACKERS_SERVER)
    async def avatar_slash(self, interaction: discord.Interaction, user: discord.User = None):
        try:
            member = user or interaction.user

            # Get guild-specific avatar if it exists
            guild_avatar = None
            if (member_obj := interaction.guild.get_member(member.id)):
                guild_avatar = member_obj.guild_avatar

            # Determine which avatar to use for link/display
            avatar_to_use = guild_avatar or member.display_avatar

            # Prepare links
            links = ["png", "jpg"]
            if avatar_to_use.is_animated():  # Add gif only if animated
                links.append("gif")

            # Build link strings
            link_strings = [
                f"[{fmt}]({avatar_to_use.with_format(fmt).with_size(4096).url})"
                for fmt in links
            ]

            # Build embed
            embed = discord.Embed(
                title=f"{member.display_name}'s avatar",
                color=discord.Color.orange()
            )
            embed.add_field(name="Link as", value=" | ".join(link_strings), inline=False)
            embed.set_image(url=avatar_to_use.with_size(4096).url)

            await interaction.response.send_message(embed=embed)
        
        except Exception as e:
            print(e)


    @app_commands.command(name="banner", description="Get a Slacker banner")
    @app_commands.describe(user="Slacker to check (optional, defaults to yourself)")
    @app_commands.guilds(SLACKERS_SERVER)
    async def banner_slash(self, interaction: discord.Interaction, user: discord.User = None):
        try:
            member = user or interaction.user

            # Fetch full user object to get banner
            fetched = await self.bot.fetch_user(member.id)
            banner_asset = fetched.banner

            if not banner_asset:
                await interaction.response.send_message(f"{member.display_name} has no banner.")
                return

            # Determine available formats
            links = ["png", "jpg"]
            if banner_asset.is_animated():
                links.append("gif")

            # Build link strings
            link_strings = [
                f"[{fmt}]({banner_asset.with_format(fmt).with_size(1024).url})"
                for fmt in links
            ]

            # Build embed
            embed = discord.Embed(
                title=f"{member.display_name}'s banner",
                color=discord.Color.orange()
            )
            embed.add_field(name="Link as", value=" | ".join(link_strings), inline=False)
            embed.set_image(url=banner_asset.with_size(1024).url)

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            print(e)

    @app_commands.command(name="slacker", description="Get a random Slacker failure")
    @app_commands.guilds(SLACKERS_SERVER)
    async def slacker_slash(self, interaction: discord.Interaction):
        alias, url = random.choice(list(ALIASES.items()))
        await interaction.response.send_message(f"🎬 {alias}: {url}")

    @app_commands.command(name="liquid", description="Get Liquid WA package")
    @app_commands.guilds(SLACKERS_SERVER)
    async def liquid_slash(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        embed = discord.Embed(
            title="Liquid WeakAura Package",
            description=(
                "This package contains **3 WeakAura imports**.\n\n"
                "If you are using NorthernSky in your guild: \n"
                "- For the **Manaforge WA**, go to the **Load tab** → scroll down → "
                "find **'Not Player Name/Realm'** → enter your main **name-realm** that uses the NorthernSky package.\n"
                "_Your NorthernSky WAs will be disabled automatically in-game, you don't need to touch them._"
            ),
            color=0x00BFFF
        )
        embed.add_field(name="📄 liquid_manaforge", value=liquid_manaforge, inline=False)
        embed.add_field(name="📄 liquid_anchors", value=liquid_anchors, inline=False)
        embed.add_field(name="📄 liquid_wa", value=liquid_wa, inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="ns", description="Get NorthernSky WA package")
    @app_commands.guilds(SLACKERS_SERVER)
    async def ns_slash(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        embed = discord.Embed(
            title="NS WeakAura Package",
            description=(
                "This package contains **2 WeakAura imports** and **NorthernSky Addon**.\n\n"
                "If you are using Liquid in your guild: \n"
                "- For the **Manaforge WA**, go to the **Load tab** → scroll down → "
                "find **'Not Player Name/Realm'** → enter your main **name-realm** that uses the Liquid package.\n"
                "_Your Liquid WAs will be disabled automatically in-game, you don't need to touch them._"
            ),
            color=0x00BFFF
        )
        embed.add_field(name="📄 ns_addon", value=ns_addon, inline=False)
        embed.add_field(name="📄 ns_manaforge", value=ns_manaforge, inline=False)
        embed.add_field(name="📄 ns_anchors1440", value=ns_anchors, inline=False)
        embed.add_field(name="📄 ns_anchors1080", value=ns_anchors1080, inline=False)
        embed.set_footer(text="There is two versions of NS Anchors - for 1080p and 1440p monitors.")

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="token", description="Displays current EU token value.")
    @app_commands.describe(amount="Number of tokens to check (default 1)")
    @app_commands.guilds(SLACKERS_SERVER)
    async def token_slash(self, interaction: discord.Interaction, amount: int = 1):
        global old_price, old_time
        amount_int = int(amount)

        if amount_int < 1:
            await interaction.response.send_message("❌ Please provide a valid positive number of tokens (e.g., /token 3).")
            return

        if amount_int > 10000:
            await interaction.response.send_message("Bitch you ain't got that much gold.")
            return

        try:
            data = await fetch_current()
            current_price = data["eu"][1]
            current_time = datetime.now()

            if old_time is None:
                old_time = current_time

            diff_time = current_time - old_time

            token_count = amount_int
            total_new = current_price * token_count
            total_old = old_price * token_count
            diff = total_new - total_old
            percent = ((diff / total_old) * 100) if total_old != 0 else 0
            duration_str = format_duration(diff_time.total_seconds())

            # Determine change text and emoji thumbnail URL
            if diff > 0:
                change_str = f"+{format(diff, ',').replace(',', '.')} 🪙 ({percent:.2f}%)"
                thumbnail_url = NOT_STONKS_EMOTE
            elif diff < 0:
                change_str = f"{format(diff, ',').replace(',', '.')} 🪙 ({percent:.2f}%)"
                thumbnail_url = STONKS_EMOTE
            else:
                change_str = "no change"
                thumbnail_url = WAITING_EMOTE

            price_str = format(total_new, ",").replace(",", ".")
            token_label = f"{token_count} x " if token_count > 1 else ""

            embed = discord.Embed(
                title="💰 EU Token Price",
                description=f"{token_label}Token Price: **{price_str}** 🪙",
                color=discord.Color.gold(),
            )
            embed.add_field(name="\u200b", value=f"**Change:** {change_str}", inline=False)
            embed.set_footer(text=f"Checked: {duration_str} ago")
            embed.set_thumbnail(url=thumbnail_url)

            await interaction.response.send_message(embed=embed)

            old_price = current_price
            old_time = current_time
        except Exception as e:
            await interaction.response.send_message("❌ Error fetching EU token data.")
            print(e)

    @app_commands.command(name="wakey", description="Wakey wakey.")
    @app_commands.guilds(SLACKERS_SERVER)
    async def wakey_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message("Work work work!")

    @is_raidleader(must_have=False)
    @app_commands.command(name="ban", description="Bans Slacker.")
    @app_commands.describe(member="Slacker you want to ban")
    @app_commands.guilds(SLACKERS_SERVER)
    async def ban_slash(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user

        if member == interaction.user:
            description = f"You trying to ban yourself {interaction.user.display_name}? Your balance is now 0."
        else:
            description = f"Naughty boy {interaction.user.display_name}, your balance is now yoinked by {member.display_name}."

        embed = discord.Embed(title="🚫 Slacker Banned", description=description, color=discord.Color.red())
        embed.set_thumbnail(url=LOSER_EMOTE)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="balance", description="Displays balance and number of runs the Slacker participated in.")
    @app_commands.describe(member="Slacker to check (optional, defaults to yourself)", season="Which season to check (defaults to current)")
    @app_commands.choices(season=[app_commands.Choice(name="Current", value="TWW-S3"), app_commands.Choice(name="TWW S2", value="TWW-S2")])
    @app_commands.guilds(SLACKERS_SERVER)
    async def balance_slash(self, interaction: discord.Interaction, member: discord.Member = None, season: app_commands.Choice[str] = None):
        member = member or interaction.user
        season = season.value if season else "TWW-S3"
        balance, runs = get_user_stats(member.id, season)
        formatted_balance = f"{int(balance):,}".replace(",", ".")

        is_self = member == interaction.user

        if is_self:
            desc = f"In {season} you boosted in **{runs}** runs and earned **{formatted_balance}** 🪙."
        else:
            desc = f"In {season} **{member.display_name}** has boosted in **{runs}** runs and earned **{formatted_balance}** 🪙."

        if balance == 0:
            desc += " Slacker!"
            thumbnail_url = NOT_STONKS_EMOTE
        else:
            thumbnail_url = STONKS_EMOTE

        embed = discord.Embed(title="💼 Slacker Stats", description=desc, color=discord.Color.blue())
        embed.add_field(name="\u200b", value=f"**Slacker:** {member.display_name}", inline=True)
        embed.add_field(name="\u200b", value=f"**Runs:** {runs}", inline=True)
        embed.add_field(name="\u200b", value=f"**Gold:** {formatted_balance} 🪙", inline=True)
        embed.set_thumbnail(url=thumbnail_url)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="runs", description="Display runs the Slacker participated in.")
    @app_commands.describe(member="Slacker to check (optional, defaults to yourself)", season="Which season to check (defaults to current)")
    @app_commands.choices(season=[app_commands.Choice(name="Current", value="TWW-S3"), app_commands.Choice(name="TWW S2", value="TWW-S2")])
    @app_commands.guilds(SLACKERS_SERVER)
    async def runs_slash(self, interaction: discord.Interaction, member: discord.Member = None, season: app_commands.Choice[str] = None):
        member = member or interaction.user
        season = season.value if season else "TWW-S3"

        runs = get_all_runs(season)
        user_runs = [run for run in runs if str(member.id) in json.loads(run[8]).keys()]

        is_self = member == interaction.user
        if not user_runs:
            if is_self:
                desc = f"In {season} you have not participated in any runs. Slacker!"
            else:
                desc = f"In {season} {member.display_name} has not participated in any runs. Slacker!"
            embed = discord.Embed(title=f"{member.display_name}'s Runs", description=desc, color=discord.Color.gold())
            embed.set_thumbnail(url=NO_RUNS_EMOTE)
            return await interaction.response.send_message(embed=embed)

        response = format_runs(user_runs)

        if len(response) < 4000:
            # Short enough for embed
            embed = discord.Embed(title=f"{member.display_name}'s {season} Runs", description=f"```yaml\n{response}\n```", color=discord.Color.gold())
            await interaction.response.send_message(embed=embed)
        else:
            # Too long → send file
            file = io.StringIO(response)
            file.seek(0)
            await interaction.response.send_message(f"📂 {member.display_name}, here are your {season} runs:", file=discord.File(file, filename="all_runs.txt"))

    @app_commands.command(name="leaderboard", description="Show top Slackers by gold earned or runs done.")
    @app_commands.describe(
        season="Which season to check (defaults to current)", stat="What to rank by: 'gold' or 'runs'", size="How many Slackers to show (1–25)"
    )
    @app_commands.choices(season=[app_commands.Choice(name="Current", value="TWW-S3"), app_commands.Choice(name="TWW S2", value="TWW-S2")])
    @app_commands.choices(stat=[app_commands.Choice(name="Gold Earned", value="balance"), app_commands.Choice(name="Runs Done", value="runs")])
    @app_commands.guilds(SLACKERS_SERVER)
    async def leaderboard_slash(
        self, interaction: discord.Interaction, season: app_commands.Choice[str] = None, stat: app_commands.Choice[str] = None, size: int = 5
    ):
        season = season.value if season else "TWW-S3"
        stat = stat.value if stat else "balance"
        metric = "🪙 earned" if stat == "balance" else "runs done"

        size = max(1, min(size, 25))  # Clamp between 1–25

        top_users = get_top_users(season, stat, limit=size)
        if not top_users:
            return await interaction.response.send_message("❌ No data found.", ephemeral=True)

        leaderboard_text = "\n".join(
            [f"**#{i}** <@{user_id}> with **{int(value):,}** {metric}" for i, (user_id, value) in enumerate(top_users, start=1)]
        ).replace(",", ".")

        embed = discord.Embed(
            title=f"🏆 Top {size} Slackers by {metric.capitalize()} in {season}",
            description=leaderboard_text,
            color=discord.Color.gold() if stat == "balance" else discord.Color.blue(),
        )

        await interaction.response.send_message(embed=embed)

    # Add more booster related commands here...


async def setup(bot):
    cog = Booster(bot)
    await bot.add_cog(cog)
