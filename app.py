import streamlit as st
import pandas as pd
import numpy as np
import re
from bs4 import BeautifulSoup
import json

st.set_page_config(layout="centered")
st.title("SEO Variation Distribution Tool - FINALIZED")

# === PAGE INPUTS ===
user_url = st.text_input("Your Page URL")
user_file = st.file_uploader("Upload Your Page HTML", type="html", key="user_html")

competitor_urls_input = st.text_area("Enter Top 10 Competitor URLs (one per line)")
competitor_urls = [u.strip() for u in competitor_urls_input.strip().splitlines() if u.strip()]

st.subheader("Upload Corresponding Competitor HTML Files")
competitor_files = []
for i in range(10):
    url_display = competitor_urls[i] if i < len(competitor_urls) else f"Competitor {i+1}"
    f = st.file_uploader(f"Competitor {i+1}: {url_display}", type="html", key=f"comp_{i}")
    competitor_files.append(f)

variations_input = st.text_area("Enter variation terms (comma-separated)")
variations = [v.strip().lower() for v in variations_input.split(",") if v.strip()]
if not variations:
    st.warning("No variation terms provided.")

# ========== CORE UTILITY FUNCTIONS ==========
def extract_tag_texts(html_str):
    soup = BeautifulSoup(html_str, "html.parser")
    for tag in ["script", "style", "noscript", "template", "svg"]:
        for match in soup.find_all(tag):
            match.decompose()
    for el in soup.find_all(attrs={"aria-label": True}):
        el.decompose()

    texts = {
        "h2": [el.get_text(" ", strip=True) for el in soup.find_all("h2")],
        "h3": [el.get_text(" ", strip=True) for el in soup.find_all("h3")],
        "h4": [el.get_text(" ", strip=True) for el in soup.find_all("h4")],
        "p":  [el.get_text(" ", strip=True) for el in soup.find_all(["p", "li"])]
    }

    body = soup.find("body")
    nav = soup.find("nav")

    body_text = ""
    if body:
        for tag in body(["script", "style", "noscript", "template", "svg"]):
            tag.extract()
        for el in body.find_all(attrs={"aria-label": True}):
            el.extract()
        body_text += body.get_text(" ", strip=True)

    if nav:
        for tag in nav(["script", "style", "noscript", "template", "svg"]):
            tag.extract()
        for el in nav.find_all(attrs={"aria-label": True}):
            el.extract()
        body_text += " " + nav.get_text(" ", strip=True)

    # Fallback: also parse visible strings not caught
    visible_texts = soup.stripped_strings
    all_text = " ".join(visible_texts)

    nav_text = nav.get_text(" ", strip=True) if nav else ""
    word_count = len((body_text + " " + nav_text).split())
    return texts, word_count

def count_variations(texts, variations):
    sorted_vars = sorted(set(variations), key=len, reverse=True)
    patterns = [(v, re.compile(rf"(?<!\w){re.escape(v)}(?=[\s\.,;:!\?)])|(?<!\w){re.escape(v)}$", re.IGNORECASE)) for v in sorted_vars]
    counts = {"h2": 0, "h3": 0, "h4": 0, "p": 0}
    for tag in texts:
        for txt in texts[tag]:
            matched = set()
            for var, pattern in patterns:
                if pattern.search(txt):
                    matched.add(var)
            counts[tag] += len(matched)
    return counts

def benchmark_ranges_weighted(tag_counts_dict, user_word_count, comp_word_counts, weights):
    result = {}
    avg_wc = np.average(comp_word_counts, weights=weights)
    scale = user_word_count / avg_wc if avg_wc else 1.0

    for tag, counts in tag_counts_dict.items():
        if tag == "h3":
            counts_filtered = [v for v in counts if v < 10]
            weights_filtered = weights[:len(counts_filtered)]
            weighted_avg = np.average(counts_filtered, weights=weights_filtered) if counts_filtered else 0
            low = 0.3 * weighted_avg * scale
            high = 0.6 * weighted_avg * scale
        elif tag == "p":
            weighted_avg = np.average(counts, weights=weights)
            low = 0.9 * weighted_avg * scale
            high = 1.1 * weighted_avg * scale
        else:
            weighted_avg = np.average(counts, weights=weights)
            if tag == "h2":
                low = 0.3 * weighted_avg * scale
                high = 0.7 * weighted_avg * scale
            else:
                low = 0.8 * weighted_avg * scale
                high = 1.2 * weighted_avg * scale

        if tag == "h3":
            low = 0.3 * weighted_avg * scale
            high = 0.6 * weighted_avg * scale
        elif tag == "h2":
            low = 0.3 * weighted_avg * scale
            high = 0.7 * weighted_avg * scale
        elif tag == "p":
            low = 1.3 * weighted_avg * scale
            high = 1.6 * weighted_avg * scale
        else:
            low = 0.8 * weighted_avg * scale
            high = 1.2 * weighted_avg * scale

        min_v = max(int(np.floor(low)), 0)
        max_v = max(int(np.ceil(high)), 0)
        if tag == "h4" and all(v == 0 for v in counts):
            result[tag] = (0, 0)
        else:
            result[tag] = (min_v, max_v)
    return result

