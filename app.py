import streamlit as st
import numpy as np
import pandas as pd
import re
from bs4 import BeautifulSoup

st.title("SEO Variation & Structure Analyzer")

# --- Upload and Input Section ---
st.header("1. Upload Your Page")
user_file = st.file_uploader("Upload your HTML file (your page)", type="html", key="user")

st.header("2. Your Page URL")
user_url = st.text_input("Enter the URL of your page")

st.header("3. Enter Variation Terms")
variations_text = st.text_area("Comma-separated variations (e.g. fleecejacka herr, fleecetröja)")
variations = [v.strip().lower() for v in variations_text.split(",") if v.strip()]
variation_parts = set()
for v in variations:
    variation_parts.update(v.split())
variation_parts.update(variations)

st.header("4. Upload Competitor Data")
competitor_urls_text = st.text_area("Enter 10 competitor URLs, one per line")
competitor_urls = [line.strip() for line in competitor_urls_text.split("
") if line.strip()]
competitor_files = []
for i, url in enumerate(competitor_urls):
    competitor_files.append(st.file_uploader(f"Upload HTML for Competitor {i+1}: {url}", type="html", key=f"comp_{i}"))

# --- Utility Functions ---
def cleaned_word_count(soup):
    for script in soup(["script", "style"]):
        script.extract()
    text = soup.get_text(separator=' ', strip=True)
    return len(re.sub(r'\s+', ' ', text).split())

def count_variations_strict(soup, tag, variation_list):
    tags = soup.find_all(tag) if tag != "p" else soup.find_all(["p", "li"])
    total = 0
    sorted_vars = sorted(variation_list, key=lambda x: -len(x))
    for el in tags:
        text = el.get_text(separator=' ', strip=True).lower()
        found = set()
        for var in sorted_vars:
            pattern = re.compile(r'(?<!\w)' + re.escape(var) + r'(?!\w)')
            if pattern.search(text):
                found.add(var)
        total += len(found)
    return total

def extract_counts(file, variation_list):
    content = file.read()
    soup = BeautifulSoup(content, "html.parser")
    wc = cleaned_word_count(soup)
    return {
        "word_count": wc,
        "h2": count_variations_strict(soup, "h2", variation_list),
        "h3": count_variations_strict(soup, "h3", variation_list),
        "h4": count_variations_strict(soup, "h4", variation_list),
        "p": count_variations_strict(soup, "p", variation_list),
    }

# --- Analysis ---
if user_file and variations and len(competitor_files) == 10:
    user_data = extract_counts(user_file, list(variation_parts))
    comp_data = [extract_counts(f, list(variation_parts)) for f in competitor_files]
    avg_word_count = np.mean([c["word_count"] for c in comp_data])
    scale = user_data["word_count"] / avg_word_count if avg_word_count else 1.0

    weights = np.array([1.5 - 0.1*i for i in range(10)])
    weights /= weights.sum()

    def compute_range(section):
        raw = np.array([c[section] for c in comp_data])
        if section == "p":
            trimmed = sorted(raw)[1:-1]
        elif section in ["h2", "h3"]:
            trimmed = sorted(np.minimum(raw, 20))[:-1]
        else:
            trimmed = raw
        avg = np.average(trimmed, weights=weights[:len(trimmed)])
        std = np.sqrt(np.average((trimmed - avg)**2, weights=weights[:len(trimmed)]))
        min_val = max(0, int(np.floor((avg - 0.5 * std) * scale)))
        max_val = int(np.ceil((avg + 0.5 * std) * scale))
        return min_val, max_val

    st.header("5. Tag Placement Recommendations")
    recs = []
    for section in ["h2", "h3", "h4", "p"]:
        min_v, max_v = compute_range(section)
        val = user_data[section]
        status = "✅ OK" if min_v <= val <= max_v else ("⬇ Too Low" if val < min_v else "⬆ Too High")
        recs.append({
            "Tag": section.upper(),
            "Your Count": val,
            "Recommended Min": min_v,
            "Recommended Max": max_v,
            "Status": status
        })

    st.dataframe(pd.DataFrame(recs))
