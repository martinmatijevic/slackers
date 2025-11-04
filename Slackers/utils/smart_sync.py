import json
import os

import discord

SYNC_CACHE_FILE = "command_sync_cache.json"
SLACKERS_SERVER = int(os.getenv("SLACKERS_SERVER"))
BAM_SERVER = int(os.getenv("BAM_SERVER"))
RAW_SERVER = int(os.getenv("RAW_SERVER"))


async def smart_sync(bot: discord.Client):
    try:
        # Always sync global (if any)
        await bot.tree.sync()
        print("✅ Global commands synced.")

        # Sync each guild explicitly
        for gid in [SLACKERS_SERVER, RAW_SERVER]:
            await bot.tree.sync(guild=discord.Object(id=gid))
            print(f"✅ Guild {gid} commands synced.")

        # Save cache manually
        current_state = {
            "global": [cmd.name for cmd in bot.tree.get_commands() if not getattr(cmd, "_guild_ids", None)],
            "guilds": {
                str(SLACKERS_SERVER): [cmd.name for cmd in bot.tree.get_commands(guild=discord.Object(id=SLACKERS_SERVER))],
                str(RAW_SERVER): [cmd.name for cmd in bot.tree.get_commands(guild=discord.Object(id=RAW_SERVER))],
            },
        }

        with open(SYNC_CACHE_FILE, "w") as f:
            json.dump(current_state, f)
            print("✅ Updated sync cache file.")

    except Exception as e:
        print("Error in smart_sync:", e)
