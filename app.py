
import streamlit as st
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
import re

st.title("SEO Variation & Structure Analyzer")

# --- 1. Target URL + file ---
st.header("1. Upload Your Page")
user_url = st.text_input("Enter your page URL")
user_file = st.file_uploader("Upload your HTML file (your page)", type="html", key="user")

# --- 2. Competitor URLs + Files ---
st.header("2. Enter Competitor URLs and Upload Matching HTMLs")
comp_urls_text = st.text_area("Paste 10 competitor URLs (one per line)")
comp_urls = [line.strip() for line in comp_urls_text.strip().splitlines() if line.strip()]

comp_files = []
if len(comp_urls) > 0:
    for i, url in enumerate(comp_urls):
        file = st.file_uploader(f"Upload HTML for Competitor {i+1}: {url}", type="html", key=f"comp_{i}")
        comp_files.append(file)

# --- 3. Variation Terms ---
st.header("3. Enter Variation Terms")
variations_text = st.text_area("Enter comma-separated variation phrases (e.g. fleecejacka herr, fleecetröja)")
variations = [v.strip().lower() for v in variations_text.split(",") if v.strip()]
variation_parts = set()
for v in variations:
    variation_parts.update(v.split())
variation_parts.update(variations)

# --- 4. Competitor Weighting ---
st.header("4. Competitor Weighting")
def default_weights(n): return [round(1.5 - i*0.1, 2) for i in range(n)]
weight_inputs = [st.number_input(f"Weight for Competitor {i+1} ({comp_urls[i] if i < len(comp_urls) else ''})", value=default_weights(len(comp_urls))[i], step=0.1) if i < len(comp_urls) else 1.0 for i in range(len(comp_urls))]

# --- Helper Functions ---
def cleaned_word_count(soup):
    for tag in soup(["script", "style", "noscript"]): tag.extract()
    text = soup.get_text(separator=' ', strip=True)
    text = re.sub(r'\s+', ' ', text)
    return len(text.split())

def count_variations_accurately(soup, tag, variation_list):
    if tag == "p":
        tags = soup.find_all(["p", "li"])
    else:
        tags = soup.find_all(tag)
    total = 0
    sorted_vars = sorted(variation_list, key=lambda x: -len(x))
    for el in tags:
        text = el.get_text(separator=' ', strip=True).lower()
        used_spans = []
        for var in sorted_vars:
            pattern = re.compile(r'(?<!\w)' + re.escape(var) + r'(?!\w)')
            for match in pattern.finditer(text):
                span = match.span()
                if any(s <= span[0] < e or s < span[1] <= e for s, e in used_spans): continue
                used_spans.append(span)
                total += 1
                break
    return total

def extract_counts(file):
    soup = BeautifulSoup(file.read(), "html.parser")
    wc = cleaned_word_count(soup)
    return wc, {
        "h2": count_variations_accurately(soup, "h2", list(variation_parts)),
        "h3": count_variations_accurately(soup, "h3", list(variation_parts)),
        "h4": count_variations_accurately(soup, "h4", list(variation_parts)),
        "p": count_variations_accurately(soup, "p", list(variation_parts))
    }

# --- 5. Compute and Show Results ---
st.header("5. Tag Placement Recommendations")
if user_file and all(f is not None for f in comp_files) and variations:
    user_wc, user_struct = extract_counts(user_file)
    comp_wcs = []
    comp_structs = []

    for f in comp_files:
        wc, struct = extract_counts(f)
        comp_wcs.append(wc)
        comp_structs.append(struct)

    avg_wc = np.average(comp_wcs, weights=weight_inputs)
    scale = user_wc / avg_wc if avg_wc > 0 else 1.0

    def range_for_tag(tag):
        counts = [s[tag] for s in comp_structs]
        counts_sorted = sorted(counts)
        if len(counts_sorted) > 4:
            trimmed = counts_sorted[1:-1]
        else:
            trimmed = counts_sorted
        if tag == "h3":
            trimmed = [min(v, 20) for v in trimmed]
        p10 = np.percentile(trimmed, 10)
        p90 = np.percentile(trimmed, 90)
        return int(np.floor(p10 * scale)), int(np.ceil(p90 * scale))

    results = []
    for tag in ["h2", "h3", "h4", "p"]:
        min_v, max_v = range_for_tag(tag)
        current = user_struct[tag]
        status = "Too few" if current < min_v else ("Too many" if current > max_v else "OK")
        results.append({
            "Tag": tag.upper(),
            "Current Matches": current,
            "Recommended Min": min_v,
            "Recommended Max": max_v,
            "Status": status
        })

    st.dataframe(pd.DataFrame(results))
