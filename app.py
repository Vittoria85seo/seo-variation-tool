# Final version of the SEO Variation Tool App with fixed math integration
# Incorporates corrected variation counting and tuned range math from benchmark logic

import streamlit as st
import pandas as pd
import numpy as np
import re
from bs4 import BeautifulSoup
from io import StringIO

st.set_page_config(layout="wide")
st.title("SEO Variation Distribution Tool")

# -------------------------------
# Variation Input
# -------------------------------
variations_input = st.text_area("Enter variation terms (comma-separated)")
variations = [v.strip().lower() for v in variations_input.split(",") if v.strip()]

# -------------------------------
# Upload User Page
# -------------------------------
st.subheader("Upload Your Page HTML")
user_file = st.file_uploader("Upload HTML", type="html", key="user_html")

# -------------------------------
# Upload Competitor HTMLs
# -------------------------------
st.subheader("Upload Competitor HTMLs (1–10 in order)")
competitor_files = []
for i in range(10):
    f = st.file_uploader(f"Competitor {i+1}", type="html", key=f"comp{i}")
    competitor_files.append(f)

# -------------------------------
# Helper: Text Extraction and Count
# -------------------------------
def extract_tag_texts(html_str):
    soup = BeautifulSoup(html_str, "html.parser")
    for tag in ["script", "style", "noscript"]:
        for match in soup.find_all(tag):
            match.decompose()
    texts = {
        "h2": [el.get_text(" ", strip=True) for el in soup.find_all("h2")],
        "h3": [el.get_text(" ", strip=True) for el in soup.find_all("h3")],
        "h4": [el.get_text(" ", strip=True) for el in soup.find_all("h4")],
        "p":  [el.get_text(" ", strip=True) for el in soup.find_all(["p", "li"])]
    }
    word_count = len(soup.get_text(" ", strip=True).split())
    return texts, word_count

def count_variations(texts, variations):
    counts = {"h2": 0, "h3": 0, "h4": 0, "p": 0}
    sorted_vars = sorted(set(variations), key=len, reverse=True)
    var_patterns = [(v, re.compile(rf"(?<!\\w){re.escape(v)}(?!\\w)", flags=re.IGNORECASE)) for v in sorted_vars]

    for tag in counts:
        for txt in texts[tag]:
            used_spans = []
            matched = set()
            for var, pattern in var_patterns:
                for match in pattern.finditer(txt):
                    span = match.span()
                    if any(start < span[1] and end > span[0] for start, end in used_spans):
                        continue
                    used_spans.append(span)
                    matched.add(var)
                    break
            counts[tag] += len(matched)
    return counts

# -------------------------------
# Collect Data
# -------------------------------
if user_file and all(competitor_files) and variations:
    user_html = user_file.read().decode("utf-8")
    user_texts, user_wc = extract_tag_texts(user_html)
    user_counts = count_variations(user_texts, variations)

    comp_counts = []
    comp_wcs = []
    for f in competitor_files:
        html = f.read().decode("utf-8")
        texts, wc = extract_tag_texts(html)
        comp_wcs.append(wc)
        comp_counts.append(count_variations(texts, variations))

    avg_comp_wc = np.mean(comp_wcs)

    # Organize data
    tag_counts_dict = {tag: [c[tag] for c in comp_counts] for tag in ["h2", "h3", "h4", "p"]}

    # -------------------------------
    # Compute Ranges
    # -------------------------------
    from Seo_Variation_Math_Fix import compute_variation_ranges  # canvas import
    ranges = compute_variation_ranges(tag_counts_dict, user_wc, avg_comp_wc)

    # -------------------------------
    # Display Output
    # -------------------------------
    df_data = {
        "Tag": ["H2", "H3", "H4", "P"],
        "Your Count": [user_counts[t] for t in ["h2", "h3", "h4", "p"]],
        "Recommended Min": [ranges[t][0] for t in ["h2", "h3", "h4", "p"]],
        "Recommended Max": [ranges[t][1] for t in ["h2", "h3", "h4", "p"]]
    }
    st.subheader("Variation Count Analysis")
    st.dataframe(pd.DataFrame(df_data))
