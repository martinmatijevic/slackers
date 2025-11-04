import asyncio
import os

import aiohttp

import env_setup

_ = env_setup

TOKEN = os.getenv("DISCORD_TOKEN")
SLACKERS_SERVER = int(os.getenv("SLACKERS_SERVER"))

GUILDS = [SLACKERS_SERVER]  # Only your guild
BASE_URL = "https://discord.com/api/v10"
HEADERS = {"Authorization": f"Bot {TOKEN}"}


async def bulk_upsert(session, url, data):
    async with session.put(url, headers=HEADERS, json=data) as resp:
        if resp.status not in (200, 201):
            print(f"⚠ Failed request {resp.status}: {await resp.text()}")


async def fetch(session, url):
    async with session.get(url, headers=HEADERS) as resp:
        return await resp.json()


async def main():
    async with aiohttp.ClientSession() as session:
        # Get bot ID
        me = await fetch(session, f"{BASE_URL}/users/@me")
        bot_id = me["id"]
        print(f"Bot ID: {bot_id}")

        # Remove all global commands
        await bulk_upsert(session, f"{BASE_URL}/applications/{bot_id}/commands", [])
        print("✅ All global commands deleted.")

        # Remove all commands in your guild
        for guild_id in GUILDS:
            await bulk_upsert(session, f"{BASE_URL}/applications/{bot_id}/guilds/{guild_id}/commands", [])
            print(f"✅ All commands deleted in guild {guild_id}")

        # Fetch remaining commands for verification
        global_cmds = await fetch(session, f"{BASE_URL}/applications/{bot_id}/commands")
        print(f"🌍 Remaining global commands ({len(global_cmds)}): {global_cmds}")

        for guild_id in GUILDS:
            guild_cmds = await fetch(session, f"{BASE_URL}/applications/{bot_id}/guilds/{guild_id}/commands")
            print(f"🏠 Remaining commands in guild {guild_id} ({len(guild_cmds)}): {guild_cmds}")


asyncio.run(main())
