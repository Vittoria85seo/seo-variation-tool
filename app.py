import streamlit as st
import numpy as np
from bs4 import BeautifulSoup
from collections import Counter
import pandas as pd
import io
import re

st.title("SEO Variations Analyzer")

# --- Upload section ---
st.header("1. Upload Files")
user_file = st.file_uploader("Upload your HTML file", type="html", key="user")
competitor_files = st.file_uploader("Upload competitor HTML files (10 max)", type="html", accept_multiple_files=True, key="comps")

# --- Variation input ---
st.header("2. Enter Variations List")
variations_text = st.text_area("Enter comma-separated variations")
variations = [v.strip().lower() for v in variations_text.split(",") if v.strip()] if variations_text else []
variation_parts = set(variations)

# --- Weighting ---
st.header("3. Adjust Competitor Weighting (Top to Bottom Rank)")
def default_weights(n):
    return [round(1.5 - i*0.1, 2) for i in range(n)]

if competitor_files:
    default_w = default_weights(len(competitor_files))
    weight_inputs = [st.number_input(f"Weight for Competitor {i+1}", value=w, step=0.1) for i, w in enumerate(default_w)]
else:
    weight_inputs = []

# --- Improved word count function ---
def cleaned_word_count(soup):
    for script in soup(["script", "style"]):
        script.extract()
    text = soup.get_text(separator=' ', strip=True)
    text = re.sub(r'\s+', ' ', text)
    return len(text.split())

# --- Variation counting function ---
def count_variation_matches(soup, tag, variation_set):
    tags = soup.find_all(tag) if tag != "p" else soup.find_all(["p", "li"])
    count = 0
    for el in tags:
        text = el.get_text(separator=' ', strip=True).lower()
        for var in variation_set:
            pattern = r'(?<!\w)' + re.escape(var) + r'(?!\w)'
            matches = re.findall(pattern, text)
            count += len(matches)
    return count

# --- Extraction Function ---
def extract_word_count_and_sections(file):
    content = file.read()
    soup = BeautifulSoup(content, "html.parser")
    word_count = cleaned_word_count(soup)
    structure = {
        "h2": count_variation_matches(soup, "h2", variation_parts),
        "h3": count_variation_matches(soup, "h3", variation_parts),
        "h4": count_variation_matches(soup, "h4", variation_parts),
        "p": count_variation_matches(soup, "p", variation_parts)
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

    avg_word_count = np.average(comp_word_counts, weights=weight_inputs)

        def compute_dynamic_range(section):
        section_counts_all = [s[section] for s in comp_structures]
        sorted_counts = sorted(section_counts_all)
        trim_n = max(1, len(sorted_counts) // 5)

        # Trim the counts and weights
        trimmed = sorted_counts[trim_n:-trim_n] if len(sorted_counts) > 2 * trim_n else sorted_counts
        trimmed_weights = weight_inputs[trim_n:-trim_n] if len(weight_inputs) > 2 * trim_n else weight_inputs[:len(trimmed)]

        # Compute weighted mean and std dev from trimmed values
        mean = np.average(trimmed, weights=trimmed_weights)
        std = np.sqrt(np.average((np.array(trimmed) - mean) ** 2, weights=trimmed_weights))

        # Scale based on user vs competitor avg word count
        scale = user_word_count / avg_word_count if avg_word_count > 0 else 1.0
        min_val = max(0, int(np.floor((mean - 0.8 * std) * scale)))
        max_val = int(np.ceil((mean + 0.8 * std) * scale)))
        return min_val, max_val

    st.subheader("Tag Placement Recommendations (Dynamic Math-Based)")
    recs = []
    for sec in ["h2", "h3", "h4", "p"]:
        min_val, max_val = compute_dynamic_range(sec)
        current = user_structure[sec]
        status = "Too few" if current < min_val else ("Too many" if current > max_val else "OK")
        recs.append({"Section": sec.upper(), "Current": current, "Target Min": min_val, "Target Max": max_val, "Action": status})

    st.dataframe(pd.DataFrame(recs))
