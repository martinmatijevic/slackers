def diff_to_type_dawn(difficulty):
    if difficulty in ["nm", "normal"]:
        team_type = "NM Teams"
    elif difficulty in ["hc", "heroic"]:
        team_type = "HC Teams"
    elif difficulty in ["mm", "mythic", "m"]:
        team_type = "Mythic Teams"
    else:
        team_type = "Unknown Team"  # Default if no match
    return team_type


def diff_to_type_obc(difficulty):
    if difficulty in ["nm", "normal"]:
        team_type = "Normal"
    elif difficulty in ["hc", "heroic"]:
        team_type = "Heroic"
    elif difficulty in ["mm", "mythic", "m"]:
        team_type = "Mythic"
    else:
        team_type = "Unknown Team"  # Default if no match
    return team_type


def loot_to_type(loot_type):
    if loot_type in ["save", "saved", "s", "sav"]:
        raid_type = "Saved"
    elif loot_type in ["unsave", "unsaved", "uns", "unsav"]:
        raid_type = "Unsaved"
    elif loot_type == "vip":
        raid_type = "VIP"
    else:
        raid_type = "Unknown Loot Type"  # Default if no match
    return raid_type
