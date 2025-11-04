import calendar
import json
from datetime import datetime

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


def format_duration(seconds: int) -> str:
    weeks, remainder = divmod(int(seconds), 604800)
    days, remainder = divmod(remainder, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)

    parts = []
    if weeks:
        parts.append(f"{weeks}w")
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs:
        parts.append(f"{secs}s")

    return " ".join(parts) if parts else "0s"


def format_date_time(run_date: str, run_time: str, community: str):
    """Format date and time string depending on community."""
    if community.lower() == "obc":
        dt = datetime.strptime(run_date, "%d/%m")
        month_abbr = calendar.month_abbr[dt.month].upper()
        return f"Date: {month_abbr}/{dt.day:02d}", f"Time: {run_time}"
    else:
        date_parts = run_date.split("/")
        date_str = f"{int(date_parts[0])}/{int(date_parts[1])}"
        time_parts = run_time.split(":")
        time_str = f"{time_parts[0]}:{time_parts[1]}"
        return date_str, time_str


def format_mentions_dawn(merged_dict, co_leaders_ids, leader, rl_cut_bool):
    """Format the mentions string for Dawn community."""
    formatted_mentions = []
    for key, value in merged_dict.items():
        if key in co_leaders_ids:
            formatted_mentions.append(f"{key}:{value}:co-lead")
        elif key == leader:
            formatted_mentions.append(f"{key}:{value}:lead" if rl_cut_bool else f"{key}:{value}:")
        else:
            formatted_mentions.append(f"{key}:{value}:")
    return ",".join(formatted_mentions)


def format_mentions_obc(merged_dict, leader, rl_cut_bool):
    """Format the mentions string for OBC community."""
    formatted_mentions = []
    for key, value in merged_dict.items():
        if key == leader:
            if not rl_cut_bool:
                formatted_mentions.append(f"<@{key}>" if value == 8 else f"<@{key}> {value}/8")
            else:
                formatted_mentions.append(f"<@{key}> L" if value == 8 else f"<@{key}> {value}/8 L")
        else:
            formatted_mentions.append(f"<@{key}>" if value == 8 else f"<@{key}> {value}/8")
    return "\n".join(formatted_mentions)
