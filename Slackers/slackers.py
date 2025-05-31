import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from utils.db_helper import close_connection
from utils.helper import log_debug

# Load environment variables from the .env file
load_dotenv()

# Retrieve credentials and the 2FA secret key from .env
TOKEN = os.getenv("DISCORD_TOKEN")

# Set up the bot with the appropriate intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents, case_insensitive=True)


class CleanHelp(commands.HelpCommand):
    def get_command_signature(self, command):
        return f"{self.context.clean_prefix}{command.qualified_name}"

    async def send_bot_help(self, mapping):
        lines = []
        for cog, commands_list in mapping.items():
            filtered = await self.filter_commands(commands_list, sort=True)
            if not filtered:
                continue
            cog_name = cog.qualified_name if cog else "No Category"
            lines.append(f"{cog_name}:")
            for command in filtered:
                aliases = ", ".join(command.aliases) if command.aliases else ""
                alias_text = f" (Aliases: {aliases})" if aliases else ""
                lines.append(f"  {self.get_command_signature(command)} - {command.short_doc}{alias_text}")
            lines.append("")  # Blank line between cogs

        # Add footer/help hint
        lines.append("Type .help <command> for more info on a command.")
        lines.append("You can also type .help <category> for more info on a category.")

        help_text = "\n".join(lines) or "No commands available."
        await self.get_destination().send(f"```\n{help_text}\n```")

    async def send_cog_help(self, cog):
        lines = [f"{cog.qualified_name} Commands:"]
        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        for command in filtered:
            aliases = ", ".join(command.aliases) if command.aliases else ""
            alias_text = f" (Aliases: {aliases})" if aliases else ""
            lines.append(f"  {self.get_command_signature(command)} - {command.short_doc}{alias_text}")
        help_text = "\n".join(lines)
        await self.get_destination().send(f"```\n{help_text}\n```")

    async def send_command_help(self, command):
        doc = command.help or "No description provided."
        aliases = ", ".join(command.aliases) if command.aliases else ""
        alias_text = f"\n\nAliases: {aliases}" if aliases else ""
        text = f"{self.get_command_signature(command)}\n\n{doc}{alias_text}"
        await self.get_destination().send(f"```\n{text}\n```")

    async def send_group_help(self, group):
        # Same as command help unless you want to list subcommands too
        await self.send_command_help(group)


# Replace the default help command with the clean version
bot.help_command = CleanHelp()


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
async def on_message(message):
    if message.author.bot:
        return  # Ignore bot messages

    # If the message starts with a dot but isn't a real command, ignore it
    if message.content.startswith("."):
        ctx = await bot.get_context(message)
        if not ctx.command:
            return

    await bot.process_commands(message)  # Allow commands to process


try:
    bot.run(TOKEN)
finally:
    close_connection()
