import streamlit as st
import re
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from io import StringIO

st.set_page_config(layout="centered")
st.title("🔍 SEO Variation Analyzer")

st.markdown("### 🧩 Your Page Info")
user_url = st.text_input("User Page URL:")
user_html = st.file_uploader("Upload your HTML file (User Page):", type=["html"])

st.markdown("### 📥 Competitor URLs")
competitor_url_list = st.text_area("Paste list of 10 competitor URLs (one per line):")

comp_urls = [url.strip() for url in competitor_url_list.strip().splitlines() if url.strip()][:10]
comp_codes = []
if comp_urls:
    st.markdown("### 📝 Upload HTML code for each Competitor:")
    for i, url in enumerate(comp_urls):
        uploaded = st.file_uploader(f"Upload Competitor {i+1} ({url}) HTML:", type=["html"], key=f"comp{i}")
        if uploaded:
            comp_codes.append(uploaded.read().decode("utf-8", errors="replace"))
        else:
            comp_codes.append("")

variations_input = st.text_area("📋 Paste variation list (comma-separated):")
tags = ["h2", "h3", "h4", "p"]


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
    detailed_debug = {}
    for tag, blocks in text_blocks.items():
        tag_count = 0
        debug_list = []
        for block in blocks:
            matched_vars = set()
            for v, pattern in patterns:
                if pattern.search(block):
                    matched_vars.add(v)
            tag_count += len(matched_vars)
            debug_list.append({"text": block, "matches": list(matched_vars)})
        counts[tag] = tag_count
        detailed_debug[tag] = debug_list
    return counts, detailed_debug


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

if user_html and len(comp_codes) == 10 and all(comp_codes) and variations_input:
    user_html_str = user_html.read().decode("utf-8", errors="replace")
    variations = [v.strip() for v in variations_input.split(",") if v.strip()]
    user_text = extract_text_by_tag(user_html_str, tags)
    user_counts, user_debug = count_variations(user_text, variations)
    user_wc = get_body_nav_word_count(user_html_str)

    st.header("📌 User Page Analysis")
    st.markdown(f"**User Word Count (Body+Nav):** {user_wc}")
    user_stats = {tag.upper(): user_counts.get(tag, 0) for tag in tags}
    st.dataframe(pd.DataFrame([user_stats]))

    st.header("📦 Competitor Pages Analysis")
    comp_counts = {tag: [] for tag in tags}
    comp_word_counts = []
    ranks = []
    competitor_data = []
    all_debugs = []

    for i, html in enumerate(comp_codes):
        if not html.strip():
            continue
        comp_text = extract_text_by_tag(html, tags)
        comp_wc = get_body_nav_word_count(html)
        comp_word_counts.append(comp_wc)
        comp_variations, comp_debug = count_variations(comp_text, variations)
        ranks.append(i + 1)
        row = {"Competitor": f"Competitor {i+1}", "Word Count": comp_wc}
        for tag in tags:
            row[tag.upper()] = comp_variations.get(tag, 0)
            comp_counts[tag].append(comp_variations.get(tag, 0))
        competitor_data.append(row)
        all_debugs.append({"Competitor": f"Competitor {i+1}", "debug": comp_debug})

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

    with st.expander("🐞 Debug Breakdown - User Block Matches"):
        for tag in tags:
            st.markdown(f"#### Tag: {tag.upper()}")
            for entry in user_debug.get(tag, []):
                st.markdown(f"- **Text:** {entry['text'][:100]}... → **Matches:** {entry['matches']}")

    st.download_button("⬇️ Download Debug JSON", data=pd.DataFrame(all_debugs).to_json(), file_name="debug_output.json")
