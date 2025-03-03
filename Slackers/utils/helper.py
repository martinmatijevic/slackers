def update_cuts(
    mentions,
    team_type,
    raid_type,
    actual_pot,
    rl_id,
    gc_id,
    rl_cut_removed,
    gc_cut_removed,
    negative,
):
    from utils.db_helper import update_user

    cut = get_cut_percentage(team_type)
    gc_cut = 0 if gc_cut_removed or gc_id == 0 else get_gc_cut(raid_type)
    rl_cut = 0 if rl_cut_removed or rl_id == 0 else actual_pot * 0.04
    booster_cut = round((actual_pot * cut - gc_cut - rl_cut) / len(mentions))

    # If negative, flip the values to subtract instead of add
    multiplier = -1 if negative else 1

    for booster in mentions:
        if int(rl_id) == int(booster):
            update_user(
                booster,
                balance_increase=multiplier * (rl_cut + booster_cut),
                run_increase=multiplier,
            )
        else:
            update_user(
                booster,
                balance_increase=multiplier * booster_cut,
                run_increase=multiplier,
            )

    if gc_cut > 0 or gc_id != 0:
        update_user(gc_id, balance_increase=multiplier * gc_cut)


def diff_to_type(difficulty):
    if difficulty == "normal":
        team_type = "NM Teams"
    elif difficulty == "heroic":
        team_type = "HC Teams"
    elif difficulty == "mythic":
        team_type = "MythicTeam"
    else:
        team_type = "Unknown Team"  # Default if no match
    return team_type


def loot_to_type(loot_type):
    if loot_type == "saved":
        raid_type = "Saved"
    elif loot_type == "unsaved":
        raid_type = "Unsaved"
    elif loot_type == "vip":
        raid_type = "VIP"
    else:
        raid_type = "Unknown Loot Type"  # Default if no match
    return raid_type


def get_cut_percentage(team_type: str) -> float:
    cut_mapping = {"NM Teams": 0.62, "HC Teams": 0.62, "MythicTeam": 0.63}
    return cut_mapping.get(team_type, 0.60)  # Default to 0.60 if team_type is not found


def get_gc_cut(raid_type: str) -> int:
    gc_cut_mapping = {"Saved": 30000, "Unsaved": 30000, "VIP": 20000}
    return gc_cut_mapping.get(raid_type, 20000)  # Default to 20000 if not found
