
import streamlit as st
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
import re

st.title("SEO Variation & Tag Analyzer")

# --- Upload your page ---
st.header("1. Upload Your Page")
user_url = st.text_input("Enter the URL of your page")
user_file = st.file_uploader("Upload your HTML file (your page)", type="html", key="user")

# --- Upload competitors ---
st.header("2. Competitor Pages")
comp_urls = st.text_area("Enter 10 competitor URLs, one per line").splitlines()
comp_files = []
for i, url in enumerate(comp_urls):
    comp_files.append(st.file_uploader(f"Upload HTML file for Competitor {i+1} ({url})", type="html", key=f"comp_{i}"))

# --- Enter variations ---
st.header("3. Enter Variation Terms")
variation_input = st.text_area("Comma-separated variations (e.g. fleecejacka herr, fleecetröja)")
variation_list = [v.strip().lower() for v in variation_input.split(",") if v.strip()]
variation_parts = list(set(part for v in variation_list for part in v.split()) | set(variation_list))

# --- Calculate word count ---
def word_count(soup):
    for tag in soup(["script", "style"]):
        tag.extract()
    text = soup.get_text(separator=' ')
    return len(text.split())

# --- Count logic ---
def count_variations(soup, tags, variations):
    total = 0
    sorted_vars = sorted(variations, key=lambda x: -len(x))
    for tag in tags:
        for el in soup.find_all(tag):
            text = el.get_text(separator=" ", strip=True).lower()
            used = []
            for var in sorted_vars:
                pattern = re.compile(r'(?<!\w)' + re.escape(var) + r'(?!\w)')
                for m in pattern.finditer(text):
                    span = m.span()
                    if not any(s <= span[0] < e or s < span[1] <= e for s, e in used):
                        used.append(span)
                        total += 1
                        break
    return total

# --- Extract info ---
def extract_counts(file, variations):
    soup = BeautifulSoup(file.read(), "html.parser")
    wc = word_count(soup)
    counts = {
        "h2": count_variations(soup, ["h2"], variations),
        "h3": count_variations(soup, ["h3"], variations),
        "h4": count_variations(soup, ["h4"], variations),
        "p": count_variations(soup, ["p", "li"], variations)
    }
    return wc, counts

# --- Weighting logic ---
def compute_ranges(user_wc, comp_wcs, comp_counts, section):
    scale = user_wc / np.mean(comp_wcs) if comp_wcs else 1.0
    values = [c[section] for c in comp_counts]
    weights = np.array([1.5 - 0.1*i for i in range(len(values))])
    weights = weights / weights.sum()

    sorted_vals = sorted(values)
    trimmed = sorted_vals[1:-1] if len(values) > 4 else sorted_vals
    mean = np.average(trimmed, weights=weights[:len(trimmed)])
    std = np.sqrt(np.average((np.array(trimmed) - mean)**2, weights=weights[:len(trimmed)]))
    low = int(np.floor((mean - 0.5 * std) * scale))
    high = int(np.ceil((mean + 0.5 * std) * scale))
    return max(low, 0), high

# --- Process everything ---
if user_file and variation_list and len(comp_files) == 10 and all(comp_files):
    user_wc, user_counts = extract_counts(user_file, variation_parts)
    comp_wcs = []
    comp_counts = []
    for f in comp_files:
        wc, counts = extract_counts(f, variation_parts)
        comp_wcs.append(wc)
        comp_counts.append(counts)

    st.header("4. Tag Placement Recommendations")
    rows = []
    for tag in ["h2", "h3", "h4", "p"]:
        min_val, max_val = compute_ranges(user_wc, comp_wcs, comp_counts, tag)
        actual = user_counts[tag]
        status = "✅ OK" if min_val <= actual <= max_val else ("⬇️ Too Low" if actual < min_val else "⬆️ Too High")
        rows.append({
            "Tag": tag.upper(),
            "Your Count": actual,
            "Recommended Min": min_val,
            "Recommended Max": max_val,
            "Status": status
        })
    df = pd.DataFrame(rows)
    st.dataframe(df)
