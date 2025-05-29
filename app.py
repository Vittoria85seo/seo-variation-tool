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
    for tag, blocks in text_blocks.items():
        count = 0
        for block in blocks:
            for v in variations:
                pattern = rf'(?<![\w-]){re.escape(v)}(?=[\W]|$)'
                matches = re.findall(pattern, block, re.IGNORECASE)
                if matches:
                    st.write(f"[DEBUG] Matched variation '{v}' in <{tag}> block: '{block[:60]}...'")
                count += len(matches)
        counts[tag] = count
        st.write(f"[DEBUG] Total count for <{tag}>: {count}")
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
    st.write(f"[DEBUG] Tag: {tag}, Mean: {mean:.2f}, Range: {rmin}-{rmax}")
    return rmin, rmax

st.title("🔍 Variation Analyzer")

user_html = st.text_area("Paste your HTML here:", height=300)
variations_input = st.text_area("Paste variation list (comma-separated):")
uploaded_files = st.file_uploader("Upload competitor HTML files", type="html", accept_multiple_files=True)

if user_html and uploaded_files and variations_input:
    variations = [v.strip() for v in variations_input.split(",") if v.strip()]
    tags = ["h2", "h3", "h4", "p"]

    st.header("📌 User Page Analysis")
    user_text = extract_text_by_tag(user_html, tags)
    user_counts = count_variations(user_text, variations)
    user_wc = get_body_nav_word_count(user_html)
    st.markdown(f"**User Word Count:** {user_wc}")

    st.markdown("**Tag Counts:**")
    col1, col2 = st.columns(2)
    with col1:
        for tag in tags[:2]:
            st.markdown(f"- **{tag.upper()}**: {user_counts.get(tag, 0)}")
    with col2:
        for tag in tags[2:]:
            st.markdown(f"- **{tag.upper()}**: {user_counts.get(tag, 0)}")

    st.header("📦 Competitor Analysis")
    comp_counts = {tag: [] for tag in tags}
    comp_word_counts = []
    ranks = []
    competitor_data = []

    for i, file in enumerate(uploaded_files):
        html = file.read().decode("utf-8")
        comp_text = extract_text_by_tag(html, tags)
        comp_wc = get_body_nav_word_count(html)
        comp_word_counts.append(comp_wc)
        comp_variations = count_variations(comp_text, variations)
        ranks.append(i)
        row = {
            "Competitor": file.name,
            "Word Count": comp_wc
        }
        for tag in tags:
            val = comp_variations.get(tag, 0)
            comp_counts[tag].append(val)
            row[tag.upper()] = val
        competitor_data.append(row)

    df_comp = pd.DataFrame(competitor_data)
    st.dataframe(df_comp)

    comp_avg_wc = np.mean(comp_word_counts)
    st.write(f"[DEBUG] Competitor average word count: {comp_avg_wc:.2f}")

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

    st.header("📊 Final Range Analysis")
    df = pd.DataFrame(results)
    st.dataframe(df)

    st.download_button("Download Range Data", data=df.to_csv(index=False), file_name="range_analysis.csv")
    st.download_button("Download Competitor Raw Data", data=df_comp.to_csv(index=False), file_name="competitor_data.csv")
