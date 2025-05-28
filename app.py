# Final Streamlit App (layout with proper URL + staged competitor upload)
import streamlit as st
import pandas as pd
import numpy as np
import re
from bs4 import BeautifulSoup

st.set_page_config(layout="centered")
st.title("SEO Variation Distribution Tool")

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


def extract_tag_texts(html_str):
    soup = BeautifulSoup(html_str, "html.parser")
    for tag in ["script", "style", "noscript"]:
        for match in soup.find_all(tag):
            match.decompose()
    texts = {
        "h2": [el.get_text(" ", strip=True) for el in soup.find_all("h2")],
        "h3": [el.get_text(" ", strip=True) for el in soup.find_all("h3")],
        "h4": [el.get_text(" ", strip=True) for el in soup.find_all("h4")],
        "p":  [el.get_text(" ", strip=True) for el in soup.find_all(["p", "li"])]
    }
    word_count = len(soup.get_text(" ", strip=True).split())
    return texts, word_count

def count_variations(texts, variations):
    counts = {"h2": 0, "h3": 0, "h4": 0, "p": 0}
    sorted_vars = sorted(set(variations), key=len, reverse=True)
    var_patterns = [(v, re.compile(rf"(?<!\w){re.escape(v)}(?=[\s\.,:;!?\-]|$)", flags=re.IGNORECASE)) for v in sorted_vars]
    for tag in counts:
        for txt in texts[tag]:
            used_spans = []
            matched = set()
            for var, pattern in var_patterns:
                for match in pattern.finditer(txt):
                    span = match.span()
                    if any(start < span[1] and end > span[0] for start, end in used_spans):
                        continue
                    used_spans.append(span)
                    matched.add(var)
                    break
            counts[tag] += len(matched)
    return counts

def weighted_percentile(data, weights, percentiles):
    data, weights = np.array(data), np.array(weights)
    sorter = np.argsort(data)
    data_sorted = data[sorter]
    weights_sorted = weights[sorter]
    cum_weights = np.cumsum(weights_sorted)
    total = cum_weights[-1]
    percentile_values = []
    for p in percentiles:
        cutoff = total * (p / 100.0)
        idx = np.searchsorted(cum_weights, cutoff)
        idx = min(len(data_sorted) - 1, idx)
        percentile_values.append(data_sorted[idx])
    return percentile_values

def compute_variation_ranges(tag_counts_dict, user_wc, avg_wc, weights):
    result = {}
    scale = user_wc / avg_wc if avg_wc else 1.0
    for tag, counts in tag_counts_dict.items():
        min_v, max_v = weighted_percentile(counts, weights, [10, 90])
        if tag == "p":
            min_adj = int(np.floor(min_v * scale))
            max_adj = int(np.ceil(max_v * scale))
        else:
            min_adj = int(np.floor(min_v))
            max_adj = int(np.ceil(max_v))
        result[tag] = (min_adj, max_adj)
    return result

if user_file and len(competitor_files) == 10 and all(competitor_files) and variations:
    user_html = user_file.read().decode("utf-8")
    user_texts, user_wc = extract_tag_texts(user_html)
    user_counts = count_variations(user_texts, variations)

    comp_counts = []
    comp_wcs = []
    for f in competitor_files:
        html = f.read().decode("utf-8")
        texts, wc = extract_tag_texts(html)
        comp_wcs.append(wc)
        comp_counts.append(count_variations(texts, variations))

    avg_comp_wc = np.mean(comp_wcs)
    tag_counts_dict = {tag: [c[tag] for c in comp_counts] for tag in ["h2", "h3", "h4", "p"]}
    fixed_weights = [1.5, 1.4, 1.3, 1.2, 1.1, 1.0, 0.9, 0.8, 0.7, 0.6]
    ranges = compute_variation_ranges(tag_counts_dict, user_wc, avg_comp_wc, weights=fixed_weights)

    df_data = {
        "Tag": ["H2", "H3", "H4", "P"],
        "Your Count": [user_counts[t] for t in ["h2", "h3", "h4", "p"]],
        "Recommended Min": [ranges[t][0] for t in ["h2", "h3", "h4", "p"]],
        "Recommended Max": [ranges[t][1] for t in ["h2", "h3", "h4", "p"]]
    }

    st.subheader("Final Analysis")
    st.dataframe(pd.DataFrame(df_data))
