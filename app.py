import streamlit as st
import pandas as pd
import numpy as np
import re
from bs4 import BeautifulSoup
import json

st.set_page_config(layout="centered")
st.title("SEO Variation Distribution Tool - FIXED PARSING + DEBUG")

user_url = st.text_input("Your Page URL")
user_file = st.file_uploader("Upload Your Page HTML", type="html", key="user_html")

competitor_urls_input = st.text_area("Enter Top 10 Competitor URLs (one per line)")
competitor_urls = [u.strip() for u in competitor_urls_input.strip().splitlines() if u.strip()]

competitor_files = []
if len(competitor_urls) == 10:
    st.subheader("Upload Corresponding Competitor HTML Files (in order of URLs above)")
    for i, url in enumerate(competitor_urls):
        f = st.file_uploader(f"Competitor {i+1}: {url}", type="html", key=f"comp{i}")
        competitor_files.append(f)

variations_input = st.text_area("Enter variation terms (comma-separated)")
variations = [v.strip().lower() for v in variations_input.split(",") if v.strip()]

# ========== CORE UTILITY FUNCTIONS ==========
def extract_tag_texts(html_str):
    soup = BeautifulSoup(html_str, "html.parser")
    for tag in ["script", "style", "noscript", "template", "svg"]:
        for match in soup.find_all(tag):
            match.decompose()
    for el in soup.find_all(attrs={"aria-label": True}):
        el.decompose()
    texts = {
        "h2": [el.get_text(" ", strip=True) for el in soup.find_all("h2")],
        "h3": [el.get_text(" ", strip=True) for el in soup.find_all("h3")],
        "h4": [el.get_text(" ", strip=True) for el in soup.find_all("h4")],
        "p":  [el.get_text(" ", strip=True) for el in soup.find_all(["p", "li"])]
    }
    word_count = len(" ".join(sum(texts.values(), [])).split())
    return texts, word_count

def count_variations(texts, variations):
    sorted_vars = sorted(set(variations), key=len, reverse=True)
    # Updated regex: allows whole words or phrases followed by punctuation or end
    patterns = [(v, re.compile(rf"(?<!\w){re.escape(v)}(?=[\s\.,;:!?\)])|(?<!\w){re.escape(v)}$", re.IGNORECASE)) for v in sorted_vars]
    counts = {"h2": 0, "h3": 0, "h4": 0, "p": 0}
    for tag in texts:
        for txt in texts[tag]:
            matched = set()
            for var, pattern in patterns:
                if pattern.search(txt):
                    matched.add(var)
            counts[tag] += len(matched)
    return counts

def benchmark_ranges_weighted(tag_counts_dict, user_wc, comp_wcs, weights):
    result = {}
    avg_wc = np.average(comp_wcs, weights=weights)
    scale = user_wc / avg_wc if avg_wc else 1.0
    for tag, counts in tag_counts_dict.items():
        weighted_avg = np.average(counts, weights=weights)
        stddev = np.sqrt(np.average((np.array(counts) - weighted_avg) ** 2, weights=weights))
        spread = 0.15 if tag == "p" else 0.25
        lo = weighted_avg - spread * stddev
        hi = weighted_avg + spread * stddev
        min_v = int(np.floor(lo * scale))
        max_v = int(np.ceil(hi * scale))
        min_v = max(min_v, 0)
        max_v = max(max_v, 0)
        if tag == "h4" and all(v == 0 for v in counts):
            result[tag] = (0, 0)
        else:
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
    tag_counts_dict = {tag: [c[tag] for c in comp_counts] for tag in ["h2", "h3", "h4", "p"]}
    fixed_weights = [1.5, 1.4, 1.3, 1.2, 1.1, 1.0, 0.9, 0.8, 0.7, 0.6]
    ranges = benchmark_ranges_weighted(tag_counts_dict, user_wc, comp_wcs, fixed_weights)

    df_data = {
        "Tag": ["H2", "H3", "H4", "P"],
        "Your Count": [user_counts[t] for t in ["h2", "h3", "h4", "p"]],
        "Recommended Min": [ranges[t][0] for t in ["h2", "h3", "h4", "p"]],
        "Recommended Max": [ranges[t][1] for t in ["h2", "h3", "h4", "p"]]
    }
    st.subheader("Final Analysis")
    st.dataframe(pd.DataFrame(df_data))

st.subheader("Downloadable Debug Output")
debug_json = json.dumps(debug_log, indent=2)
st.download_button("Download Debug JSON", debug_json, file_name="debug_output.json")
