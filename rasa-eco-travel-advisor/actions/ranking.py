"""Weighted ranking for hotel/flight options."""


def rank_options(options: list[dict],
                 sustainability_level: str = "medium",
                 budget: float | None = None) -> list[dict]:
    """Return options sorted by weighted score (best first)."""
    weights = {
        "low":    {"carbon": 0.2, "price": 0.7, "eco": 0.1},
        "medium": {"carbon": 0.4, "price": 0.4, "eco": 0.2},
        "high":   {"carbon": 0.6, "price": 0.2, "eco": 0.2},
    }
    w = weights.get(sustainability_level, weights["medium"])

    def normalize(values):
        lo, hi = min(values), max(values)
        return [1.0 if hi == lo else (v - lo) / (hi - lo) for v in values]

    if not options:
        return []

    carbons = normalize([o["carbon_kg"] for o in options])
    prices = normalize([o["price"] for o in options])
    ecos = normalize([o["eco_rating"] for o in options])

    scored = []
    for i, o in enumerate(options):
        # Lower carbon / price is better, higher eco is better
        score = (
            w["carbon"] * (1 - carbons[i])
            + w["price"] * (1 - prices[i])
            + w["eco"] * ecos[i]
        )
        if budget and o["price"] > budget:
            score *= 0.5  # penalize over-budget options
        o = {**o, "score": round(score, 3)}
        scored.append(o)

    return sorted(scored, key=lambda x: x["score"], reverse=True)
