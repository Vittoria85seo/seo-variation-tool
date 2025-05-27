
import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import re

st.set_page_config(page_title="SEO Variation Tool", layout="wide")
st.title("SEO Variation & Structure Analyzer")

# Upload fields
st.header("1. Upload Your Page and Competitors")
user_url = st.text_input("Your Page URL")
user_file = st.file_uploader("Upload your HTML file", type="html", key="user")

st.markdown("### Competitors (URL and HTML Upload)")
comp_urls = []
comp_files = []
for i in range(10):
    col1, col2 = st.columns([2, 2])
    with col1:
        url = st.text_input(f"Competitor {i+1} URL", key=f"url_{i}")
    with col2:
        file = st.file_uploader(f"Competitor {i+1} HTML", type="html", key=f"html_{i}")
    if url and file:
        comp_urls.append(url)
        comp_files.append(file)

# Variation input
st.header("2. Enter Variation Terms")
var_input = st.text_area("Enter comma-separated variation phrases", key="variations")
variations = [v.strip().lower() for v in var_input.split(",") if v.strip()]
variation_parts = set()
for v in variations:
    variation_parts.update(v.split())
variation_parts.update(variations)

# Variation regex list
variation_patterns = [re.compile(r'(?<!\w)' + re.escape(var) + r'(?!\w)', re.IGNORECASE) for var in sorted(variation_parts, key=len, reverse=True)]

# Word count
def count_words(soup):
    for s in soup(["script", "style"]):
        s.extract()
    text = soup.get_text(separator=' ', strip=True)
    return len(re.sub(r'\s+', ' ', text).split())

# Variation count logic
def count_variations_by_tag(soup, tag, patterns):
    tags = soup.find_all(tag) if tag != "p" else soup.find_all(["p", "li"])
    total = 0
    for el in tags:
        text = el.get_text(separator=" ", strip=True).lower()
        matched = set()
        used_spans = []
        for pattern in patterns:
            for m in pattern.finditer(text):
                span = m.span()
                if any(s <= span[0] < e or s < span[1] <= e for s, e in used_spans):
                    continue
                used_spans.append(span)
                matched.add(pattern.pattern)
                break
        total += len(matched)
    return total

# Parse and extract all metrics
def analyze_file(html_file):
    soup = BeautifulSoup(html_file.read(), "html.parser")
    wc = count_words(soup)
    return {
        "word_count": wc,
        "h2": count_variations_by_tag(soup, "h2", variation_patterns),
        "h3": count_variations_by_tag(soup, "h3", variation_patterns),
        "h4": count_variations_by_tag(soup, "h4", variation_patterns),
        "p": count_variations_by_tag(soup, "p", variation_patterns)
    }

if user_file and comp_files and variations:
    user_data = analyze_file(user_file)

    comp_data = []
    for file in comp_files:
        comp_data.append(analyze_file(file))

    df_comp = pd.DataFrame(comp_data)
    avg_wc = df_comp["word_count"].mean()
    scale = user_data["word_count"] / avg_wc if avg_wc > 0 else 1.0

    def compute_range(values, section):
        cleaned = sorted(values)
        if section == "p":
            trimmed = cleaned[1:-1] if len(cleaned) > 4 else cleaned
            low, high = np.percentile(trimmed, [10, 90])
        elif section == "h3":
            capped = [min(v, 20) for v in cleaned]
            trimmed = capped[:-1] if len(capped) > 4 else capped
            low, high = np.percentile(trimmed, [10, 90])
        elif section == "h2":
            trimmed = cleaned[:-1] if len(cleaned) > 4 else cleaned
            low, high = np.percentile(trimmed, [10, 90])
        else:
            low, high = 0, 0
        return int(np.floor(low * scale)), int(np.ceil(high * scale))

    st.header("3. Variation Count Results")
    rows = []
    for section in ["h2", "h3", "h4", "p"]:
        comp_vals = df_comp[section].tolist()
        min_val, max_val = compute_range(comp_vals, section)
        current = user_data[section]
        status = "OK" if min_val <= current <= max_val else ("Too few" if current < min_val else "Too many")
        rows.append({
            "Tag": section.upper(),
            "Current": current,
            "Recommended Min": min_val,
            "Recommended Max": max_val,
            "Status": status
        })

    st.dataframe(pd.DataFrame(rows))
