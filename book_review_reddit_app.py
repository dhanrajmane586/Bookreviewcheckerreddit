import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
import json

# Page configuration
st.set_page_config(page_title="Reddit Book Reviews", layout="wide")
st.title("📚 Reddit Book Review Finder")

# Debug mode toggle
debug_mode = st.sidebar.checkbox("Debug Mode", value=False)

# API key validation with better error handling
try:
    SERP_API_KEY = st.secrets["serpapi"]["api_key"]
    if not SERP_API_KEY or SERP_API_KEY == "your_api_key_here":
        st.error("❌ Please set your actual SerpAPI key in secrets.")
        st.code("""
        Go to your Streamlit Cloud dashboard:
        1. Click on your app
        2. Go to Settings > Secrets
        3. Add:
        [serpapi]
        api_key = "your_actual_serpapi_key"
        """)
        st.stop()
except KeyError:
    st.error("❌ SerpAPI key not found in secrets. Please add your API key.")
    st.stop()
except Exception as e:
    st.error(f"❌ Error accessing secrets: {str(e)}")
    st.stop()

# Try to import serpapi with error handling
try:
    from serpapi import GoogleSearch
    if debug_mode:
        st.success("✅ SerpAPI imported successfully")
except ImportError as e:
    st.error(f"❌ Failed to import serpapi: {str(e)}")
    st.error("Make sure your requirements.txt contains: google-search-results")
    st.stop()

# API key test function
def test_api_key():
    """Test if the API key is working"""
    try:
        test_search = GoogleSearch({
            "q": "test search",
            "api_key": SERP_API_KEY,
            "num": 1
        })
        results = test_search.get_dict()
        
        if "error" in results:
            return False, f"API Error: {results['error']}"
        elif "organic_results" in results:
            return True, "API key is working correctly!"
        else:
            return False, "Unexpected API response format"
    except Exception as e:
        return False, f"API test failed: {str(e)}"

# User input
book_name = st.text_input("Enter Book Title", placeholder="e.g., The Great Gatsby")

# API test button (always visible)
if st.button("🔧 Test API Key"):
    with st.spinner("Testing API..."):
        is_working, message = test_api_key()
        if is_working:
            st.success(message)
        else:
            st.error(message)

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
        
        if debug_mode:
            st.write("🔍 Search parameters:", params)
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        if debug_mode:
            st.write("📊 Raw API Response:", results)
        
        if "error" in results:
            st.error(f"API Error: {results['error']}")
            return []
        
        urls = []
        organic_results = results.get("organic_results", [])
        
        if debug_mode:
            st.write(f"📈 Found {len(organic_results)} organic results")
        
        for result in organic_results:
            link = result.get("link")
            title = result.get("title", "")
            
            if debug_mode:
                st.write(f"🔗 Checking link: {link}")
            
            # Filter for Reddit comment threads
            if link and "reddit.com/r/" in link and "/comments/" in link:
                clean_url = link.split("?")[0].split("#")[0]
                urls.append({
                    "url": clean_url,
                    "title": title
                })
                if debug_mode:
                    st.write(f"✅ Added Reddit URL: {clean_url}")
        
        return urls
    
    except Exception as e:
        st.error(f"Error searching for Reddit URLs: {str(e)}")
        if debug_mode:
            st.exception(e)
        return []

