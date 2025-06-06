def compute_benchmark_ranges(user_html, competitor_data, coefficients):
    import math
    from bs4 import BeautifulSoup

    def weighted_avg(values):
        weights = [1.6, 1.5, 1.4, 1.3, 1.2, 1.0, 0.8, 0.6, 0.5, 0.4]  # reduce outlier weight
        return sum(v * w for v, w in zip(values, weights)) / sum(weights)

    def compute_word_count(html):
        soup = BeautifulSoup(html, "html.parser")
        return len(soup.get_text().split())

    user_word_count = compute_word_count(user_html)
    word_counts = [c["word_count"] for c in competitor_data]
    avg_word_count = sum(word_counts) / len(word_counts)
    scale = user_word_count / avg_word_count

    h2_vals = [c["variation_counts"]["h2"] for c in competitor_data]
    h3_vals = [c["variation_counts"]["h3"] for c in competitor_data]
    h4_vals = [c["variation_counts"]["h4"] for c in competitor_data]
    p_vals = [c["variation_counts"]["p"] for c in competitor_data]

    h2_avg = round(weighted_avg(h2_vals), 1)
    h3_avg = round(weighted_avg(h3_vals), 1)
    h4_avg = round(weighted_avg(h4_vals), 1)
    p_avg = round(weighted_avg(p_vals), 1)

    def force_zero_floor(values, default_floor):
        top4 = sorted(values, reverse=True)[:4]
        return 0 if top4.count(0) >= 2 else default_floor

    ranges = {}
    ranges["h2"] = (
        max(0, math.floor(coefficients["h2"][0] * h2_avg * scale)),
        math.ceil(coefficients["h2"][1] * h2_avg * scale)
    )
    h3_floor = force_zero_floor(h3_vals, math.floor(coefficients["h3"][0] * h3_avg * scale))
    ranges["h3"] = (
        max(0, h3_floor),
        math.ceil(coefficients["h3"][1] * h3_avg * scale)
    )
    h4_scaled = coefficients["h4"][0] * h4_avg * scale
    if h4_scaled < 0.5:
        ranges["h4"] = (0, 0)
    else:
        ranges["h4"] = (
            max(0, math.floor(h4_scaled)),
            math.ceil(coefficients["h4"][1] * h4_avg * scale)
        )
    ranges["p"] = (
        max(0, math.floor(coefficients["p"][0] * p_avg * scale)),
        math.ceil(coefficients["p"][1] * p_avg * scale)
    )

    return ranges
