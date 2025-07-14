import streamlit as st
from serpapi import GoogleSearch
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# Page setup
st.set_page_config(page_title="Reddit Book Reviews", layout="wide")
st.title("📚 Reddit Book Review Finder")

# Get API key from Streamlit secrets
SERP_API_KEY = st.secrets["serpapi"]["api_key"]

# Input book name
book_name = st.text_input("Enter Book Title", "")

# Function to get Reddit URLs using SerpAPI
def get_reddit_urls(query):
    params = {
        "q": f"{query} review site:reddit.com",
        "hl": "en",
        "gl": "us",
        "api_key": SERP_API_KEY,
    }

    search = GoogleSearch(params)
    results = search.get_dict()
    urls = []

    for result in results.get("organic_results", []):
        link = result.get("link")
        if link and "reddit.com/r/" in link and "/comments/" in link:
            urls.append(link.split("?")[0])

    return list(set(urls))

# Function to extract Reddit comments using Reddit JSON
def extract_comments(url, max_comments=10):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        json_url = url + ".json"
        html = requests.get(json_url, headers=headers).json()
        comments_data = html[1]["data"]["children"]
        comments = []
        for comment in comments_data:
            body = comment["data"].get("body", "")
            if len(body) > 30:
                comments.append(body.strip())
            if len(comments) >= max_comments:
                break
        return comments
    except Exception as e:
        return [f"Failed to parse: {e}"]

# Main logic
if book_name:
    st.write(f"🔍 Searching for Reddit reviews on: **{book_name}**...")
    with st.spinner("Fetching reviews..."):
        reddit_urls = get_reddit_urls(book_name)
        time.sleep(1)

        reviews = []
        for url in reddit_urls:
            comments = extract_comments(url)
            for comment in comments:
                reviews.append({"Reddit URL": url, "Comment": comment})

        if reviews:
            df = pd.DataFrame(reviews)
            st.success(f"Found {len(reviews)} comments from {len(reddit_urls)} Reddit URLs.")
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("No reviews found.")
