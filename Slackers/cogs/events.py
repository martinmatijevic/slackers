import datetime
import os

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.helper import build_event_embed_from_list, is_app_owner, purge_channel, sort_events_by_category

SLACKERS = int(os.getenv("SLACKERS_CHANNEL"))
SLACK = int(os.getenv("SLACK_CHANNEL"))
SLACKERS_SERVER = int(os.getenv("SLACKERS_SERVER"))


class EventViewer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.guild: discord.Guild | None = None

        self.channel_ids = {
            "slackers": SLACKERS,
            #"slack": SLACK,
        }

        self.last_updated: datetime.datetime | None = None
        self.grace_period = datetime.timedelta(hours=3)

    def cog_unload(self):
        self.update_event_view.cancel()

    async def fetch_guild(self):
        if not self.guild:
            self.guild = self.bot.get_guild(SLACKERS_SERVER)
        return self.guild

    async def update_embed(self, force: bool = False):
        now = datetime.datetime.now()
        if not force and self.last_updated and (now - self.last_updated) < self.grace_period:
            return

        guild = await self.fetch_guild()
        if not guild:
            return

        sorted_events = await sort_events_by_category(guild)
        if not sorted_events:
            return

        slackers_events, slack_events = sorted_events
        event_lists = {
            "slackers": slackers_events,
            "slack": slack_events,
        }

        for key, events in event_lists.items():
            if not events:
                continue

            channel_id = self.channel_ids.get(key)
            if not channel_id:
                continue

            channel = guild.get_channel(channel_id)
            if not channel:
                continue

            await purge_channel(channel, 100)

            embeds = build_event_embed_from_list(events, key)
            for embed in embeds:
                await channel.send(embed=embed)

        self.last_updated = now

    @is_app_owner()
    @app_commands.command(name="schedule", description="Display all active events on the server.")
    @app_commands.guilds(SLACKERS_SERVER)
    async def schedule_slash(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        await self.update_embed(force=True)
        await interaction.followup.send("Event list posted.", ephemeral=True)

    @commands.Cog.listener()
    async def on_scheduled_event_create(self, event: discord.ScheduledEvent):
        await self.update_embed()

    @commands.Cog.listener()
    async def on_scheduled_event_update(self, before: discord.ScheduledEvent, after: discord.ScheduledEvent):
        await self.update_embed()

    @commands.Cog.listener()
    async def on_scheduled_event_delete(self, event: discord.ScheduledEvent):
        await self.update_embed()

    @tasks.loop(minutes=1440)
    async def update_event_view(self):
        await self.update_embed(force=True)

    @update_event_view.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()
        await self.fetch_guild()


async def setup(bot):
    await bot.add_cog(EventViewer(bot))
