def diff_to_type_dawn(difficulty):
    if difficulty == "NM":
        team_type = "NM Teams"
    elif difficulty == "HC":
        team_type = "HC Teams"
    elif difficulty == "MM":
        team_type = "MythicTeam"
    else:
        team_type = "Unknown Team"  # Default if no match
    return team_type


def diff_to_type_obc(difficulty):
    if difficulty == "NM":
        team_type = "Normal"
    elif difficulty == "HC":
        team_type = "Heroic"
    elif difficulty == "MM":
        team_type = "Mythic"
    else:
        team_type = "Unknown Team"  # Default if no match
    return team_type


def loot_to_type(loot_type):
    if loot_type == "Saved":
        raid_type = "Saved"
    elif loot_type == "Unsaved":
        raid_type = "Unsaved"
    elif loot_type == "VIP":
        raid_type = "VIP"
    else:
        raid_type = "Unknown Loot Type"  # Default if no match
    return raid_type
