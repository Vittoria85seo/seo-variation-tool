
import streamlit as st
import numpy as np
from bs4 import BeautifulSoup
import pandas as pd
import re

st.title("SEO Variation & Structure Analyzer")

# --- Your Page ---
st.header("1. Your Page")
user_url = st.text_input("Your page URL")
user_file = st.file_uploader("Upload your HTML file (your page)", type="html", key="user")

# --- Competitor URLs and Files ---
st.header("2. Competitors")
comp_url_text = st.text_area("Enter 10 competitor URLs, one per line")
comp_urls = [line.strip() for line in comp_url_text.split("\n") if line.strip()]

comp_files = []
for i in range(10):
    label = f"Upload HTML for Competitor {i+1} ({comp_urls[i] if i < len(comp_urls) else 'URL missing'})"
    uploaded = st.file_uploader(label, type="html", key=f"comp_{i}")
    comp_files.append(uploaded)

# --- Variations ---
st.header("3. Variation Terms")
variations_text = st.text_area("Enter comma-separated variation phrases (e.g. fleecejacka herr, fleecetröja)")
variations = [v.strip().lower() for v in variations_text.split(",") if v.strip()] if variations_text else []
variation_parts = set()
for v in variations:
    variation_parts.update(v.split())
variation_parts.update(variations)

# --- Word Count ---
def cleaned_word_count(soup):
    for script in soup(["script", "style"]):
        script.extract()
    text = soup.get_text(separator=' ', strip=True)
    text = re.sub(r'\s+', ' ', text)
    return len(text.split())

# --- Accurate Count Function ---
def count_variations_per_tag(soup, tag, variation_list):
    tags = soup.find_all(tag) if tag != "p" else soup.find_all(["p", "li"])
    total = 0
    sorted_vars = sorted(variation_list, key=lambda x: -len(x))
    for el in tags:
        text = el.get_text(separator=' ', strip=True).lower()
        used_spans = []
        for var in sorted_vars:
            pattern = re.compile(r'(?<!\w)' + re.escape(var) + r'(?!\w)')
            for match in pattern.finditer(text):
                span = match.span()
                if any(s <= span[0] < e or s < span[1] <= e for s, e in used_spans):
                    continue
                used_spans.append(span)
                total += 1
                break
    return total

# --- Extract Tag Data ---
def extract_structure(file, variation_list):
    soup = BeautifulSoup(file.read(), "html.parser")
    wc = cleaned_word_count(soup)
    data = {
        "h2": count_variations_per_tag(soup, "h2", variation_list),
        "h3": count_variations_per_tag(soup, "h3", variation_list),
        "h4": count_variations_per_tag(soup, "h4", variation_list),
        "p": count_variations_per_tag(soup, "p", variation_list),
        "word_count": wc
    }
    return data

# --- Analysis ---
if user_file and all(comp_files) and variations:
    user_data = extract_structure(user_file, list(variation_parts))
    comp_data = [extract_structure(f, list(variation_parts)) for f in comp_files]

    comp_df = pd.DataFrame(comp_data)
    avg_wc = comp_df["word_count"].mean()
    scale = user_data["word_count"] / avg_wc if avg_wc > 0 else 1.0

    st.header("4. Tag Placement Recommendations")

    def compute_range(values, section):
        values = sorted(values)
        if section == "p":
            trimmed = values[1:-1] if len(values) > 4 else values
            p10 = np.percentile(trimmed, 10)
            p90 = np.percentile(trimmed, 90)
        elif section == "h3":
            capped = [min(v, 20) for v in values]
            trimmed = capped[:-1] if len(capped) > 4 else capped
            p10 = np.percentile(trimmed, 10)
            p90 = np.percentile(trimmed, 90)
        elif section == "h2":
            trimmed = values[:-1] if len(values) > 4 else values
            p10 = np.percentile(trimmed, 10)
            p90 = np.percentile(trimmed, 90)
        else:
            p10 = np.percentile(values, 10)
            p90 = np.percentile(values, 90)
        return int(np.floor(p10 * scale)), int(np.ceil(p90 * scale))

    rows = []
    for section in ["h2", "h3", "h4", "p"]:
        values = comp_df[section].tolist()
        min_r, max_r = compute_range(values, section)
        user_val = user_data[section]
        status = "Too few" if user_val < min_r else ("Too many" if user_val > max_r else "OK")
        rows.append({
            "Tag": section.upper(),
            "Your Count": user_val,
            "Recommended Min": min_r,
            "Recommended Max": max_r,
            "Status": status
        })

    st.dataframe(pd.DataFrame(rows))
