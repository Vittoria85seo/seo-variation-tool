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
def extract_word_count_and_sections(file):
    content = file.read()
    soup = BeautifulSoup(content, "html.parser")
    word_count = len(soup.get_text(separator=' ', strip=True).split())
    structure = {
        "h2": len(soup.find_all("h2")),
        "h3": len(soup.find_all("h3")),
        "h4": len(soup.find_all("h4")),
        "p": len(set(
            el.get_text(separator=' ', strip=True).lower()
            for el in soup.find_all(["p", "li"])
            if el.get_text(strip=True)
        ))
    }
    return word_count, structure, content

# --- Main Processing ---
if user_file and competitor_files and variations:
    user_word_count, user_structure, user_content = extract_word_count_and_sections(user_file)

    comp_word_counts = []
    comp_structures = []
    for comp_file in competitor_files:
        wc, struct, _ = extract_word_count_and_sections(comp_file)
        comp_word_counts.append(wc)
        comp_structures.append(struct)

    # Compute average word count across competitors
    avg_word_count = np.average(comp_word_counts, weights=weight_inputs)

    # Compute per-section average tag count and std dev, weighted
    def compute_section_ranges(section):
        tag_counts = np.array([s[section] for s in comp_structures])
        mean_count = np.average(tag_counts, weights=weight_inputs)
        std_count = np.sqrt(np.average((tag_counts - mean_count) ** 2, weights=weight_inputs))

        # Adjust expected tag count range to user word count relative to avg competitor word count
        scaling_factor = user_word_count / avg_word_count if avg_word_count > 0 else 1.0
        min_val = max(0, int(np.floor((mean_count - 0.8 * std_count) * scaling_factor)))
        max_val = int(np.ceil((mean_count + 0.8 * std_count) * scaling_factor))
        return min_val, max_val

    st.subheader("Tag Placement Recommendations (Word-Scaled by Competitor Avg)")
    recs = []
    for sec in ["h2", "h3", "h4", "p"]:
        min_val, max_val = compute_section_ranges(sec)
        current = user_structure[sec]
        status = "Too few" if current < min_val else ("Too many" if current > max_val else "OK")
        recs.append({"Section": sec.upper(), "Current": current, "Target Min": min_val, "Target Max": max_val, "Action": status})

    st.dataframe(pd.DataFrame(recs))
