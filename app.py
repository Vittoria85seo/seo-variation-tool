import streamlit as st
import re
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from io import StringIO

def extract_text_by_tag(html_str, tags):
    soup = BeautifulSoup(html_str, "html.parser")
    for tag in ["script", "style", "noscript", "template", "svg"]:
        for el in soup.find_all(tag):
            el.decompose()
    for el in soup.find_all(attrs={"aria-label": True}):
        el.decompose()
    text_blocks = {tag: [] for tag in tags}
    for tag in tags:
        for el in soup.find_all(tag):
            text = el.get_text(" ", strip=True)
            if text:
                text_blocks[tag].append(text)
    return text_blocks

def get_body_nav_word_count(html_str):
    soup = BeautifulSoup(html_str, "html.parser")
    for tag in ["script", "style", "noscript", "template", "svg"]:
        for el in soup.find_all(tag):
            el.decompose()
    for el in soup.find_all(attrs={"aria-label": True}):
        el.decompose()
    texts = []
    for tag in ["body", "nav"]:
        for el in soup.find_all(tag):
            t = el.get_text(" ", strip=True)
            if t:
                texts.append(t)
    return len(" ".join(texts).split())

def count_variations(text_blocks, variations):
    counts = {}
    sorted_vars = sorted(set(variations), key=len, reverse=True)
    patterns = [(v, re.compile(rf"(?<![\\w-]){re.escape(v)}(?=[\\W]|$)", re.IGNORECASE)) for v in sorted_vars]
    for tag, blocks in text_blocks.items():
        tag_count = 0
        for block in blocks:
            matched_vars = set()
            for v, pattern in patterns:
                if pattern.search(block):
                    matched_vars.add(v)
            tag_count += len(matched_vars)
        counts[tag] = tag_count
    return counts

def soft_weighted_range(arr, ranks, user_wc, comp_avg_wc, tag):
    arr = np.array(arr)
    ranks = np.array(ranks)
    weights = (11 - ranks) ** 2
    scaled = arr * (user_wc / comp_avg_wc)
    weighted = scaled * weights
    mean = weighted.sum() / weights.sum()
    if tag == "p":
        std = 4.62
    elif tag == "h2":
        std = 0.5
    elif tag == "h3":
        std = 1.5
    else:
        std = 0
    rmin = int(max(0, mean - std))
    rmax = int(mean + std)
    return rmin, rmax

st.set_page_config(layout="wide")
st.title("🔍 SEO Variation Analyzer")

url_col, code_col = st.columns([1, 3])

with url_col:
    st.markdown("### 🧩 Your Page Info")
    user_url = st.text_input("User Page URL:")
    comp_urls = []
    for i in range(10):
        url = st.text_input(f"Competitor {i+1} URL:", key=f"cu{i}")
        comp_urls.append(url)

with code_col:
    user_html = st.text_area("Paste your HTML code (User Page):", height=300)
    comp_codes = []
    for i in range(10):
        code = st.text_area(f"Paste HTML code for Competitor {i+1}:", height=200, key=f"cc{i}")
        comp_codes.append(code)

variations_input = st.text_area("Paste variation list (comma-separated):")
tags = ["h2", "h3", "h4", "p"]

if user_html and all(comp_codes) and variations_input:
    variations = [v.strip() for v in variations_input.split(",") if v.strip()]
    user_text = extract_text_by_tag(user_html, tags)
    user_counts = count_variations(user_text, variations)
    user_wc = get_body_nav_word_count(user_html)

    st.header("📌 User Page Analysis")
    st.markdown(f"**User Word Count (Body+Nav):** {user_wc}")
    user_stats = {tag.upper(): user_counts.get(tag, 0) for tag in tags}
    st.dataframe(pd.DataFrame([user_stats]))

    st.header("📦 Competitor Pages Analysis")
    comp_counts = {tag: [] for tag in tags}
    comp_word_counts = []
    ranks = []
    competitor_data = []

    for i, html in enumerate(comp_codes):
        if not html.strip():
            continue
        comp_text = extract_text_by_tag(html, tags)
        comp_wc = get_body_nav_word_count(html)
        comp_word_counts.append(comp_wc)
        comp_variations = count_variations(comp_text, variations)
        ranks.append(i + 1)
        row = {"Competitor": f"Competitor {i+1}", "Word Count": comp_wc}
        for tag in tags:
            row[tag.upper()] = comp_variations.get(tag, 0)
            comp_counts[tag].append(comp_variations.get(tag, 0))
        competitor_data.append(row)

    df_comp = pd.DataFrame(competitor_data)
    st.dataframe(df_comp)

    comp_avg_wc = np.mean(comp_word_counts)

    results = []
    for tag in tags:
        rmin, rmax = soft_weighted_range(comp_counts[tag], ranks, user_wc, comp_avg_wc, tag)
        results.append({
            "Tag": tag.upper(),
            "Your Count": user_counts.get(tag, 0),
            "Scaled Min": rmin,
            "Scaled Max": rmax,
            "In Range": rmin <= user_counts.get(tag, 0) <= rmax
        })

    st.header("📊 Final Range Comparison")
    df = pd.DataFrame(results)
    st.dataframe(df)

    st.download_button("⬇️ Download Full Competitor Data", data=df_comp.to_csv(index=False), file_name="competitor_data.csv")
    st.download_button("⬇️ Download Range Summary", data=df.to_csv(index=False), file_name="range_analysis.csv")
