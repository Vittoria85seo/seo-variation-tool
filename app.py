
import streamlit as st
import numpy as np
from bs4 import BeautifulSoup
import pandas as pd
import re

st.title("SEO Variation Analyzer")

# --- Upload user file ---
st.header("1. Your Page")
user_url = st.text_input("Your Page URL")
user_file = st.file_uploader("Upload your HTML file", type="html", key="user")

# --- Competitor section ---
st.header("2. Competitors")
st.markdown("Upload each competitor file with its URL in order")

comp_urls = []
comp_files = []
for i in range(10):
    url = st.text_input(f"Competitor {i+1} URL", key=f"url_{i}")
    file = st.file_uploader(f"Upload HTML for Competitor {i+1}", type="html", key=f"file_{i}")
    if url and file:
        comp_urls.append(url)
        comp_files.append(file)

# --- Variations ---
st.header("3. Variation Terms")
variations_text = st.text_area("Enter comma-separated variation phrases")
variations = [v.strip().lower() for v in variations_text.split(",") if v.strip()]
variation_parts = set()
for v in variations:
    variation_parts.update(v.split())
variation_parts.update(variations)

# --- Count logic ---
def count_variations(soup, tag, variation_list):
    if tag == "p":
        tags = soup.find_all(["p", "li"])
    else:
        tags = soup.find_all(tag)
    total = 0
    sorted_vars = sorted(variation_list, key=lambda x: -len(x))
    for el in tags:
        text = el.get_text(separator=' ', strip=True).lower()
        found = set()
        used_spans = []
        for var in sorted_vars:
            pattern = re.compile(r'(?<!\w)' + re.escape(var) + r'(?!\w)')
            for match in pattern.finditer(text):
                span = match.span()
                if any(s <= span[0] < e or s < span[1] <= e for s, e in used_spans):
                    continue
                used_spans.append(span)
                found.add(var)
                break
        total += len(found)
    return total

def word_count(soup):
    for script in soup(["script", "style"]): script.extract()
    text = soup.get_text(separator=' ', strip=True)
    return len(re.sub(r'\s+', ' ', text).split())

# --- Processing ---
def process_file(file, variation_parts):
    soup = BeautifulSoup(file.read(), "html.parser")
    return {
        "word_count": word_count(soup),
        "h2": count_variations(soup, "h2", variation_parts),
        "h3": count_variations(soup, "h3", variation_parts),
        "h4": count_variations(soup, "h4", variation_parts),
        "p": count_variations(soup, "p", variation_parts)
    }

# --- Analyze and show ---
if user_file and comp_files and variations:
    st.header("4. Analysis")

    user_data = process_file(user_file, variation_parts)
    comp_data = [process_file(f, variation_parts) for f in comp_files]

    avg_wc = np.mean([c["word_count"] for c in comp_data])
    scale = user_data["word_count"] / avg_wc if avg_wc else 1.0

    def compute_range(values, section, scale):
        values_sorted = sorted(values)
        if section == "p":
            trimmed = values_sorted[1:-1] if len(values_sorted) > 4 else values_sorted
        elif section == "h3":
            capped = [min(v, 20) for v in values_sorted]
            trimmed = capped[:-1] if len(capped) > 4 else capped
        elif section == "h2":
            trimmed = values_sorted[:-1] if len(values_sorted) > 4 else values_sorted
        else:
            trimmed = values_sorted
        p10 = np.percentile(trimmed, 10)
        p90 = np.percentile(trimmed, 90)
        return int(np.floor(p10 * scale)), int(np.ceil(p90 * scale))

    final_table = []
    for sec in ["h2", "h3", "h4", "p"]:
        values = [c[sec] for c in comp_data]
        min_v, max_v = compute_range(values, sec, scale)
        current = user_data[sec]
        status = "✅" if min_v <= current <= max_v else ("⬆️ too high" if current > max_v else "⬇️ too low")
        final_table.append({
            "Tag": sec.upper(),
            "Your Count": current,
            "Recommended Min": min_v,
            "Recommended Max": max_v,
            "Status": status
        })

    st.subheader("Tag Recommendations")
    st.dataframe(pd.DataFrame(final_table))
