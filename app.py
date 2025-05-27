
import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import re

st.title("SEO Variation & Structure Analyzer")

# Step 1 – Upload your page
st.header("1. Upload Your Page")
user_file = st.file_uploader("Upload your HTML file (your page)", type="html", key="user")

# Step 2 – Upload 10 competitors in order
st.header("2. Upload 10 Competitor Files")
competitor_urls_input = st.text_area("Paste 10 competitor URLs in correct order (1 per line)")
competitor_urls = [line.strip() for line in competitor_urls_input.split("\n") if line.strip()]
competitor_files = []
for i, url in enumerate(competitor_urls):
    competitor_files.append(st.file_uploader(f"Upload HTML for Competitor {i+1} ({url})", type="html", key=f"comp_{i}"))

# Step 3 – Enter variation terms
st.header("3. Enter Variation Phrases")
variations_text = st.text_area("Enter comma-separated variations", value="fleecejacka herr, fleecejacka, herr")
variations = [v.strip().lower() for v in variations_text.split(",") if v.strip()]
variation_parts = set(variations)
for v in variations:
    variation_parts.update(v.split())

# Helper – word count cleaner
def cleaned_word_count(soup):
    for tag in soup(["script", "style"]): tag.extract()
    return len(re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).split())

# Variation match count logic – allow overlaps and count each variation once per tag
def count_variations_per_tag(soup, tag, variation_list):
    elements = soup.find_all(tag) if tag != "p" else soup.find_all(["p", "li"])
    total = 0
    sorted_vars = sorted(variation_list, key=lambda x: -len(x))
    for el in elements:
        text = el.get_text(separator=" ", strip=True).lower()
        found = set()
        for var in sorted_vars:
            if re.search(rf"(?<!\w){re.escape(var)}(?!\w)", text):
                found.add(var)
        total += len(found)
    return total

# Step 4 – Run analysis
if user_file and all(competitor_files) and len(competitor_files) == 10 and variations:
    # Analyze user page
    user_html = user_file.read()
    user_soup = BeautifulSoup(user_html, "html.parser")
    user_wc = cleaned_word_count(user_soup)
    user_counts = {
        "h2": count_variations_per_tag(user_soup, "h2", variation_parts),
        "h3": count_variations_per_tag(user_soup, "h3", variation_parts),
        "h4": count_variations_per_tag(user_soup, "h4", variation_parts),
        "p":  count_variations_per_tag(user_soup, "p", variation_parts),
    }

    # Analyze competitors
    comp_data = []
    for f in competitor_files:
        html = f.read()
        soup = BeautifulSoup(html, "html.parser")
        wc = cleaned_word_count(soup)
        counts = {
            "h2": count_variations_per_tag(soup, "h2", variation_parts),
            "h3": count_variations_per_tag(soup, "h3", variation_parts),
            "h4": count_variations_per_tag(soup, "h4", variation_parts),
            "p":  count_variations_per_tag(soup, "p", variation_parts),
        }
        comp_data.append({"wc": wc, **counts})

    df = pd.DataFrame(comp_data)
    avg_wc = df["wc"].mean()
    scale = user_wc / avg_wc if avg_wc else 1

    # Weights: top = more important
    weights = np.array([1.5 - 0.1*i for i in range(10)])
    weights /= weights.sum()

    # Compute weighted, scaled percentiles
    def get_range(section):
        vals = df[section].values
        if section == "h3":
            vals = np.clip(vals, 0, 20)
        weighted_avg = np.average(vals, weights=weights)
        std_dev = np.sqrt(np.average((vals - weighted_avg)**2, weights=weights))
        lower = max(0, int(np.floor((weighted_avg - 0.3*std_dev) * scale)))
        upper = int(np.ceil((weighted_avg + 0.3*std_dev) * scale))
        return lower, upper

    st.header("4. Tag Placement Recommendations")
    rows = []
    for tag in ["h2", "h3", "h4", "p"]:
        rmin, rmax = get_range(tag)
        user_val = user_counts[tag]
        rows.append({
            "Tag": tag.upper(),
            "Your Count": user_val,
            "Recommended Min": rmin,
            "Recommended Max": rmax,
            "Status": "OK" if rmin <= user_val <= rmax else ("Too few" if user_val < rmin else "Too many")
        })

    st.dataframe(pd.DataFrame(rows))
