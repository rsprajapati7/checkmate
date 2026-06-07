def get_tier(score: float) -> str:
    if score < 30: return "GREEN"
    if score < 60: return "AMBER"
    return "RED"
