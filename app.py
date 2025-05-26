
import streamlit as st
import numpy as np
from bs4 import BeautifulSoup
import pandas as pd
import re

st.title("SEO Variation & Structure Analyzer")

# --- Upload section ---
st.header("1. Upload Files")
user_file = st.file_uploader("Upload your HTML file", type="html", key="user")
competitor_files = st.file_uploader("Upload competitor HTML files (10 max)", type="html", accept_multiple_files=True, key="comps")

# --- Variation input ---
st.header("2. Enter Variations List")
variations_text = st.text_area("Enter comma-separated variations")
variations = [v.strip().lower() for v in variations_text.split(",") if v.strip()] if variations_text else []
variation_parts = set()
for v in variations:
    parts = v.split()
    variation_parts.update(parts)
variation_parts.update(variations)

# --- Weighting ---
st.header("3. Adjust Competitor Weighting (Top to Bottom Rank)")
def default_weights(n):
    return [round(1.5 - i*0.1, 2) for i in range(n)]

if competitor_files:
    default_w = default_weights(len(competitor_files))
    weight_inputs = [st.number_input(f"Weight for Competitor {i+1}", value=w, step=0.1) for i, w in enumerate(default_w)]
else:
    weight_inputs = []

# --- Word count function ---
def cleaned_word_count(soup):
    for script in soup(["script", "style"]):
        script.extract()
    text = soup.get_text(separator=' ', strip=True)
    text = re.sub(r'\s+', ' ', text)
    return len(text.split())

# --- Variation match count ---
def count_variation_matches(soup, tag, variation_set):
    tags = soup.find_all(tag) if tag != "p" else soup.find_all(["p", "li"])
    count = 0
    for el in tags:
        text = el.get_text(separator=' ', strip=True).lower()
        found = set()
        for var in variation_set:
            pattern = r'(?<!\w)' + re.escape(var) + r'(?!\w)'
            matches = re.findall(pattern, text)
            if matches:
                found.update([var]*len(matches))
        count += len(found)
    return count

# --- Extract data ---
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
    return word_count, structure

# --- Main logic ---
if user_file and competitor_files and variations:
    user_word_count, user_structure = extract_word_count_and_sections(user_file)

    comp_word_counts = []
    comp_structures = []
    for comp_file in competitor_files:
        wc, struct = extract_word_count_and_sections(comp_file)
        comp_word_counts.append(wc)
        comp_structures.append(struct)

    avg_word_count = np.average(comp_word_counts, weights=weight_inputs)

    def compute_dynamic_range(section):
        section_counts = np.array([s[section] for s in comp_structures])
        mean = np.average(section_counts, weights=weight_inputs)
        std = np.sqrt(np.average((section_counts - mean) ** 2, weights=weight_inputs))
        scale = user_word_count / avg_word_count if avg_word_count > 0 else 1.0
        min_val = max(0, int(np.floor((mean - 0.8 * std) * scale)))
        max_val = int(np.ceil((mean + 0.8 * std) * scale))
        return min_val, max_val

    st.subheader("Tag Placement Recommendations (Variation Match Count)")
    recs = []
    for sec in ["h2", "h3", "h4", "p"]:
        min_val, max_val = compute_dynamic_range(sec)
        current = user_structure[sec]
        status = "Too few" if current < min_val else ("Too many" if current > max_val else "OK")
        recs.append({
            "Section": sec.upper(),
            "Current": current,
            "Target Min": min_val,
            "Target Max": max_val,
            "Status": status
        })

    st.dataframe(pd.DataFrame(recs))
