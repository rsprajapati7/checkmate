def calculate_final_score(ela_score: float, meta_score: float, seal_score: float, nlp_score: float) -> tuple[float, str]:
    score = (ela_score * 0.35) + (meta_score * 0.25) + (seal_score * 0.25) + (nlp_score * 0.15)
    tier = "GREEN" if score < 30 else "AMBER" if score < 60 else "RED"
    return score, tier