# ========== MAIN LOGIC EXECUTION ==========
debug_log = {"user_read_success": False, "competitor_reads": [], "user_counts": {}, "comp_counts": [], "errors": []}

user_word_count = 0
user_counts = {"h2": 0, "h3": 0, "h4": 0, "p": 0}

if user_file:
    try:
        user_html_bytes = user_file.read()
        if not user_html_bytes:
            raise ValueError("User file is empty or failed to read.")
        user_html = user_html_bytes.decode("utf-8", errors="replace")
        debug_log["user_read_success"] = True
        user_texts, user_word_count = extract_tag_texts(user_html)
        user_counts = count_variations(user_texts, variations)
        debug_log["user_counts"] = user_counts
        debug_log["user_counts"]["word_count"] = user_word_count

        st.subheader("User HTML Debug Info")
        st.write("Total body word count:", user_word_count)
        st.write("Extracted tag counts:", {tag: len(user_texts[tag]) for tag in user_texts})
        st.write("Variation match counts:", user_counts)

    except Exception as e:
        st.error(f"Error parsing user file: {str(e)}")
        debug_log["errors"].append(f"User HTML parse error: {str(e)}")

comp_counts = []
# manual_p_variation_counts removed
comp_word_counts = []
valid_comp_files = [f for f in competitor_files if f]
if len(valid_comp_files) < 10:
    st.warning("Please upload all 10 competitor HTML files.")

if len(valid_comp_files) == 10:
    for i in range(10):
        f = competitor_files[i]
        try:
            if f is None:
                raise ValueError("File missing.")
            html_bytes = f.getvalue()
            if not html_bytes:
                raise ValueError("Empty file content.")
            html = html_bytes.decode("utf-8", errors="replace")
            texts, wc = extract_tag_texts(html)
            count = count_variations(texts, variations)
            comp_word_counts.append(wc)
            comp_counts.append(count)
            debug_log["competitor_reads"].append({"index": i, "url": competitor_urls[i] if i < len(competitor_urls) else f"Competitor {i+1}", "success": True, "wc": wc, "counts": count})

            st.subheader(f"Competitor {i+1} Debug Info")
# st.write("URL:", competitor_urls[i] if i < len(competitor_urls) else f"Competitor {i+1}")
            st.write("Total body word count:", wc)
            st.write("Extracted tag counts:", {tag: len(texts[tag]) for tag in texts})
            st.write("Variation match counts:", count)

        except Exception as e:
            st.error(f"Competitor {i+1} file error: {str(e)}")
            debug_log["competitor_reads"].append({"index": i, "success": False, "error": str(e)})
            comp_word_counts.append(0)
            comp_counts.append({"h2": 0, "h3": 0, "h4": 0, "p": 0})

if any(user_counts.values()) and comp_counts:
    tag_counts_dict = {tag: [c[tag] for c in comp_counts] for tag in ["h2", "h3", "h4", "p"]}
    fixed_weights = [1.5, 1.4, 1.3, 1.2, 1.1, 1.0, 0.9, 0.8, 0.7, 0.6]
    ranges = benchmark_ranges_weighted(tag_counts_dict, user_word_count, comp_word_counts, fixed_weights)
    debug_log["recommended_ranges"] = ranges
    debug_log["competitor_h3_averages"] = tag_counts_dict["h3"]

    df_data = {
        "Tag": ["H2", "H3", "H4", "P"],
        "Your Count": [user_counts[t] for t in ["h2", "h3", "h4", "p"]],
        "Recommended Min": [ranges[t][0] for t in ["h2", "h3", "h4", "p"]],
        "Recommended Max": [ranges[t][1] for t in ["h2", "h3", "h4", "p"]]
    }
    st.subheader("Final Analysis")
    st.dataframe(pd.DataFrame(df_data))
st.subheader("Downloadable Debug Output")
debug_json = json.dumps(debug_log, indent=2)
st.download_button("Download Debug JSON", debug_json, file_name="debug_output.json")
