
import streamlit as st
import numpy as np
import pandas as pd
import re
from bs4 import BeautifulSoup

st.title("SEO Variation Tool — Verified Logic")

# Step 1: Upload your target page
st.header("1. Your Page")
your_url = st.text_input("Enter your target page URL")
your_file = st.file_uploader("Upload your page's HTML", type="html")

# Step 2: Enter competitors
st.header("2. Competitors")
comp_urls = []
comp_files = []

st.text("Enter exactly 10 competitor URLs below, then upload matching HTMLs one-by-one in order:")

url_input = st.text_area("Paste 10 competitor URLs (one per line)")
comp_urls = [line.strip() for line in url_input.splitlines() if line.strip()]
comp_files = st.file_uploader("Upload matching competitor HTMLs (in same order)", type="html", accept_multiple_files=True)

# Step 3: Variation terms
st.header("3. Variation phrases")
variations_text = st.text_area("Comma-separated variation phrases", value="fleecetröja herr,fleece herr,fleece,herr,fleecejacka herr,fleecejackor,fleecejacka,fleecetröjor,fleecejackor herr,för män,fleece för herr,fleecetröja,herrar,fleecens,fleecetröjor till herr,fleecetröjor för män,herr fleecetröja,fleecetröjor för herr,fleecetröjans,fleecetröja för herr,herrfleecetröjor,män,fleece tröja herr,fleecejackorna,tröjor,herr-fleecetröjor,fleecejackornas,herr fleece tröja,för herrar,fleecejackans,fleecetröja för män,för herr,fleecetröjan,fleecetröjor - herr,tröja,fleece tröja,fleecen,herr fleece,fleecetröjorna,herr fleecejacka,fleecejackan,fleecetröjornas,herrfleecetröja")
variations = [v.strip().lower() for v in variations_text.split(",") if v.strip()]

variation_patterns = [re.compile(r'(?<!\w)' + re.escape(v) + r'(?!\w)', re.IGNORECASE) for v in sorted(variations, key=lambda x: -len(x))]

# Match logic with non-overlap per tag
def count_variations(soup, tags):
    result = {"h2": 0, "h3": 0, "h4": 0, "p": 0}
    for tag in tags:
        elements = soup.find_all(tag)
        for el in elements:
            text = el.get_text(separator=' ', strip=True).lower()
            used_spans = []
            for pattern in variation_patterns:
                for match in pattern.finditer(text):
                    span = match.span()
                    if any(s <= span[0] < e or s < span[1] <= e for s, e in used_spans):
                        continue
                    used_spans.append(span)
                    result[tag] += 1
                    break
    return result

def count_p_li(soup):
    count = 0
    for el in soup.find_all(["p", "li"]):
        text = el.get_text(separator=' ', strip=True).lower()
        used_spans = []
        for pattern in variation_patterns:
            for match in pattern.finditer(text):
                span = match.span()
                if any(s <= span[0] < e or s < span[1] <= e for s, e in used_spans):
                    continue
                used_spans.append(span)
                count += 1
                break
    return count

def extract_structure_and_wc(file):
    soup = BeautifulSoup(file.read(), "html.parser")
    counts = count_variations(soup, ["h2", "h3", "h4"])
    counts["p"] = count_p_li(soup)
    for s in soup(["script", "style"]):
        s.extract()
    text = soup.get_text(separator=" ", strip=True)
    word_count = len(re.sub(r'\s+', ' ', text).split())
    return word_count, counts

# Word count scaling + weighted percentile range
def compute_weighted_range(counts_list, weights, user_wc, avg_wc, tag, cap=None):
    counts = np.array([min(x[tag], cap) if cap else x[tag] for x in counts_list])
    if len(counts) < 3:
        return (0, max(counts) if len(counts) else 0)
    scale = user_wc / avg_wc if avg_wc > 0 else 1.0
    p10 = np.percentile(counts, 10)
    p90 = np.percentile(counts, 90)
    return int(np.floor(p10 * scale)), int(np.ceil(p90 * scale))

if your_file and len(comp_files) == 10 and len(comp_urls) == 10:
    user_wc, user_struct = extract_structure_and_wc(your_file)
    comp_wcs = []
    comp_structs = []

    for file in comp_files:
        wc, struct = extract_structure_and_wc(file)
        comp_wcs.append(wc)
        comp_structs.append(struct)

    weights = [round(1.5 - i * 0.1, 2) for i in range(10)]
    avg_wc = np.average(comp_wcs, weights=weights)

    st.header("4. Results — Counts & Ranges")
    summary = []
    for tag in ["h2", "h3", "h4", "p"]:
        cap = 20 if tag == "h3" else None
        min_v, max_v = compute_weighted_range(comp_structs, weights, user_wc, avg_wc, tag, cap)
        user_val = user_struct[tag]
        status = "Too few" if user_val < min_v else ("Too many" if user_val > max_v else "OK")
        summary.append({
            "Tag": tag.upper(),
            "Current": user_val,
            "Recommended Min": min_v,
            "Recommended Max": max_v,
            "Status": status
        })

    st.dataframe(pd.DataFrame(summary))

else:
    st.warning("Please make sure to upload 1 target HTML, exactly 10 competitor files, and paste 10 URLs.")
