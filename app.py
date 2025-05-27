import streamlit as st
from bs4 import BeautifulSoup
import re
import numpy as np

st.set_page_config(page_title="SEO Variation Analyzer", layout="centered")
st.title("SEO Variation Analyzer")

# Upload inputs
user_url = st.text_input("Your Page URL")
user_file = st.file_uploader("Upload your HTML file", type="html", key="user")

st.markdown("**Top 10 Competitors**")
comp_urls = []
comp_files = []
for i in range(10):
    url = st.text_input(f"Competitor {i+1} URL", key=f"url_{i}")
    file = st.file_uploader("", type="html", key=f"html_{i}")
    if url and file:
        comp_urls.append(url)
        comp_files.append(file)

# Variations
raw_variations = st.text_area("Enter comma-separated variation phrases")
variations = set(v.strip().lower() for v in raw_variations.split(",") if v.strip())

P_TAGS = {"p", "li"}
HEADINGS = {"h2", "h3", "h4"}
ALL_TAGS = ["h2", "h3", "h4", "p"]

def is_valid(tag):
    parent = tag.find_parent()
    while parent:
        if parent.name == "div" and parent.name not in HEADINGS and parent.name not in P_TAGS:
            return False
        parent = parent.find_parent()
    return True

def get_text(tag):
    return tag.get_text(separator=" ", strip=True).lower()

def count_words(soup):
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator=' ', strip=True)
    return len(re.sub(r'\s+', ' ', text).split())

def analyze_file(file):
    soup = BeautifulSoup(file.read(), "html.parser")
    counts = {"h2": 0, "h3": 0, "h4": 0, "p": 0}
    for tag in soup.find_all(True):
        name = tag.name.lower()
        if name in HEADINGS or name in P_TAGS:
            if not is_valid(tag):
                continue
            text = get_text(tag)
            matched = set()
            for variation in variations:
                if re.search(rf"(?<!\w){re.escape(variation)}(?!\w)", text):
                    matched.add(variation)
            if matched:
                if name in P_TAGS:
                    counts["p"] += len(matched)
                else:
                    counts[name] += len(matched)
    wc = count_words(soup)
    return counts, wc

if user_file and comp_files and variations:
    user_counts, user_wc = analyze_file(user_file)
    comp_data = []
    comp_wordcounts = []
    for f in comp_files:
        counts, wc = analyze_file(f)
        comp_data.append(counts)
        comp_wordcounts.append(wc)

    df = {tag: [row[tag] for row in comp_data] for tag in ALL_TAGS}
    weights = np.exp(-np.arange(len(comp_files)))
    weights /= weights.sum()
    wc_avg = np.average(comp_wordcounts, weights=weights)
    ratio = user_wc / wc_avg

    st.subheader("Results")
    for tag in ALL_TAGS:
        values = np.array(df[tag])
        avg = np.average(values, weights=weights)
        std = np.sqrt(np.average((values - avg) ** 2, weights=weights))
        min_val = round((avg - std) * ratio)
        max_val = round((avg + std) * ratio)
        current = user_counts[tag]
        if current < min_val:
            status = "Add"
        elif current > max_val:
            status = "Reduce"
        else:
            status = "OK"
        st.markdown(f"**{tag.upper()}**: {current} | Range: {min_val}-{max_val} → {status}")
