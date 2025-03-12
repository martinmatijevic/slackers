import os
import re

import discord
from discord.ext import commands
from dotenv import load_dotenv

from utils.db_helper import close_connection

# Load environment variables from the .env file
load_dotenv()

# Retrieve credentials and the 2FA secret key from .env
TOKEN = os.getenv("DISCORD_TOKEN")

# Set up the bot with the appropriate intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents, case_insensitive=True)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    # Load the cogs
    await bot.load_extension("cogs.admin")
    await bot.load_extension("cogs.booster")
    await bot.load_extension("cogs.raid_leader")


@bot.event
async def on_shutdown():
    close_connection()


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "🚫 You don't have the required permissions to use this command!"
        )
    elif isinstance(error, commands.MissingRole):
        await ctx.send("🚫 You need a specific role to use this command!")
    elif isinstance(error, commands.NotOwner):
        await ctx.send("🚫 Only the bot owner can use this command!")

    elif isinstance(error, commands.CommandNotFound):
        await ctx.send(
            "❓ That command doesn't exist! Try `.help` for a list of commands."
        )
    else:
        await ctx.send("⚠️ An error occurred. Please try again.")


@bot.event
async def on_message(message):
    if message.author.bot:
        return  # Ignore bot messages

    # Ignore messages that contain only dots (one or more)
    if re.fullmatch(r"\.+", message.content):
        return

    await bot.process_commands(message)  # Allow commands to process


bot.run(TOKEN)
close_connection()