def extract_comments(url, max_comments=10):
    """Extract comments from Reddit thread"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        json_url = url + ".json"
        if debug_mode:
            st.write(f"📥 Fetching: {json_url}")
        
        response = requests.get(json_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        if debug_mode:
            st.write(f"📊 Response status: {response.status_code}")
            st.write(f"📊 Data structure: {type(data)}, length: {len(data) if isinstance(data, list) else 'N/A'}")
        
        # Check if we have the expected structure
        if not isinstance(data, list) or len(data) < 2:
            return ["Invalid response format - not a list or too short"]
        
        if "data" not in data[1] or "children" not in data[1]["data"]:
            return ["Invalid thread structure - missing data or children"]
        
        comments_data = data[1]["data"]["children"]
        comments = []
        
        if debug_mode:
            st.write(f"📈 Found {len(comments_data)} raw comments")
        
        for comment in comments_data:
            if "data" not in comment:
                continue
                
            comment_data = comment["data"]
            body = comment_data.get("body", "")
            author = comment_data.get("author", "Unknown")
            score = comment_data.get("score", 0)
            
            # Filter out deleted/removed comments and very short ones
            if body and body not in ["[deleted]", "[removed]"] and len(body) > 30:
                comments.append({
                    "author": author,
                    "body": body[:800] + "..." if len(body) > 800 else body,
                    "score": score
                })
                
            if len(comments) >= max_comments:
                break
        
        if debug_mode:
            st.write(f"✅ Extracted {len(comments)} valid comments")
        
        return comments
    
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error accessing {url}: {str(e)}"
        if debug_mode:
            st.exception(e)
        return [error_msg]
    except json.JSONDecodeError as e:
        error_msg = f"JSON parsing error: {str(e)}"
        if debug_mode:
            st.exception(e)
        return [error_msg]
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        if debug_mode:
            st.exception(e)
        return [error_msg]

def display_comments(comments, thread_title, url):
    """Display comments in a formatted way"""
    st.subheader(f"📝 {thread_title}")
    st.write(f"**Source:** [Reddit Thread]({url})")
    
    if not comments:
        st.write("No comments found for this thread.")
        return
    
    # Check if comments are error messages
    if len(comments) == 1 and isinstance(comments[0], str) and "error" in comments[0].lower():
        st.error(comments[0])
        return
    
    valid_comments = [c for c in comments if isinstance(c, dict)]
    
    if not valid_comments:
        st.warning("No valid comments found in this thread.")
        return
    
    for i, comment in enumerate(valid_comments, 1):
        with st.expander(f"💬 Comment {i} by u/{comment['author']} (Score: {comment['score']})"):
            st.write(comment['body'])
    
    st.divider()

# Main application logic
if book_name:
    st.write(f"🔍 Searching for Reddit reviews on: **{book_name}**...")
    
    with st.spinner("Fetching Reddit threads..."):
        reddit_urls = get_reddit_urls(book_name, max_results=5)
    
    if not reddit_urls:
        st.warning("⚠️ No Reddit threads found for this book.")
        st.info("💡 Try these tips:")
        st.write("• Use the exact book title")
        st.write("• Try removing subtitles")
        st.write("• Check if the book is popular enough to have Reddit discussions")
        st.write("• Test your API key using the button above")
    else:
        st.success(f"🎉 Found {len(reddit_urls)} Reddit threads!")
        
        # Display all threads in sequence instead of tabs (better for debugging)
        for i, url_data in enumerate(reddit_urls, 1):
            st.markdown(f"## Thread {i}")
            
            with st.spinner(f"Loading comments from thread {i}..."):
                comments = extract_comments(url_data['url'])
                time.sleep(1)  # Rate limiting
            
            display_comments(comments, url_data['title'], url_data['url'])

# Sidebar with information
with st.sidebar:
    st.header("ℹ️ About")
    st.write("""
    This app searches Reddit for book reviews and discussions.
    
    **How to use:**
    1. Test your API key first
    2. Enter a book title
    3. Browse through the results
    
    **Troubleshooting:**
    - Enable Debug Mode for detailed logs
    - Test your API key regularly
    - Check your SerpAPI credits
    """)
    
    st.header("⚙️ API Info")
    if st.button("Check API Credits"):
        # This would require additional API call to check account info
        st.info("Check your SerpAPI dashboard for credit information")
    
    st.header("🔧 Debug")
    if debug_mode:
        st.info("Debug mode is ON - you'll see detailed logs")
    else:
        st.info("Debug mode is OFF - enable for troubleshooting")

# Footer
st.markdown("---")
st.markdown("Built with ❤️ using Streamlit and SerpAPI")
st.markdown("💡 **Tip:** Enable debug mode in the sidebar if you encounter issues")
