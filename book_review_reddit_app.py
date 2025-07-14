import streamlit as st
from googlesearch import search
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time

st.set_page_config(page_title="Reddit Book Reviews", layout="wide")
st.title("📚 Reddit Book Review Finder")

book_name = st.text_input("Enter Book Title", "")

def get_reddit_urls(query):
    search_query = f"{query} review reddit"
    urls = []
    for url in search(search_query, num_results=15):
        if "reddit.com/r/" in url and "/comments/" in url:
            urls.append(url.split("?")[0])
    return list(set(urls))

def extract_comments(url, max_comments=10):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        html = requests.get(url + ".json", headers=headers).json()
        comments_data = html[1]["data"]["children"]
        comments = []
        for comment in comments_data:
            body = comment["data"].get("body", "")
            if len(body) > 30:  # filter short junk
                comments.append(body.strip())
            if len(comments) >= max_comments:
                break
        return comments
    except Exception as e:
        return [f"Failed to parse: {e}"]

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
            st.dataframe(df)
        else:
            st.warning("No reviews found.")
