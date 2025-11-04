import asyncio
import os

import discord
from discord import app_commands
from discord.ext import commands

import env_setup
from utils.db_helper import close_connection
from utils.helper import format_slash_args, log_debug
from utils.smart_sync import smart_sync

_ = env_setup

TOKEN = os.getenv("DISCORD_TOKEN")
PLAYGROUND = int(os.getenv("PLAYGROUND"))

# Set up the bot with the appropriate intents
intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents, case_insensitive=True)


@bot.tree.command(name="help", description="Show all slash commands.")
async def help_slash(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)

    # Collect commands by category
    grouped = {}
    for cmd in bot.tree.walk_commands():
        if cmd.name.startswith("_"):  # skip hidden
            continue

        # Get the cog name if available
        category = cmd.binding.__class__.__name__ if cmd.binding else "No Category"

        # Build parameter list
        param_list = []
        for param in cmd.parameters:
            if param.required:
                param_list.append(f"<{param.name}>")
            else:
                if param.default is not None and not callable(param.default):
                    # Show default value repr but strip quotes from strings for neatness
                    default_val = param.default
                    if isinstance(default_val, str):
                        default_val = f'"{default_val}"'  # add quotes around string defaults
                    param_list.append(f"[{param.name}={default_val}]")
                else:
                    param_list.append(f"[{param.name}]")

        params_str = " " + " ".join(param_list) if param_list else ""
        description = cmd.description or "No description"

        grouped.setdefault(category, []).append(f"/{cmd.qualified_name}{params_str} — {description}")

    # Build final text
    lines = []
    for category in sorted(grouped.keys()):
        lines.append(f"{category}:")
        for entry in sorted(grouped[category], key=str.lower):
            lines.append(f"  {entry}")
        lines.append("")

    # Legend at the bottom
    if lines:
        lines.append("<param> = required argument.")
        lines.append("[param] = optional argument.")

    help_text = "\n".join(lines) or "No slash commands available."
    await interaction.followup.send(f"```\n{help_text}\n```", ephemeral=True)


@bot.tree.command(name="find", description="Mention a user by Discord ID")
@app_commands.describe(discord_id="The Discord user ID to mention")
async def find(interaction: discord.Interaction, discord_id: str):
    try:
        user_id = int(discord_id)
        user = await bot.fetch_user(user_id)  # Fetch user object (works in DMs too)
        await interaction.response.send_message(f"Found user: {user.mention} ({user})", ephemeral=True)
    except ValueError:
        await interaction.response.send_message("❌ That’s not a valid Discord ID.", ephemeral=True)
    except discord.NotFound:
        await interaction.response.send_message("❌ I couldn’t find a user with that ID.", ephemeral=True)


@bot.event
async def on_ready():

    await asyncio.sleep(5)
    await smart_sync(bot)

    print(f"Logged in as {bot.user}")
    channel = bot.get_channel(PLAYGROUND)
    if channel:
        await channel.send(f"✅ {bot.user} is now online.")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 You don't have the required permissions to use this command!")
    elif isinstance(error, commands.MissingRole):
        await ctx.send("🚫 You need a specific role to use this command!")
    elif isinstance(error, commands.NotOwner):
        await ctx.send("🚫 Only the bot owner can use this command!")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("❓ That command doesn't exist! Try `.help` for a list of commands.")
    else:
        await ctx.send("⚠️ An error occurred. Please try again.")


@bot.event
async def on_command(ctx):
    loc = f"{ctx.guild}/{ctx.channel}" if ctx.guild else f"DM/{ctx.author}"
    await log_debug(bot, f"Command `{ctx.message.content}` used by {ctx.author} in {loc}")


@bot.event
async def on_app_command_completion(interaction, command):
    args_str = format_slash_args(interaction)
    loc = f"{interaction.guild}/{interaction.channel}" if interaction.guild else f"DM/{interaction.user}"
    await log_debug(bot, f"Slash Command `/{command.qualified_name}{args_str}` used by {interaction.user} in {loc}")


@bot.event
async def on_app_command_error(interaction, error):
    args_str = format_slash_args(interaction)
    loc = f"{interaction.guild}/{interaction.channel}" if interaction.guild else f"DM/{interaction.user}"
    await log_debug(bot, f"⚠ Slash Command `/{interaction.command.qualified_name}{args_str}` by {interaction.user} in {loc} failed with: {error}")


@bot.event
async def on_message(message):
    if message.author.bot:
        return  # Ignore bot messages

    # If the message starts with a dot but isn't a real command, ignore it
    if message.content.startswith("."):
        ctx = await bot.get_context(message)
        if not ctx.command:
            return

    await bot.process_commands(message)  # Allow commands to process


async def main():
    # Load cogs BEFORE starting the bot
    for ext in ["cogs.admin", "cogs.booster", "cogs.raid_leader", "cogs.events", "cogs.bam", "cogs.raw", "cogs.quick_create"]:
        await bot.load_extension(ext)

    # Now start the bot
    try:
        await bot.start(TOKEN)
    except KeyboardInterrupt:
        pass
    finally:
        channel = bot.get_channel(PLAYGROUND)
        if channel:
            try:
                await channel.send(f"❌ {bot.user} is shutting down.")
            except Exception as e:
                print("Failed to send shutdown message:", e)
        close_connection()
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
