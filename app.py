import streamlit as st
from bs4 import BeautifulSoup
import re
import numpy as np

st.set_page_config(page_title="SEO Variation Analyzer", layout="centered")
st.title("SEO Variation Analyzer")

# Upload inputs
user_url = st.text_input("Your Page URL")
user_file = st.file_uploader("Upload your HTML file", type="html", key="user")

# Input all competitor URLs at once
st.markdown("**Enter All 10 Competitor URLs (one per line)**")
url_block = st.text_area("Paste competitor URLs here", height=300)
parsed_urls = [u.strip() for u in url_block.splitlines() if u.strip()]

# Always create 10 upload fields, aligned with parsed_urls or placeholder
comp_urls = parsed_urls + [f"Competitor {i+1}" for i in range(len(parsed_urls), 10)]
comp_files = []

for i, label in enumerate(comp_urls):
    st.markdown(f"**{i+1}. {label}**")
    file = st.file_uploader("Upload HTML for this competitor", type="html", key=f"html_{i}")
    comp_files.append(file)

# Variations
raw_variations = st.text_area("Enter comma-separated variation phrases", height=300)
variations = [v.strip().lower() for v in raw_variations.split(",") if v.strip()]
variation_parts = set()
for v in variations:
    variation_parts.update(v.split())
variation_parts.update(variations)

variation_patterns = [
    re.compile(rf"(?<!\w){re.escape(v)}(?!\w)", re.IGNORECASE)
    for v in sorted(variation_parts, key=len, reverse=True)
]

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
            for pattern in variation_patterns:
                if pattern.search(text):
                    matched.add(pattern.pattern)
            if matched:
                if name in P_TAGS:
                    counts["p"] += len(matched)
                else:
                    counts[name] += len(matched)
    wc = count_words(soup)
    return counts, wc

# Run analysis only when all needed files are present
valid_comp_files = [f for f in comp_files if f is not None]
if user_file and len(valid_comp_files) == 10 and variation_patterns:
    user_counts, user_wc = analyze_file(user_file)
    comp_data = []
    comp_wordcounts = []
    for f in valid_comp_files:
        counts, wc = analyze_file(f)
        comp_data.append(counts)
        comp_wordcounts.append(wc)

    df = {tag: [row[tag] for row in comp_data] for tag in ALL_TAGS}
    weights = np.exp(-np.arange(len(valid_comp_files)))
    weights /= weights.sum()
    wc_avg = np.average(comp_wordcounts, weights=weights)
    ratio = user_wc / wc_avg

    st.subheader("Debug Info")
    st.write(f"Your word count: {user_wc}")
    st.write(f"Competitor avg word count (weighted): {wc_avg:.2f}")
    st.write(f"Ratio: {ratio:.4f}")

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
