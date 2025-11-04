import asyncio


def sort_dawn_cuts(bot, difficulty, type, pot, rl_id, gc_id, boosters, rl_cut_shared, gc_cut_shared, negative=0):
    from utils.db_helper import update_user
    from utils.helper import log_debug, send_batched_logs

    cut = get_cut_percentage(difficulty)
    rl_cut = 0 if rl_cut_shared else pot * 0.04
    gc_cut = 0 if gc_cut_shared else get_gc_cut(type, difficulty)
    cut_per_boss = round((pot * cut - rl_cut - gc_cut) / sum(boosters.values()))

    # If negative, flip the values to subtract instead of add
    multiplier = -1 if negative else 1

    log_lines = []

    for booster, value in boosters.items():
        if rl_id == booster:
            update_user(
                booster,
                balance_increment=round(multiplier * (rl_cut + value * cut_per_boss)),
                runs_increment=multiplier,
            )
            log_lines.append(f"Updating RL {booster}: bal = {round(multiplier * (rl_cut + value * cut_per_boss))}, run = {multiplier}")
        else:
            update_user(
                booster,
                balance_increment=round(multiplier * value * cut_per_boss),
                runs_increment=multiplier,
            )
            log_lines.append(f"Updating booster {booster}: bal = {round(multiplier * value * cut_per_boss)}, run = {multiplier}")

    if gc_cut > 0:
        update_user(gc_id, balance_increment=multiplier * gc_cut)
        log_lines.append(f"Updating GC {gc_id}: bal = {multiplier * gc_cut}")

    # Send all logs as one message
    if log_lines:
        try:
            asyncio.create_task(send_batched_logs(bot, log_debug, log_lines))
        except Exception as e:
            print(e)

    return cut_per_boss * 8


def sort_obc_cuts(bot, difficulty, type, pot, rl_id, gc_id, boosters, rl_cut_shared, gc_cut_shared, negative=0):
    from utils.db_helper import update_user
    from utils.helper import log_debug, send_batched_logs

    cut = get_cut_percentage_obc(difficulty)
    rl_cut = 0 if rl_cut_shared else pot * 0.03
    total_units = sum(count / 8 for count in boosters.values()) + get_gc_cut_obc(type)
    if gc_cut_shared:
        total_units -= get_gc_cut_obc(type)
    full_booster_cut = round((pot * cut - rl_cut) / total_units)
    gc_cut = 0 if gc_cut_shared else round(full_booster_cut * get_gc_cut_obc(type))

    # If negative, flip the values to subtract instead of add
    multiplier = -1 if negative else 1

    log_lines = []

    for booster, value in boosters.items():
        if rl_id == booster:
            balance = round(multiplier * (rl_cut + value / 8 * full_booster_cut))
            update_user(
                booster,
                balance_increment=balance,
                runs_increment=multiplier,
            )
            log_lines.append(f"Updating RL {booster}: bal = {balance}, run = {multiplier}")
        else:
            balance = round(multiplier * value / 8 * full_booster_cut)
            update_user(
                booster,
                balance_increment=balance,
                runs_increment=multiplier,
            )
            log_lines.append(f"Updating booster {booster}: bal = {balance}, run = {multiplier}")

    if gc_cut > 0:
        balance = multiplier * gc_cut
        update_user(gc_id, balance_increment=balance)
        log_lines.append(f"Updating GC {gc_id}: bal = {balance}")

    # Send combined log message
    if log_lines:
        try:
            asyncio.create_task(send_batched_logs(bot, log_debug, log_lines))
        except Exception as e:
            print(e)

    return full_booster_cut

def sort_raw_cuts(difficulty, type, pot, boosters, rl_cut_shared, gc_cut_shared):
    cut = get_cut_percentage_raw(difficulty)
    rl_cut = 0 if rl_cut_shared else pot * 0.04
    gc_cut = 0 if gc_cut_shared else get_gc_cut(type, difficulty)
    cut_per_boss = round((pot * cut - rl_cut - gc_cut) / sum(boosters.values()))
    return cut_per_boss * 8



def get_cut_percentage(team_type: str) -> float:
    cut_mapping = {"NM Teams": 0.62, "HC Teams": 0.62, "Mythic Teams": 0.63}
    return cut_mapping.get(team_type, 0.8)  # Default to 0.8 if team_type is not found

def get_cut_percentage_raw(team_type: str) -> float:
    cut_mapping = {"NM Teams": 0.65, "HC Teams": 0.65, "Mythic Teams": 0.63}
    return cut_mapping.get(team_type, 0.8)  # Default to 0.8 if team_type is not found


def get_cut_percentage_obc(team_type: str) -> float:
    cut_mapping = {"Normal": 0.625, "Heroic": 0.625, "Mythic": 0.65}
    return cut_mapping.get(team_type, 0.6)  # Default to 0.6 if team_type is not found


def get_gc_cut(raid_type: str, team_type: str) -> int:
    gc_cut_mapping_nm = {"Saved": 35000, "Unsaved": 35000, "VIP": 35000}
    gc_cut_mapping_hc = {"Saved": 50000, "Unsaved": 70000, "VIP": 60000}
    if team_type == "NM Teams":
        return gc_cut_mapping_nm.get(raid_type, 60000)  # Default to 60000 for mythic
    else:
        return gc_cut_mapping_hc.get(raid_type, 60000)  # Default to 60000 for mythic


def get_gc_cut_obc(raid_type: str) -> float:
    gc_cut_mapping = {"Saved": 0.3, "Unsaved": 0.3, "VIP": 0.1}
    return gc_cut_mapping.get(raid_type, 0.2)  # Default to 0.2 if not found
