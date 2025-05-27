
import streamlit as st
import numpy as np
from bs4 import BeautifulSoup
import pandas as pd
import re

st.title("SEO Variation & Structure Analyzer")

# --- Upload section ---
st.header("1. Upload Your Page and Competitors")
user_file = st.file_uploader("Upload your HTML file (your page)", type="html", key="user")
competitor_files = st.file_uploader("Upload 10 competitor HTML files", type="html", accept_multiple_files=True, key="comps")

# --- Competitor URLs ---
st.header("2. Enter Competitor URLs")
url_text = st.text_area("Enter one competitor URL per line, in the same order as the uploaded files")
competitor_urls = [line.strip() for line in url_text.split("\n") if line.strip()]

# --- Variation input ---
st.header("3. Enter Variation Terms")
variations_text = st.text_area("Enter comma-separated variation phrases (e.g. fleecejacka herr, fleecetröja)")
variations = [v.strip().lower() for v in variations_text.split(",") if v.strip()] if variations_text else []
variation_parts = set()
for v in variations:
    variation_parts.update(v.split())
variation_parts.update(variations)

# --- Weighting ---
st.header("4. Competitor Weighting")
def default_weights(n):
    return [round(1.5 - i*0.1, 2) for i in range(n)]

if competitor_files:
    default_w = default_weights(len(competitor_files))
    weight_inputs = [st.number_input(f"Weight for Competitor {i+1} ({competitor_urls[i] if i < len(competitor_urls) else 'URL missing'})", value=w, step=0.1) for i, w in enumerate(default_w)]
else:
    weight_inputs = []

# --- Word count ---
def cleaned_word_count(soup):
    for script in soup(["script", "style"]):
        script.extract()
    text = soup.get_text(separator=' ', strip=True)
    text = re.sub(r'\s+', ' ', text)
    return len(text.split())

# --- Count logic: each variation counts once per tag, allow overlapping ---
def count_variations_per_tag(soup, tag, variation_list):
    tags = soup.find_all(tag) if tag != "p" else soup.find_all(["p"])
    total = 0
    sorted_vars = sorted(variation_list, key=lambda x: -len(x))
    for el in tags:
        text = el.get_text(separator=' ', strip=True).lower()
        found = set()
        for var in sorted_vars:
            pattern = re.compile(r'(?<!\w)' + re.escape(var) + r'(?!\w)')
            if pattern.search(text):
                found.add(var)
        total += len(found)
    return total

# --- Extract info from file ---
def extract_word_count_and_structure(file):
    content = file.read()
    soup = BeautifulSoup(content, "html.parser")
    word_count = cleaned_word_count(soup)
    structure = {
        "h2": count_variations_per_tag(soup, "h2", list(variation_parts)),
        "h3": count_variations_per_tag(soup, "h3", list(variation_parts)),
        "h4": count_variations_per_tag(soup, "h4", list(variation_parts)),
        "p": count_variations_per_tag(soup, "p", list(variation_parts))
    }
    return word_count, structure

# --- Main logic ---
if user_file and competitor_files and variations:
    user_word_count, user_structure = extract_word_count_and_structure(user_file)
    comp_word_counts = []
    comp_structures = []
    for comp_file in competitor_files:
        wc, struct = extract_word_count_and_structure(comp_file)
        comp_word_counts.append(wc)
        comp_structures.append(struct)

    avg_word_count = np.average(comp_word_counts, weights=weight_inputs)
    scale = user_word_count / avg_word_count if avg_word_count > 0 else 1.0

    def compute_section_range(section):
        counts = [s[section] for s in comp_structures]
        counts_sorted = sorted(counts)

        if section == "p":
            trimmed = counts_sorted[1:-1] if len(counts_sorted) > 4 else counts_sorted
        elif section == "h3":
            capped = [min(v, 20) for v in counts_sorted]
            trimmed = capped[:-1] if len(capped) > 4 else capped
        elif section == "h2":
            trimmed = counts_sorted[:-1] if len(counts_sorted) > 4 else counts_sorted
        else:
            trimmed = counts_sorted

        p10 = np.percentile(trimmed, 10)
        p90 = np.percentile(trimmed, 90)
        return int(np.floor(p10 * scale)), int(np.ceil(p90 * scale))

    # --- Output ---
    st.header("5. Tag Placement Recommendations")
    recs = []
    for sec in ["h2", "h3", "h4", "p"]:
        min_val, max_val = compute_section_range(sec)
        current = user_structure[sec]
        status = "Too few" if current < min_val else ("Too many" if current > max_val else "OK")
        recs.append({
            "Tag": sec.upper(),
            "Current Matches": current,
            "Recommended Min": min_val,
            "Recommended Max": max_val,
            "Status": status
        })

    st.dataframe(pd.DataFrame(recs))
