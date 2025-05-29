@@ -1,12 +1,12 @@
# Final Streamlit App (fully verified)
import streamlit as st
import pandas as pd
import numpy as np
import re
from bs4 import BeautifulSoup
import json

st.set_page_config(layout="centered")
st.title("SEO Variation Distribution Tool - FIXED PARSING + DEBUG")
st.title("SEO Variation Distribution Tool")

user_url = st.text_input("Your Page URL")
user_file = st.file_uploader("Upload Your Page HTML", type="html", key="user_html")
@@ -24,7 +24,7 @@
variations_input = st.text_area("Enter variation terms (comma-separated)")
variations = [v.strip().lower() for v in variations_input.split(",") if v.strip()]

# ========== CORE UTILITY FUNCTIONS ==========

def extract_tag_texts(html_str):
soup = BeautifulSoup(html_str, "html.parser")
for tag in ["script", "style", "noscript", "template", "svg"]:
@@ -41,10 +41,12 @@ def extract_tag_texts(html_str):
word_count = len(" ".join(sum(texts.values(), [])).split())
return texts, word_count


def count_variations(texts, variations):
sorted_vars = sorted(set(variations), key=len, reverse=True)
patterns = [(v, re.compile(rf"(?<!\\w){re.escape(v)}(?=(?:\\s?[^\\w<]|$))", re.IGNORECASE)) for v in sorted_vars]
counts = {"h2": 0, "h3": 0, "h4": 0, "p": 0}

for tag in texts:
for txt in texts[tag]:
matched = set()
@@ -54,6 +56,18 @@ def count_variations(texts, variations):
counts[tag] += len(matched)
return counts


def per_variation_counts_all(html_str, variations):
    soup = BeautifulSoup(html_str, "html.parser")
    full_text = soup.get_text(" ", strip=True)
    sorted_vars = sorted(set(variations), key=len, reverse=True)
    patterns = [(v, re.compile(rf"(?<!\\w){re.escape(v)}(?=(?:\\s?[^\\w<]|$))", re.IGNORECASE)) for v in sorted_vars]
    var_counts = {v: 0 for v in variations}
    for var, pattern in patterns:
        var_counts[var] = len(pattern.findall(full_text))
    return var_counts


def benchmark_ranges_weighted(tag_counts_dict, user_wc, comp_wcs, weights):
result = {}
avg_wc = np.average(comp_wcs, weights=weights)
@@ -74,39 +88,25 @@ def benchmark_ranges_weighted(tag_counts_dict, user_wc, comp_wcs, weights):
result[tag] = (min_v, max_v)
return result

# ========== MAIN LOGIC EXECUTION ==========
debug_log = {"user_read_success": False, "competitor_reads": [], "user_counts": {}, "comp_counts": [], "errors": []}

if user_file:
    try:
        user_html_bytes = user_file.read()
        user_html = user_html_bytes.decode("utf-8", errors="replace")
        debug_log["user_read_success"] = True
        user_texts, user_wc = extract_tag_texts(user_html)
        user_counts = count_variations(user_texts, variations)
        debug_log["user_counts"] = user_counts
    except Exception as e:
        debug_log["errors"].append(f"User HTML parse error: {str(e)}")
        user_wc = 0
        user_counts = {"h2": 0, "h3": 0, "h4": 0, "p": 0}

comp_counts = []
comp_wcs = []
if len(competitor_files) == 10 and all(competitor_files):
    for i, f in enumerate(competitor_files):
        try:
            html = f.read().decode("utf-8", errors="replace")
            texts, wc = extract_tag_texts(html)
            count = count_variations(texts, variations)
            comp_wcs.append(wc)
            comp_counts.append(count)
            debug_log["competitor_reads"].append({"index": i, "success": True, "wc": wc, "counts": count})
        except Exception as e:
            debug_log["competitor_reads"].append({"index": i, "success": False, "error": str(e)})
            comp_wcs.append(0)
            comp_counts.append({"h2": 0, "h3": 0, "h4": 0, "p": 0})

if user_counts and comp_counts:
if user_file and len(competitor_files) == 10 and all(competitor_files) and variations:
    user_html = user_file.read().decode("utf-8")
    user_texts, user_wc = extract_tag_texts(user_html)
    user_counts = count_variations(user_texts, variations)
    user_per_var = per_variation_counts_all(user_html, variations)

    comp_counts = []
    comp_wcs = []
    comp_var_totals = {v: [] for v in variations}

    for f in competitor_files:
        html = f.read().decode("utf-8")
        texts, wc = extract_tag_texts(html)
        comp_wcs.append(wc)
        cvc = per_variation_counts_all(html, variations)
        for v in variations:
            comp_var_totals[v].append(cvc[v])
        comp_counts.append(count_variations(texts, variations))

tag_counts_dict = {tag: [c[tag] for c in comp_counts] for tag in ["h2", "h3", "h4", "p"]}
fixed_weights = [1.5, 1.4, 1.3, 1.2, 1.1, 1.0, 0.9, 0.8, 0.7, 0.6]
ranges = benchmark_ranges_weighted(tag_counts_dict, user_wc, comp_wcs, fixed_weights)
@@ -117,9 +117,14 @@ def benchmark_ranges_weighted(tag_counts_dict, user_wc, comp_wcs, weights):
"Recommended Min": [ranges[t][0] for t in ["h2", "h3", "h4", "p"]],
"Recommended Max": [ranges[t][1] for t in ["h2", "h3", "h4", "p"]]
}

st.subheader("Final Analysis")
st.dataframe(pd.DataFrame(df_data))

st.subheader("Downloadable Debug Output")
debug_json = json.dumps(debug_log, indent=2)
st.download_button("Download Debug JSON", debug_json, file_name="debug_output.json")
    st.subheader("Variation Count Table")
    var_data = {
        "Variation": variations,
        "C = User Count": [user_per_var[v] for v in variations],
        "A = Avg Competitor Count": [round(np.mean(comp_var_totals[v]), 2) for v in variations]
    }
    st.dataframe(pd.DataFrame(var_data))
