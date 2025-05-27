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

# Strict word-boundary match (no parts of words)
variation_patterns = [
    re.compile(rf"(?<!\w){re.sub(r'\s+', ' ', re.escape(v)).replace('\\ ', ' ')}(?!\w)", re.IGNORECASE)
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
    try:
        file.seek(0)
    except Exception:
        pass
    try:
        raw = file.read()
        try:
            decoded = raw.decode("utf-8")
        except:
            decoded = raw.decode("latin1")
        soup = BeautifulSoup(decoded, "html.parser")
    except Exception as e:
        st.error(f"Failed to parse HTML: {e}")
        return {"h2": 0, "h3": 0, "h4": 0, "p": 0}, 0, {"h2": [], "h3": [], "h4": [], "p": []}

    counts = {"h2": 0, "h3": 0, "h4": 0, "p": 0}
    matches_per_tag = {"h2": [], "h3": [], "h4": [], "p": []}
    tag_debug_list = []
    try:
        for tag in soup.find_all(True):
            name = tag.name.lower()
            if name in HEADINGS or name in P_TAGS:
                if not is_valid(tag):
                    continue
                text = get_text(tag)
                count = 0
                used_spans = []
                found = []
                for pattern in variation_patterns:
                    for m in pattern.finditer(text):
                        span = m.span()
                        if any(s <= span[0] < e or s < span[1] <= e for s, e in used_spans):
                            continue
                        used_spans.append(span)
                        count += 1
                        found.append(m.group())
                tag_debug_list.append((name, text))
                if count:
                    tag_key = "p" if name in P_TAGS else name
                    counts[tag_key] += count
                    matches_per_tag[tag_key].extend(found)
    except Exception as e:
        st.error(f"Failed during tag processing: {e}")

    try:
        wc = count_words(soup)
    except Exception as e:
        st.error(f"Failed to count words: {e}")
        wc = 0

    if tag_debug_list:
        st.subheader("First 10 visible tags from parsed HTML")
        st.json(tag_debug_list[:10])

    return counts, wc, matches_per_tag
