import streamlit as st
import json
from bs4 import BeautifulSoup
import math
import base64
import io

def compute_benchmark_ranges(user_html, competitor_data, coefficients):

    def weighted_avg(values):
        weights = [1.6, 1.5, 1.4, 1.3, 1.2, 1.0, 0.8, 0.6, 0.5, 0.4]
        return sum(v * w for v, w in zip(values, weights)) / sum(weights)

    def compute_word_count(html):
        soup = BeautifulSoup(html, "html.parser")
        return len(soup.get_text().split())

    user_word_count = compute_word_count(user_html)
    word_counts = [c["word_count"] for c in competitor_data]
    avg_word_count = sum(word_counts) / len(word_counts)
    scale = user_word_count / avg_word_count

    h2_vals = [c["variation_counts"]["h2"] for c in competitor_data]
    h3_vals = [c["variation_counts"]["h3"] for c in competitor_data]
    h4_vals = [c["variation_counts"]["h4"] for c in competitor_data]
    p_vals = [c["variation_counts"]["p"] for c in competitor_data]

    h2_avg = round(weighted_avg(h2_vals), 1)
    h3_avg = round(weighted_avg(h3_vals), 1)
    h4_avg = round(weighted_avg(h4_vals), 1)
    p_avg = round(weighted_avg(p_vals), 1)

    def force_zero_floor(values, default_floor):
        top4 = sorted(values, reverse=True)[:4]
        return 0 if top4.count(0) >= 2 else default_floor

    ranges = {}
    ranges["h2"] = (
        max(0, math.floor(coefficients["h2"][0] * h2_avg * scale)),
        math.ceil(coefficients["h2"][1] * h2_avg * scale)
    )
    h3_floor = force_zero_floor(h3_vals, math.floor(coefficients["h3"][0] * h3_avg * scale))
    ranges["h3"] = (
        max(0, h3_floor),
        math.ceil(coefficients["h3"][1] * h3_avg * scale)
    )
    h4_scaled = coefficients["h4"][0] * h4_avg * scale
    if h4_scaled < 0.5:
        ranges["h4"] = (0, 0)
    else:
        ranges["h4"] = (
            max(0, math.floor(h4_scaled)),
            math.ceil(coefficients["h4"][1] * h4_avg * scale)
        )
    ranges["p"] = (
        max(0, math.floor(coefficients["p"][0] * p_avg * scale)),
        math.ceil(coefficients["p"][1] * p_avg * scale)
    )

    return ranges

st.title("SEO Variation Range Calculator")

user_url = st.text_input("User Page URL")
user_html = st.file_uploader("Upload User HTML File", type=["html"])

competitor_urls = st.text_area("Paste Competitor URLs (1 per line)").splitlines()
competitor_html_files = []

if len(competitor_urls) == 10:
    st.subheader("Upload HTML for Each Competitor")
    for i, url in enumerate(competitor_urls):
        uploaded = st.file_uploader(f"Upload HTML for Competitor {i+1}: {url}", type=["html"], key=f"c{i}")
        competitor_html_files.append(uploaded)
else:
    st.warning("Please enter exactly 10 competitor URLs.")

with st.form("variation_form"):
    variations_input = st.text_area("Enter Variations (comma-separated)")
    submitted = st.form_submit_button("Compute Variation Ranges")

if submitted:
    variation_list = [v.strip() for v in variations_input.split(",") if v.strip()]
    user_html_content = user_html.read().decode("utf-8") if user_html else None
    competitor_contents = [f.read().decode("utf-8") if f else None for f in competitor_html_files]

    if user_html_content and all(competitor_contents) and len(variation_list) > 0:
        try:
            competitor_data = []
            for html in competitor_contents:
                soup = BeautifulSoup(html, "html.parser")
                word_count = len(soup.get_text().split())
                variation_counts = {tag: 0 for tag in ["h2", "h3", "h4", "p"]}

                for tag in variation_counts:
                    tags = soup.find_all(tag)
                    count = 0
                    for t in tags:
                        text = t.get_text(separator=" ").lower()
                        for var in variation_list:
                            var = var.lower()
                            words = text.split()
                            count += sum(1 for word in words if word == var)
                    variation_counts[tag] = count

                competitor_data.append({"word_count": word_count, "variation_counts": variation_counts})

            coefficients = {
                "h2": (1.3, 2.0),
                "h3": (0.4, 1.75),
                "h4": (0.6, 1.5),
                "p": (1.1, 1.5)
            }
            ranges = compute_benchmark_ranges(user_html_content, competitor_data, coefficients)
            st.subheader("Recommended Variation Ranges")
            st.json(ranges)

            # Hidden debug download logic
            debug_data = {
                "user_word_count": len(user_html_content.split()),
                "variation_list": variation_list,
                "competitor_data": competitor_data,
                "output_ranges": ranges
            }
            json_bytes = json.dumps(debug_data, indent=2).encode("utf-8")
            b64 = base64.b64encode(json_bytes).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="debug_output.json" style="display:none">Download</a>'
            st.markdown(href, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.warning("Please provide all required inputs.")
