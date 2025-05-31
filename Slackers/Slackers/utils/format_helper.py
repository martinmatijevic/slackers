import json

import discord


async def get_username(bot, server_id, user_id):
    guild = bot.get_guild(server_id)  # Get the guild (server) object
    try:
        user = await guild.fetch_member(int(user_id))
        return f"{user.display_name}"
    except (discord.NotFound, discord.HTTPException, ValueError):
        return user_id


async def format_schedule(bot, server_id, schedule_data):
    table = "```Run ID                    | Date       | Time  | Difficulty | Type  | RL ID               | GC ID               | Community\n"
    table += "-" * 123 + "\n"

    for run_id, run_date, run_time, difficulty, run_type, rl_id, gc_id, community in schedule_data:
        rl = await get_username(bot, server_id, rl_id)
        gc = await get_username(bot, server_id, gc_id)
        table += f"{run_id.ljust(24)}  | {run_date:<10} | {run_time:<5} | {difficulty:<10} | {run_type:<5} | {rl:<19} | {gc:<19} | {community}\n"

    table += "```"
    return table


async def format_users(bot, server_id, users_data):
    table = "```Balance    | Runs  | User ID\n" + "-" * 47 + "\n"

    for user_id, balance, runs in users_data:
        user = await get_username(bot, server_id, user_id)
        formatted_balance = f"{int(balance):,}".replace(",", ".")
        table += f"{formatted_balance:<10} | {runs:<5} | {user}\n"
    table += "```"

    return table


def format_runs(runs):
    try:
        formatted_runs = []

        for run in runs:
            (run_id, run_date, run_time, difficulty, rtype, pot, rl_id, gc_id, user_ids, community, *_) = run
            user_ids = json.loads(user_ids)  # Convert JSON string back to dict
            users_str = ", ".join(f"{user_id}:{cut}" for user_id, cut in user_ids.items())

            formatted_runs.append(
                f"📌 Run ID: {run_id}\n"
                f"📅 Date: {run_date} | ⏰ Time: {run_time}\n"
                f"🎮 Difficulty: {difficulty} | Type: {rtype}\n"
                f"💰 Pot: {pot} | 🌐 Community: {community}\n"
                f"🆔 RL ID: {rl_id} | GC ID: {gc_id}\n"
                f"👥 Users: {users_str}\n"
                f"{'-'*40}"
            )

        return "\n".join(formatted_runs)
    except Exception as e:
        print(e)
