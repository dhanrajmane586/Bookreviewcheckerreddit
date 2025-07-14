import streamlit as st
from serpapi import GoogleSearch
import requests
import pandas as pd
import time
from datetime import datetime

# Page configuration
st.set_page_config(page_title="Reddit Book Reviews", layout="wide")
st.title("📚 Reddit Book Review Finder")

# API key validation
try:
    SERP_API_KEY = st.secrets["serpapi"]["api_key"]
    if not SERP_API_KEY:
        st.error("❌ SerpAPI key not found in secrets. Please add your API key.")
        st.stop()
except Exception as e:
    st.error("❌ Error accessing SerpAPI key from secrets. Please check your configuration.")
    st.stop()

# User input
book_name = st.text_input("Enter Book Title", placeholder="e.g., The Great Gatsby")

def get_reddit_urls(query, max_results=10):
    """Search for Reddit URLs using SerpAPI"""
    try:
        params = {
            "q": f'"{query}" review site:reddit.com',
            "hl": "en",
            "gl": "us",
            "api_key": SERP_API_KEY,
            "num": max_results
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        if "error" in results:
            st.error(f"API Error: {results['error']}")
            return []
        
        urls = []
        for result in results.get("organic_results", []):
            link = result.get("link")
            title = result.get("title", "")
            
            # Filter for Reddit comment threads
            if link and "reddit.com/r/" in link and "/comments/" in link:
                # Remove query parameters and fragments
                clean_url = link.split("?")[0].split("#")[0]
                urls.append({
                    "url": clean_url,
                    "title": title
                })
        
        return urls
    
    except Exception as e:
        st.error(f"Error searching for Reddit URLs: {str(e)}")
        return []

def extract_comments(url, max_comments=10):
    """Extract comments from Reddit thread"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        json_url = url + ".json"
        response = requests.get(json_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Check if we have the expected structure
        if len(data) < 2 or "data" not in data[1] or "children" not in data[1]["data"]:
            return ["No comments found or invalid thread structure"]
        
        comments_data = data[1]["data"]["children"]
        comments = []
        
        for comment in comments_data:
            if "data" not in comment:
                continue
                
            body = comment["data"].get("body", "")
            author = comment["data"].get("author", "Unknown")
            score = comment["data"].get("score", 0)
            
            # Filter out deleted/removed comments and very short ones
            if body and body not in ["[deleted]", "[removed]"] and len(body) > 50:
                comments.append({
                    "author": author,
                    "body": body[:500] + "..." if len(body) > 500 else body,
                    "score": score
                })
                
            if len(comments) >= max_comments:
                break
        
        return comments
    
    except requests.exceptions.RequestException as e:
        return [f"Network error: {str(e)}"]
    except Exception as e:
        return [f"Error parsing comments: {str(e)}"]

def display_comments(comments, thread_title):
    """Display comments in a formatted way"""
    if not comments:
        st.write("No comments found for this thread.")
        return
    
    st.subheader(f"📝 {thread_title}")
    
    for i, comment in enumerate(comments, 1):
        if isinstance(comment, dict):
            with st.expander(f"Comment {i} by {comment['author']} (Score: {comment['score']})"):
                st.write(comment['body'])
        else:
            st.error(comment)
    
    st.divider()

# Main application logic
if book_name:
    st.write(f"🔍 Searching for Reddit reviews on: **{book_name}**...")
    
    with st.spinner("Fetching Reddit threads..."):
        reddit_urls = get_reddit_urls(book_name, max_results=5)
    
    if not reddit_urls:
        st.warning("No Reddit threads found for this book. Try a different search term.")
    else:
        st.success(f"Found {len(reddit_urls)} Reddit threads!")
        
        # Create tabs for different threads
        tab_names = [f"Thread {i+1}" for i in range(len(reddit_urls))]
        tabs = st.tabs(tab_names)
        
        for i, (tab, url_data) in enumerate(zip(tabs, reddit_urls)):
            with tab:
                st.write(f"**Source:** {url_data['url']}")
                
                with st.spinner(f"Loading comments from thread {i+1}..."):
                    comments = extract_comments(url_data['url'])
                    time.sleep(1)  # Rate limiting
                
                display_comments(comments, url_data['title'])

# Sidebar with information
with st.sidebar:
    st.header("ℹ️ About")
    st.write("""
    This app searches Reddit for book reviews and discussions.
    
    **How to use:**
    1. Enter a book title
    2. Click search or press Enter
    3. Browse through the Reddit threads and comments
    
    **Tips:**
    - Use the exact book title for best results
    - Try variations if no results are found
    - Popular books will have more discussions
    """)
    
    st.header("⚙️ Settings")
    st.write("Configure your SerpAPI key in Streamlit secrets:")
    st.code("""
    [serpapi]
    api_key = "your_api_key_here"
    """)

# Footer
st.markdown("---")
st.markdown("Built with ❤️ using Streamlit and SerpAPI")
