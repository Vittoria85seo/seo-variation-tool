import streamlit as st
from bs4 import BeautifulSoup
import re
import numpy as np
import pandas as pd

st.set_page_config(page_title="SEO Variation Analyzer", layout="centered")
st.title("SEO Variation Analyzer")

# Upload inputs
user_url = st.text_input("Your Page URL")
user_file = st.file_uploader("Upload your HTML file", type="html", key="user")

# Input all competitor URLs at once
st.markdown("**Enter All 10 Competitor URLs (one per line)**")
url_block = st.text_area("Paste competitor URLs here", height=300)
parsed_urls = [u.strip() for u in url_block.splitlines() if u.strip()]

# Always create 10 upload fields, aligned with parsed_urls or placeholder
comp_urls = parsed_urls + [f"Competitor {i+1}" for i in range(len(parsed_urls), 10)]
comp_files = []

for i, label in enumerate(comp_urls):
    st.markdown(f"**{i+1}. {label}**")
    file = st.file_uploader("Upload HTML for this competitor", type="html", key=f"html_{i}")
    comp_files.append(file)

# Variations
raw_variations = st.text_area("Enter comma-separated variation phrases", height=300)
variations = [v.strip().lower() for v in raw_variations.split(",") if v.strip()]
variation_parts = set()
for v in variations:
    variation_parts.update(v.split())
variation_parts.update(variations)

# Strict word-boundary match (no parts of words)
variation_patterns = [
    re.compile(rf"(?<!\w){re.sub(r'\s+', ' ', re.escape(v)).replace('\ ', ' ')}(?!\w)", re.IGNORECASE)
    for v in sorted(variation_parts, key=len, reverse=True)
]

P_TAGS = {"p", "li"}
HEADINGS = {"h2", "h3", "h4"}
ALL_TAGS = ["h2", "h3", "h4", "p"]

def get_text(tag):
    return tag.get_text(separator=" ", strip=True).lower()

def count_words(soup):
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator=' ', strip=True)
    return len(re.sub(r'\s+', ' ', text).split())

def analyze_file(file):
    try:
        file.seek(0)
    except Exception:
        pass
    try:
        raw = file.read()
        try:
            decoded = raw.decode("utf-8")
        except:
            decoded = raw.decode("latin1")
        soup = BeautifulSoup(decoded, "html.parser")
    except:
        return {tag: 0 for tag in ALL_TAGS}, 0, {tag: [] for tag in ALL_TAGS}

    counts = {tag: 0 for tag in ALL_TAGS}
    matches_per_tag = {tag: [] for tag in ALL_TAGS}
    for tag in soup.find_all(True):
        name = tag.name.lower()
        if name in HEADINGS or name in P_TAGS:
            text = get_text(tag)
            count = 0
            used_spans = []
            found = []
            for pattern in variation_patterns:
                for m in pattern.finditer(text):
                    span = m.span()
                    if any(s <= span[0] < e or s < span[1] <= e for s, e in used_spans):
                        continue
                    used_spans.append(span)
                    count += 1
                    found.append(m.group())
            if count:
                key = "p" if name in P_TAGS else name
                counts[key] += count
                matches_per_tag[key].extend(found)
    wc = count_words(soup)
    return counts, wc, matches_per_tag

# Run main analysis
valid_comp_files = [f for f in comp_files if f is not None]
if user_file and len(valid_comp_files) == 10 and variation_patterns:
    user_counts, user_wc, user_matches = analyze_file(user_file)

    comp_data = []
    comp_wordcounts = []
    for f in valid_comp_files:
        counts, wc, _ = analyze_file(f)
        comp_data.append(counts)
        comp_wordcounts.append(wc)

    df = {tag: [row[tag] for row in comp_data] for tag in ALL_TAGS}
    weights = np.exp(-np.arange(10))
    weights /= weights.sum()
    avg_wc = np.average(comp_wordcounts, weights=weights)
    scale = user_wc / avg_wc if avg_wc > 0 else 1

    # Final results table
    result_rows = []
    for tag in ALL_TAGS:
        values = np.array(df[tag])
        cleaned = sorted([v for v in values if v > 0])
        if len(cleaned) >= 3:
            trimmed = cleaned[1:-1] if len(cleaned) > 4 else cleaned
            low, high = np.percentile(trimmed, [10, 90])
        elif len(cleaned) > 0:
            low, high = min(cleaned), max(cleaned)
        else:
            low, high = 0, 0
        min_val = round(low * scale)
        max_val = round(high * scale)
        actual = user_counts[tag]
        status = "Add" if actual < min_val else "Reduce" if actual > max_val else "OK"
        result_rows.append((tag.upper(), actual, f"{min_val}–{max_val}", status))

    result_df = pd.DataFrame(result_rows, columns=["Tag", "Your Count", "Recommended Range", "Action"])
    st.subheader("Final Optimization Summary")
    st.table(result_df)
