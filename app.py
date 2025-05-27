
import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import re

st.title("SEO Variation & Competitor Structure Analyzer")

# --- 1. Your Page ---
st.header("1. Your Page")
your_url = st.text_input("Enter your page URL")
your_file = st.file_uploader("Upload your HTML file", type="html", key="your")

# --- 2. Competitor Pages ---
st.header("2. Competitors")
url_text = st.text_area("Enter 10 competitor URLs (one per line, in correct order)")
competitor_urls = [line.strip() for line in url_text.split("\n") if line.strip()]

competitor_files = []
if len(competitor_urls) == 10:
    st.subheader("Upload HTML files for each competitor below:")
    for i, url in enumerate(competitor_urls):
        file = st.file_uploader(f"Upload HTML for Competitor {i+1}: {url}", type="html", key=f"comp{i}")
        competitor_files.append(file)

# --- 3. Variation Terms ---
st.header("3. Enter Variation Terms")
variations_text = st.text_area("Comma-separated variation phrases")
variations = [v.strip().lower() for v in variations_text.split(",") if v.strip()]
variation_parts = set()
for v in variations:
    variation_parts.update(v.split())
variation_parts.update(variations)

# --- 4. Parsing and Count Logic ---
def count_variations(soup, tag, variation_list):
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
                if any(s <= span[0] < e or s < span[1] <= e for s, e in used_spans):
                    continue
                used_spans.append(span)
                total += 1
                break
    return total

def count_all(soup, variation_list):
    return {
        "h2": count_variations(soup, "h2", variation_list),
        "h3": count_variations(soup, "h3", variation_list),
        "h4": count_variations(soup, "h4", variation_list),
        "p": count_variations(soup, "p", variation_list) + count_variations(soup, "li", variation_list)
    }

def get_word_count(soup):
    for tag in soup(["script", "style"]):
        tag.decompose()
    return len(soup.get_text(separator=' ', strip=True).split())

# --- 5. Run Analysis ---
if your_file and all(competitor_files) and variations:
    user_soup = BeautifulSoup(your_file.read(), "html.parser")
    user_word_count = get_word_count(user_soup)
    user_counts = count_all(user_soup, list(variation_parts))

    comp_data = []
    for file in competitor_files:
        soup = BeautifulSoup(file.read(), "html.parser")
        word_count = get_word_count(soup)
        counts = count_all(soup, list(variation_parts))
        counts["word_count"] = word_count
        comp_data.append(counts)

    # Word count scaling
    comp_word_avg = np.mean([c["word_count"] for c in comp_data])
    scale = user_word_count / comp_word_avg if comp_word_avg > 0 else 1.0

    # Compute recommended ranges
    def compute_range(section, values, scale):
        values = sorted(values)
        if section == "p":
            values = values[1:-1] if len(values) > 4 else values
        elif section in ["h2", "h3"]:
            values = [min(v, 20) for v in values]
            values = values[:-1] if len(values) > 4 else values
        p10 = np.percentile(values, 10)
        p90 = np.percentile(values, 90)
        return int(np.floor(p10 * scale)), int(np.ceil(p90 * scale))

    st.header("4. Results")
    output = []
    for tag in ["h2", "h3", "h4", "p"]:
        values = [c[tag] for c in comp_data]
        min_val, max_val = compute_range(tag, values, scale)
        user_val = user_counts[tag]
        status = "✅ OK" if min_val <= user_val <= max_val else ("⬇ Too few" if user_val < min_val else "⬆ Too many")
        output.append({
            "Tag": tag.upper(),
            "Your Matches": user_val,
            "Recommended Min": min_val,
            "Recommended Max": max_val,
            "Status": status
        })

    st.dataframe(pd.DataFrame(output))
