import streamlit as st
from bs4 import BeautifulSoup
import re

st.title("SEO Variation Analyzer (Standardized Math)")

# User inputs
html_file = st.file_uploader("Upload your HTML file", type="html")
user_wc = st.number_input("Your page word count", min_value=1, value=1101)
avg_wc = st.number_input("Competitor average word count", min_value=1, value=2922)

# Input variations
raw_variations = st.text_area("Enter comma-separated variation phrases")
variations = set(v.strip().lower() for v in raw_variations.split(",") if v.strip())

# Input raw min/max ranges
st.markdown("### Enter competitor min/max per tag")
raw_min = {
    "h2": st.number_input("Min H2", value=0),
    "h3": st.number_input("Min H3", value=0),
    "h4": st.number_input("Min H4", value=0),
    "p": st.number_input("Min P/LI", value=0),
}
raw_max = {
    "h2": st.number_input("Max H2", value=0),
    "h3": st.number_input("Max H3", value=0),
    "h4": st.number_input("Max H4", value=0),
    "p": st.number_input("Max P/LI", value=0),
}

if html_file and variations:
    soup = BeautifulSoup(html_file.read(), "html.parser")
    variation_counts = {"h2": 0, "h3": 0, "h4": 0, "p": 0}
    P_TAGS = {"p", "li"}
    HEADINGS = {"h2", "h3", "h4"}

    def is_valid(tag):
        parent = tag.find_parent()
        while parent:
            if parent.name == "div" and parent.name not in HEADINGS and parent.name not in P_TAGS:
                return False
            parent = parent.find_parent()
        return True

    def get_text_content(tag):
        return tag.get_text(separator=" ", strip=True).lower()

    for tag in soup.find_all(True):
        tag_name = tag.name.lower()
        if tag_name in HEADINGS or tag_name in P_TAGS:
            if not is_valid(tag):
                continue
            text = get_text_content(tag)
            matched = set()
            for variation in variations:
                if re.search(rf"(?<!\\w){re.escape(variation)}(?!\\w)", text):
                    matched.add(variation)
            # Deduplicate by tag level (variation only counted once per tag block)
            if tag_name in P_TAGS:
                variation_counts["p"] += len(matched)
            elif tag_name in HEADINGS:
                variation_counts[tag_name] += len(matched)

    ratio = user_wc / avg_wc
    scaled_ranges = {
        tag: (round(ratio * raw_min[tag]), round(ratio * raw_max[tag])) for tag in ["h2", "h3", "h4", "p"]
    }

    st.markdown("### Results")
    for tag in ["h2", "h3", "h4", "p"]:
        my_count = variation_counts[tag]
        low, high = scaled_ranges[tag]
        if my_count < low:
            status = "Add"
        elif my_count > high:
            status = "Reduce"
        else:
            status = "OK"
        st.write(f"**{tag.upper()}** — Yours: {my_count} | Range: {low}-{high} → {status}")
