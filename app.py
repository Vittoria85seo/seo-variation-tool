import streamlit as st
import numpy as np
from bs4 import BeautifulSoup
from collections import Counter
import pandas as pd
import io

st.title("SEO Variation & Structure Analyzer")

# --- Upload section ---
st.header("1. Upload Files")
user_file = st.file_uploader("Upload your HTML file", type="html", key="user")
competitor_files = st.file_uploader("Upload competitor HTML files (10 max)", type="html", accept_multiple_files=True, key="comps")

# --- Variation input ---
st.header("2. Enter Variations List")
variations_text = st.text_area("Enter comma-separated variations")
variations = [v.strip().lower() for v in variations_text.split(",") if v.strip()] if variations_text else []

# --- Weighting ---
st.header("3. Adjust Competitor Weighting (Top to Bottom Rank)")
def default_weights(n):
    return [round(1.5 - i*0.1, 2) for i in range(n)]

if competitor_files:
    default_w = default_weights(len(competitor_files))
    weight_inputs = [st.number_input(f"Weight for Competitor {i+1}", value=w, step=0.1) for i, w in enumerate(default_w)]
else:
    weight_inputs = []

# --- Extraction Function ---
def extract_variation_counts(file, variations):
    content = file.read()
    soup = BeautifulSoup(content, "html.parser")
    counts = {"h2": 0, "h3": 0, "h4": 0, "p": 0}

    for tag in ["h2", "h3", "h4"]:
        for el in soup.find_all(tag):
            txt = el.get_text(separator=' ', strip=True).lower()
            counts[tag] += sum(txt.count(v) for v in variations)

    # Combine <p> and <li> as paragraph sources, without duplicates
    para_texts = set(
        el.get_text(separator=' ', strip=True).lower()
        for el in soup.find_all(["p", "li"])
        if el.get_text(strip=True)
    )
    counts["p"] = sum(
        sum(text.count(v) for v in variations)
        for text in para_texts
    )

    full_text = " ".join(para_texts)
    token_list = full_text.split()
    variation_counts = {v: token_list.count(v) for v in variations}

    return variation_counts, counts

# --- Main Processing ---
if user_file and competitor_files and variations:
    user_var_counts, user_struct_counts = extract_variation_counts(user_file, variations)

    comp_data = []
    for comp_file in competitor_files:
        var_counts, struct_counts = extract_variation_counts(comp_file, variations)
        comp_data.append((var_counts, struct_counts))

    # Weighted variation stats
    def weighted_stat(v):
        vals = np.array([comp[0][v] for comp in comp_data])
        mean = np.average(vals, weights=weight_inputs)
        std = np.sqrt(np.average((vals - mean) ** 2, weights=weight_inputs))
        return round(mean, 2), round(std, 2)

    var_table = []
    for v in variations:
        c = user_var_counts[v]
        a, std = weighted_stat(v)
        action = "add" if c < a else ("remove" if c > a else "ok")
        var_table.append({"Variation": v, "C=": c, "A=": a, "Action": action})

    st.subheader("Variation Frequency Table")
    st.dataframe(pd.DataFrame(var_table))

    # Section tag recommendations
    def section_stats(section):
        values = np.array([comp[1][section] for comp in comp_data])
        if not values.any():
            return 0, 0.0, 0, 0
        mean = np.average(values, weights=weight_inputs)
        std = np.sqrt(np.average((values - mean) ** 2, weights=weight_inputs))
        min_t = max(0, int(np.floor(mean - 0.8 * std)))
        max_t = int(np.ceil(mean + 0.8 * std))
        return int(mean), round(std, 2), min_t, max_t

    st.subheader("Tag Placement Recommendations")
    rows = []
    for sec in ["h2", "h3", "h4", "p"]:
        mean, std, min_val, max_val = section_stats(sec)
        current = user_struct_counts[sec]
        status = "Too few" if current < min_val else ("Too many" if current > max_val else "OK")
        rows.append({"Section": sec.upper(), "Current": current, "Target Min": min_val, "Target Max": max_val, "Action": status})

    st.dataframe(pd.DataFrame(rows))
