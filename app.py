
import streamlit as st
import numpy as np
import pandas as pd
import re
from bs4 import BeautifulSoup

st.title("SEO Variation Analyzer")

# --- Section 1: Upload User Page ---
st.header("1. Upload Your Page")
user_url = st.text_input("Your Page URL")
user_file = st.file_uploader("Upload your page HTML", type="html", key="user")

# --- Section 2: Competitor Setup ---
st.header("2. Competitor Setup")
st.markdown("Enter 10 competitor URLs (in order):")
url_text = st.text_area("One URL per line", height=180)
competitor_urls = [line.strip() for line in url_text.splitlines() if line.strip()]
competitor_files = []
if len(competitor_urls) > 0:
    st.markdown("Upload HTML for each competitor (in the same order):")
    for i, url in enumerate(competitor_urls):
        f = st.file_uploader(f"HTML for Competitor {i+1}: {url}", type="html", key=f"comp_{i}")
        competitor_files.append(f)

# --- Section 3: Variation Terms ---
st.header("3. Enter Variation Terms")
variation_input = st.text_area("Comma-separated variations", placeholder="e.g. fleecejacka herr, fleecejacka, herr")
variations = [v.strip().lower() for v in variation_input.split(",") if v.strip()]
variation_parts = set()
for v in variations:
    variation_parts.update(v.split())
variation_parts.update(variations)
sorted_variations = sorted(variation_parts, key=len, reverse=True)

# --- Weight Calculation ---
def get_weights(n):
    w = [1.5 - i * 0.1 for i in range(n)]
    total = sum(w)
    return [x / total for x in w]

# --- Word Count ---
def word_count(soup):
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return len(text.split())

# --- Variation Count Logic ---
def count_variations_by_tag(soup, tags, patterns, variations):
    total = 0
    for tag in tags:
        for el in soup.find_all(tag):
            if tag in ["p", "li"] and (el.get("class") or el.get("id")):
                continue
            text = el.get_text(separator=' ', strip=True).lower()
            found = set()
            for pattern, var in zip(patterns, variations):
                if pattern.search(text):
                    found.add(var)
            total += len(found)
    return total

# --- Parse File ---
def parse_html(file, patterns, variations):
    content = file.read()
    soup = BeautifulSoup(content, "html.parser")
    wc = word_count(soup)
    return {
        "word_count": wc,
        "h2": count_variations_by_tag(soup, ["h2"], patterns, variations),
        "h3": count_variations_by_tag(soup, ["h3"], patterns, variations),
        "h4": count_variations_by_tag(soup, ["h4"], patterns, variations),
        "p": count_variations_by_tag(soup, ["p", "li"], patterns, variations)
    }

# --- Section 4: Output ---
if user_file and all(competitor_files) and variations:
    patterns = [re.compile(r'(?<!\w)' + re.escape(v) + r'(?!\w)', re.IGNORECASE) for v in sorted_variations]
    user_data = parse_html(user_file, patterns, sorted_variations)

    comp_data = [parse_html(f, patterns, sorted_variations) for f in competitor_files]
    weights = get_weights(len(comp_data))
    avg_word_count = np.average([c["word_count"] for c in comp_data], weights=weights)
    scale = user_data["word_count"] / avg_word_count if avg_word_count else 1

    def compute_range(section):
        values = [c[section] for c in comp_data]
        trimmed = sorted(values)
        if section == "p" and len(trimmed) > 4:
            trimmed = trimmed[1:-1]
        elif section == "h3":
            trimmed = [min(v, 20) for v in trimmed]
            if len(trimmed) > 4:
                trimmed = trimmed[:-1]
        elif section == "h2":
            if len(trimmed) > 4:
                trimmed = trimmed[:-1]
        p10 = np.percentile(trimmed, 10)
        p90 = np.percentile(trimmed, 90)
        return int(np.floor(p10 * scale)), int(np.ceil(p90 * scale))

    st.header("4. Results")
    results = []
    for tag in ["h2", "h3", "h4", "p"]:
        min_r, max_r = compute_range(tag)
        current = user_data[tag]
        status = "✅ OK" if min_r <= current <= max_r else ("⬇️ Too Low" if current < min_r else "⬆️ Too High")
        results.append({
            "Tag": tag.upper(),
            "Current": current,
            "Min Recommended": min_r,
            "Max Recommended": max_r,
            "Status": status
        })
    st.dataframe(pd.DataFrame(results))
