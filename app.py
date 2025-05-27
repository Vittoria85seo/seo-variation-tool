
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

# --- Match logic with non-overlapping variations, prefer longest, no <div> ---
def count_variations_strict(soup, tag, variation_list):
    tags = soup.find_all(tag) if tag != "p" else soup.find_all(["p", "li"])
    total = 0
    sorted_vars = sorted(variation_list, key=lambda x: -len(x))
    for el in tags:
        text = el.get_text(separator=' ', strip=True).lower()
        used_spans = []
        for var in sorted_vars:
            pattern = re.compile(r'(?<!\w)' + re.escape(var) + r'(?!\w)')
            for match in pattern.finditer(text):
                span = match.span()
                if any(s <= span[0] < e or s < span[1] <= e for s, e in used_spans):
                    continue
                used_spans.append(span)
                total += 1
                break
    return total

# --- Extract structure and word count ---
def extract_info(file):
    content = file.read()
    soup = BeautifulSoup(content, "html.parser")
    word_count = cleaned_word_count(soup)
    structure = {
        "h2": count_variations_strict(soup, "h2", list(variation_parts)),
        "h3": count_variations_strict(soup, "h3", list(variation_parts)),
        "h4": count_variations_strict(soup, "h4", list(variation_parts)),
        "p": count_variations_strict(soup, "p", list(variation_parts))
    }
    return word_count, structure

# --- Range calculation logic ---
def compute_range(values, scale, section):
    values = sorted(values)
    if section == "p":
        trimmed = values[1:-1] if len(values) > 4 else values
    elif section == "h3":
        capped = [min(v, 20) for v in values]
        trimmed = capped[:-1] if len(capped) > 4 else capped
    elif section == "h2":
        trimmed = values[:-1] if len(values) > 4 else values
    else:
        trimmed = values
    p10 = np.percentile(trimmed, 10)
    p90 = np.percentile(trimmed, 90)
    return int(np.floor(p10 * scale)), int(np.ceil(p90 * scale))

# --- Main processing ---
if user_file and competitor_files and variations:
    user_wc, user_struct = extract_info(user_file)
    comp_wcs, comp_structs = [], []
    for f in competitor_files:
        wc, s = extract_info(f)
        comp_wcs.append(wc)
        comp_structs.append(s)
    avg_wc = np.average(comp_wcs, weights=weight_inputs)
    scale = user_wc / avg_wc if avg_wc > 0 else 1.0

    st.header("5. Tag Placement Recommendations")
    results = []
    for sec in ["h2", "h3", "h4", "p"]:
        vals = [s[sec] for s in comp_structs]
        min_v, max_v = compute_range(vals, scale, sec)
        current = user_struct[sec]
        status = "Too few" if current < min_v else ("Too many" if current > max_v else "OK")
        results.append({
            "Tag": sec.upper(),
            "Current Matches": current,
            "Recommended Min": min_v,
            "Recommended Max": max_v,
            "Status": status
        })
    st.dataframe(pd.DataFrame(results))
