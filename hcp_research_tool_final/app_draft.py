import streamlit as st
import pandas as pd
import http.client
import json
import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os
import openai  # Add OpenAI import
import time

# Set page configuration
st.set_page_config(
    page_title="HCP Research tool",
    page_icon="📊",
    layout="wide"
)

# Title and description
st.title("HCP Research Tool")
st.markdown("Filter and analyze content from HCPs from different social media platforms")

# Healthcare industry codes
HEALTHCARE_INDUSTRIES = {
    "Hospitals and Health Care": 14,
    "Community Services": 2115,
    "Services for the Elderly and Disabled": 2112,
    "Hospitals": 2081,
    "Individual and Family Services": 88,
    "Child Day Care Services": 2128,
    "Emergency and Relief Services": 2122,
    "Vocational Rehabilitation Services": 2125,
    "Medical Practices": 13,
    "Alternative Medicine": 125,
    "Ambulance Services": 2077,
    "Chiropractors": 2048,
    "Dentists": 2045,
    "Family Planning Centers": 2060,
    "Home Health Care Services": 2074,
    "Medical and Diagnostic Laboratories": 2069,
    "Mental Health Care": 139,
    "Optometrists": 2050,
    "Outpatient Care Centers": 2063,
    "Physical, Occupational and Speech Therapists": 2054,
    "Physicians": 2040
}

# Create sidebar for filters
st.sidebar.header("Filters")

# Platform selection dropdown
platform = st.sidebar.selectbox(
    "Select Platform",
    options=["All", "LinkedIn", "Reddit", "Twitter", "Big Data"],
    index=0
)

# LinkedIn specific filters (only show when LinkedIn is selected)
linkedin_keyword = ""
if platform == "LinkedIn":
    st.sidebar.subheader("LinkedIn Filters")
    linkedin_keyword = st.sidebar.text_input("Search Keyword", "")
    linkedin_sort = "relevance"
    # Add dropdown for datePosted with user-friendly labels
    date_options = {
        "past-month": "Past Month",
        "past-week": "Past Week",
        "past-24h": "Past 24 Hours",
    }
    date_posted = st.sidebar.selectbox(
        "Date Posted",
        options=list(date_options.keys()),
        format_func=lambda x: date_options[x],
        index=0,
        help="Filter posts by when they were posted"
    )



# Add function to load data from the specified Big Data Google Sheet
def load_big_data_from_sheet():
    try:
        with st.spinner("Loading big data from Google Sheet..."):
            # Get sheet URL from secrets
            sheet_url = st.secrets["gsheets"]["sheet_url"]
            sheet_url = sheet_url.replace('/edit?gid=0', '/export?format=csv')
            df = pd.read_csv(sheet_url)
            
            # Create Platform column and rename columns for consistency
            df["Platform"] = "External Source"
            df = df.rename(columns={
                "content": "Post",
                "title": "Author",
                "score": "Engagement",
                "url": "URL"
            })
            
            # Handle date conversion
            if "created_at" in df.columns:
                df["Date"] = pd.to_datetime(df["created_at"], errors='coerce')
            else:
                df["Date"] = datetime.now()
            
            # Ensure URL column exists
            if "URL" not in df.columns:
                df["URL"] = ""
                
            # Select only needed columns
            columns = ["Platform", "Post", "Date", "Engagement", "Author", "URL", "raw_content"]
            df = df[columns]
            
            # Process and combine with mock data
            if not df.empty:
                # Clean and deduplicate
                df = df.sort_values(by="Engagement", ascending=False)
                df = df.drop_duplicates(subset=["Post"], keep="first")
                
                # Augment with mock data
                mock_df = load_mock_data_from_sheet()
                if not mock_df.empty:
                    # Combine and deduplicate again
                    df = pd.concat([df, mock_df])
                    df = df.sort_values(by="Engagement", ascending=False)
                    df = df.drop_duplicates(subset=["Post"], keep="first")
                
                return df
    except Exception as e:
        st.error(f"Error loading data from Big Data Google Sheet: {str(e)}")
    
    # Return empty DataFrame if failed
    return pd.DataFrame()

# Function for OpenAI analysis
def analyze_with_openai(df, prompt):
    try:
        # Get API key from secrets
        api_key = st.secrets["openai"]["api_key"]
        
        # Create a more efficient sampling strategy
        # Get high engagement posts with more weight
        high_engagement = df.nlargest(5, 'Engagement')[['Post', 'Engagement', 'Author', 'Platform']]
        
        # Get diverse samples from different platforms
        platform_samples = []
        for platform in df['Platform'].unique():
            platform_df = df[df['Platform'] == platform]
            if not platform_df.empty:
                platform_samples.append(platform_df.sample(min(3, len(platform_df))))
        
        if platform_samples:
            diverse_sample = pd.concat(platform_samples)[['Post', 'Engagement', 'Author', 'Platform']]
        else:
            # Fallback to random sampling if no platform-specific samples
            diverse_sample = df.sample(min(10, len(df)))[['Post', 'Engagement', 'Author', 'Platform']]
        
        # Get comprehensive statistics
        stats = {
            'total_records': len(df),
            'avg_engagement': df['Engagement'].mean(),
            'max_engagement': df['Engagement'].max(),
            'min_engagement': df['Engagement'].min(),
            'engagement_std': df['Engagement'].std(),
            'unique_authors': df['Author'].nunique(),
            'platforms': df['Platform'].value_counts().to_dict(),
            'date_range': f"{df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}",
        }
        
        # Construct an improved prompt
        full_prompt = f"""
        # Healthcare Data Analysis Request
        
        ## Dataset Overview
        - Total Records: {stats['total_records']}
        - Date Range: {stats['date_range']}
        - Platforms: {', '.join([f"{p} ({c})" for p, c in stats['platforms'].items()])}
        
        ## Engagement Metrics
        - Average: {stats['avg_engagement']:.2f}
        - Maximum: {stats['max_engagement']}
        - Minimum: {stats['min_engagement']}
        - Standard Deviation: {stats['engagement_std']:.2f}
        - Unique Authors: {stats['unique_authors']}
        
        ## HIGH ENGAGEMENT SAMPLE:
        {high_engagement.to_string()}
        
        ## DIVERSE PLATFORM SAMPLE:
        {diverse_sample.to_string()}

        ## USER ANALYSIS REQUEST:
        {prompt}

        Provide a clear, structured analysis focusing specifically on the healthcare implications.
        Use bullet points for key findings and organize insights by theme.
        """
        
        # Use the OpenAI client to make the API call
        client = openai.OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a healthcare data analyst specializing in analyzing social media and web content related to healthcare professionals. Your analysis should be evidence-based, focusing on practical insights for pharmaceutical and healthcare organizations."
                },
                {
                    "role": "user", 
                    "content": full_prompt
                }
            ],
            temperature=0.3  # Lower temperature for more focused analysis
        )
        
        # Return the analysis
        return response.choices[0].message.content
    
    except Exception as e:
        return f"Error during OpenAI analysis: {str(e)}"

# Add to Google Sheet using webhook
def add_to_google_sheet(df, search_query=""):
    try:
        # Get the webhook URL and credentials from secrets
        webhook_url = st.secrets["webhook"]["url"]
        username = st.secrets["webhook"]["username"]
        password = st.secrets["webhook"]["password"]
        
        # Convert DataFrame to list of dictionaries for the API
        rows = []
        for _, row in df.iterrows():
            rows.append({
                'Platform': row.get('Platform', ''),
                'Post': row.get('Post', ''),
                'Date': row.get('Date', '').strftime('%Y-%m-%d %H:%M:%S') if isinstance(row.get('Date'), datetime) else str(row.get('Date', '')),
                'Engagement': row.get('Engagement', 0),
                'Author': row.get('Author', ''),
                'URL': row.get('URL', ''),
                'Search': search_query  # Add the search query
            })
        
        # Prepare the request data
        data = {
            "rows": rows
        }
        
        # Make the API request with basic auth
        response = requests.post(
            webhook_url, 
            json=data,
            auth=(username, password)
        )
        
        # Check the response
        if response.status_code == 200:
            return True
        else:
            st.sidebar.error(f"Error saving data: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        st.sidebar.error(f"Error saving data: {str(e)}")
        return False

# Parse LinkedIn data from API response
def parse_linkedin_data(response):
    if 'success' in response and response['success'] and 'data' in response and 'items' in response['data'] and 'count' in response['data'] and response['data']['count'] > 0:
        posts = []
        for post in response['data']['items']:
            # Convert timestamp to datetime (ms to datetime)
            if 'postedDateTimestamp' in post:
                created_time = datetime.fromtimestamp(post.get('postedDateTimestamp', 0)/1000)
            else:
                created_time = datetime.now()
            
            # Calculate engagement as sum of all social activities
            engagement = 0
            if 'socialActivityCountsInsight' in post:
                social_stats = post['socialActivityCountsInsight']
                engagement = (
                    social_stats.get('numComments', 0) +
                    social_stats.get('likeCount', 0) +
                    social_stats.get('appreciationCount', 0) +
                    social_stats.get('empathyCount', 0) +
                    social_stats.get('InterestCount', 0) +
                    social_stats.get('praiseCount', 0) +
                    social_stats.get('funnyCount', 0) +
                    social_stats.get('maybeCount', 0)
                )
            
            posts.append({
                "Platform": "LinkedIn",
                "Post": post.get('text', 'No content'),
                "Date": created_time,
                "Engagement": engagement,
                "Author": post.get('author', {}).get('fullName', 'Unknown'),
                "URL": post.get('url', '')
            })
        return pd.DataFrame(posts)
    elif 'count' in response['data'] and response['data']['count'] <= 0:
        st.error("No LinkedIn data found. Please try a different search term.")
        return pd.DataFrame()
    else:
        st.error("Failed to retrieve LinkedIn data. API response format unexpected.")
        return pd.DataFrame()

# Function to fetch LinkedIn data
def get_linkedin_data(keyword="nhs pathway", sort_by="relevance", date_posted=""):
    conn = http.client.HTTPSConnection("linkedin-api8.p.rapidapi.com")
    
    # Include all healthcare industry codes in the request
    industry_codes = list(HEALTHCARE_INDUSTRIES.values())
    
    payload = {
        "keyword": keyword,
        "sortBy": sort_by,
        "datePosted": date_posted,
        "page": 1,
        "contentType": "",
        "authorIndustry": industry_codes  
    }
    
    api_key = st.secrets["rapidapi"]["key"]
    
    headers = {
        'x-rapidapi-key': api_key,
        'x-rapidapi-host': "linkedin-api8.p.rapidapi.com",
        'Content-Type': "application/json"
    }
    
    try:
        conn.request("POST", "/search-posts", json.dumps(payload), headers)
        res = conn.getresponse()
        data = res.read()
        response = json.loads(data.decode("utf-8"))
        print(response)
        # Process the LinkedIn API response into a DataFrame
        return parse_linkedin_data(response)
    except Exception as e:
        st.error(f"Error fetching LinkedIn data: {str(e)}")
        return pd.DataFrame()

# Parse Twitter data from API response
def parse_twitter_data(response, min_engagement=10):
    if 'results' in response:
        posts = []
        for tweet in response['results']:
            # Calculate engagement as sum of interactions
            engagement = (
                tweet.get('favorite_count', 0) + 
                tweet.get('retweet_count', 0) + 
                tweet.get('reply_count', 0) + 
                tweet.get('quote_count', 0)
            )
            
            # Skip tweets with engagement less than minimum
            if engagement < min_engagement:
                continue
            
            # Get media URL if available
            media_url = ""
            if 'media_url' in tweet and len(tweet['media_url']) > 0:
                media_url = tweet['media_url'][0]
            
            created_time = datetime.strptime(tweet.get('creation_date', ''), "%a %b %d %H:%M:%S %z %Y") if 'creation_date' in tweet else datetime.now()
            
            posts.append({
                "Platform": "Twitter",
                "Post": tweet.get('text', 'No content'),
                "Date": created_time,
                "Engagement": engagement,
                "Author": tweet.get('user', {}).get('username', 'Unknown'),
                "URL": f"https://twitter.com/{tweet.get('user', {}).get('username', 'unknown')}/status/{tweet.get('tweet_id')}"
            })
        return pd.DataFrame(posts)
    else:
        st.error("Failed to retrieve Twitter data. API response format unexpected.")
        return pd.DataFrame()

# Function to fetch Twitter data
def get_twitter_data(keyword="nhs pathway", section="top", min_engagement=10, start_date=None):
    conn = http.client.HTTPSConnection("twitter154.p.rapidapi.com")
    
    # Replace spaces with %20 for URL encoding
    encoded_keyword = keyword.replace(" ", "%20")
    
    # Get API key directly from secrets
    api_key = st.secrets["rapidapi"]["key"]
    
    headers = {
        'x-rapidapi-key': api_key,
        'x-rapidapi-host': "twitter154.p.rapidapi.com"
    }
    
    # Format start_date if provided (YYYY-MM-DD)
    date_param = ""
    section_param = f"&section={section}"
    if start_date:
        formatted_date = start_date.strftime('%Y-%m-%d')
        date_param = f"&start_date={formatted_date}"
    
    # Construct the endpoint to search tweets - use minimal filtering in API call
    endpoint = f"/search/search?query={encoded_keyword}{section_param}&min_retweets=0&min_likes=1&limit=50&language=en{date_param}"
    
    try:
        conn.request("GET", endpoint, headers=headers)
        res = conn.getresponse()
        data = res.read()
        response = json.loads(data.decode("utf-8"))
        
        # Process the Twitter API response into a DataFrame
        return parse_twitter_data(response, min_engagement)
    except Exception as e:
        st.error(f"Error fetching Twitter data: {str(e)}")
        return pd.DataFrame()

# Parse Reddit data from API response
def parse_reddit_data(response, min_engagement=10):
    if 'data' in response:
        posts = []
        for post in response['data']:
            # Calculate engagement as sum of interactions (score and comments)
            engagement = post.get('score', 0) + post.get('comments', 0)
            
            # Skip posts with engagement less than minimum
            if engagement < min_engagement:
                continue
            
            # Extract post title
            title = post.get('title', '')
            
            # Get post content based on type
            content = title
            content_type = "text"
            media_url = ""
            
            if post.get('content'):
                # Check for text content
                if post['content'].get('text'):
                    content = f"{title}\n\n{post['content']['text']}"
                # Check for image content
                elif post['content'].get('image') and post['content']['image'].get('url'):
                    media_url = post['content']['image']['url']
                    content_type = "image"
                # Check for video content
                elif post['content'].get('video') and post['content']['video'].get('url'):
                    media_url = post['content']['video']['url']
                    content_type = "video"
            
            # Convert timestamp to datetime
            created_date = post.get('creationDate', '')
            if created_date:
                created_time = datetime.strptime(created_date, "%Y-%m-%dT%H:%M:%S.%f%z")
            else:
                created_time = datetime.now()
            
            # Get author name
            author = post.get('author', {}).get('name', 'Unknown')
            
            # Get post URL
            post_url = post.get('url', '')
            
            posts.append({
                "Platform": "Reddit",
                "Post": content,
                "Date": created_time,
                "Engagement": engagement,
                "Author": author,
                "URL": post_url,
                "Subreddit": post.get('subreddit', {}).get('name', 'Unknown'),
                "ContentType": content_type,
                "MediaURL": media_url
            })
            
        return pd.DataFrame(posts)
    else:
        st.error("Failed to retrieve Reddit data")
        return pd.DataFrame()

# Function to fetch Reddit data
def get_reddit_data(keyword="healthcare", sort="RELEVANCE", min_engagement=10, time="ALL", subreddit="", subreddit_keyword=""):
    conn = http.client.HTTPSConnection("reddit-scraper2.p.rapidapi.com")
    
    # Get API key directly from secrets
    api_key = st.secrets["rapidapi"]["key"]
    
    headers = {
        'x-rapidapi-key': api_key,
        'x-rapidapi-host': "reddit-scraper2.p.rapidapi.com"
    }
    
    # Determine which endpoint to use based on whether we're searching by keyword or subreddit
    if subreddit:
        # Clean the subreddit name - remove 'r/', '@', 'https://' etc.
        clean_subreddit = subreddit.strip()
        if 'reddit.com/r/' in clean_subreddit:
            # Extract the subreddit name from a full URL
            parts = clean_subreddit.split('reddit.com/r/')
            if len(parts) > 1:
                clean_subreddit = parts[1].split('/')[0]
        elif clean_subreddit.startswith('r/'):
            clean_subreddit = clean_subreddit[2:]
        elif clean_subreddit.startswith('@'):
            clean_subreddit = clean_subreddit[1:]
        
        # Use the exact working URL format from the example
        # Ensure uppercase ALL for time parameter
        actual_time = time.upper() if time.lower() == "all" else time
        
        # If subreddit_keyword is provided, add it to the search
        if subreddit_keyword:
            encoded_keyword = subreddit_keyword.replace(" ", "%20")
            endpoint = f"/sub_posts_v3?sub=https%3A%2F%2Fwww.reddit.com%2Fr%2F{clean_subreddit}%2F&sort={sort}&time={actual_time}&query={encoded_keyword}"
        else:
            endpoint = f"/sub_posts_v3?sub=https%3A%2F%2Fwww.reddit.com%2Fr%2F{clean_subreddit}%2F&sort={sort}&time={actual_time}"
    else:
        # Replace spaces with %20 for URL encoding
        encoded_keyword = keyword.replace(" ", "%20")
        # Construct the endpoint to search Reddit posts by keyword
        actual_time = time.upper() if time.lower() == "all" else time
        endpoint = f"/search_posts_v3?query={encoded_keyword}&sort={sort}&time={actual_time}&nsfw=0"
        print(endpoint)
    
    try:
        conn.request("GET", endpoint, headers=headers)
        res = conn.getresponse()
        
        if res.status != 200:
            st.error(f"API returned status code {res.status}")
            return pd.DataFrame()
            
        data = res.read()
        response_text = data.decode("utf-8")
        
        try:
            response = json.loads(response_text)
        except json.JSONDecodeError:
            st.error(f"Failed to parse API response as JSON")
            return pd.DataFrame()
        
        # Process the Reddit API response into a DataFrame
        return parse_reddit_data(response, min_engagement)
    except Exception as e:
        st.error(f"Error fetching Reddit data: {str(e)}")
        return pd.DataFrame()

# Mock data from Google Sheet
def load_mock_data_from_sheet():
    try:
        with st.spinner("Loading test data from Google Sheet..."):
            # Get mock sheet URL from secrets
            sheet_url = st.secrets["gsheets"]["mock_sheet_url"]
            sheet_url = sheet_url.replace('/edit?usp=sharing', '/export?format=csv')
            df = pd.read_csv(sheet_url)
            
            # Convert Date column to datetime
            df["Date"] = pd.to_datetime(df["Date"])
            
            if not df.empty:
                # Sort by engagement in descending order to show highest engagement first
                df = df.sort_values(by="Engagement", ascending=False).drop_duplicates(subset=["Post"], keep="first")
                return df
    except Exception as e:
        st.error(f"Error loading data from Google Sheet: {str(e)}")
    
    # Return empty DataFrame if failed
    return pd.DataFrame()

# Twitter specific filters (only show when Twitter is selected)
twitter_keyword = ""
if platform == "Twitter":
    st.sidebar.subheader("Twitter Filters")
    twitter_keyword = st.sidebar.text_input("Search Keyword", "")
    
    # Add date filter
    twitter_start_date = st.sidebar.date_input(
        "Start Date",
        value=datetime.now(),
        max_value=datetime.now(),
        help="Filter tweets posted on or after this date"
    )
    
    # Always use "top" as default section
    twitter_section = "top"
    
    # Replace min engagement with min_engagement
    twitter_min_engagement = st.sidebar.slider("Minimum Engagement", 0, 5000, 10, help="Filter tweets by minimum engagement (sum of likes, retweets, replies, quotes)")

# Reddit specific filters (only show when Reddit is selected)
reddit_keyword = ""
if platform == "Reddit":
    st.sidebar.subheader("Reddit Filters")
    
    # Two search options - keyword or subreddit
    reddit_search_type = st.sidebar.radio(
        "Search Type",
        options=["Keyword", "Subreddit"],
        index=0,  # Set Keyword as the default option
        help="Search by keyword across all subreddits or browse a specific subreddit"
    )
    
    if reddit_search_type == "Keyword":
        reddit_keyword = st.sidebar.text_input("Search Keyword", "")
        reddit_subreddit = ""
        reddit_subreddit_keyword = ""  # Set default empty value
        
        # Sort options for keyword search (exclude CONTROVERSIAL and RISING)
        reddit_sort = st.sidebar.selectbox(
            "Sort By", 
            options=["TOP", "NEW", "HOT"], 
            index=0,  # Default to TOP
            help="How to sort the Reddit posts"
        )
        
        # Minimum engagement filter - only show for keyword search
        reddit_min_engagement = st.sidebar.slider("Minimum Engagement", 0, 10000, 10, help="Filter posts by minimum engagement (sum of upvotes and comments)")
    else:
        reddit_subreddit = st.sidebar.text_input(
            "Subreddit Name", 
            "nhs",  # Default to nhs subreddit
            help="Enter just the subreddit name without any prefixes"
        )
        
        # Add a textbox to search within the subreddit
        reddit_subreddit_keyword = st.sidebar.text_input(
            "Search within Subreddit", 
            "",
            help="Enter keywords to search within the selected subreddit"
        )
        
        reddit_keyword = ""
        
        # Sort options for subreddit search (include all options)
        reddit_sort = st.sidebar.selectbox(
            "Sort By", 
            options=["CONTROVERSIAL", "TOP", "NEW", "HOT", "RISING"], 
            index=1,  # Default to TOP
            help="How to sort the Reddit posts"
        )
        
        # For subreddit search, set min_engagement to 0 (no filtering)
        reddit_min_engagement = 0
    
    # Add time filter only when TOP or CONTROVERSIAL are selected
    if reddit_sort in ["TOP", "CONTROVERSIAL"]:
        reddit_time = st.sidebar.selectbox(
            "Time Period", 
            options=["ALL", "YEAR", "MONTH", "WEEK", "DAY", "HOUR"],
            index=0,  # Default to ALL
            help="Filter posts by time period (only used with TOP or CONTROVERSIAL sort)"
        )
    else:
        # Set a default value for reddit_time when not shown
        reddit_time = "ALL"

# Function to fetch data based on platform
def fetch_platform_data(platform, params):
    with st.spinner(f"Fetching {platform} data..."):
        try:
            if platform == "LinkedIn":
                data_df = get_linkedin_data(
                    params['keyword'], 
                    params['sort'], 
                    params['date_posted']
                )
            elif platform == "Twitter":
                data_df = get_twitter_data(
                    params['keyword'], 
                    params['section'], 
                    params['min_engagement'], 
                    params['start_date']
                )
            elif platform == "Reddit":
                data_df = get_reddit_data(
                    keyword=params['keyword'],
                    sort=params['sort'],
                    min_engagement=params['min_engagement'],
                    time=params['time'],
                    subreddit=params['subreddit'],
                    subreddit_keyword=params['subreddit_keyword']
                )
            
            if not data_df.empty:
                # Sort by engagement in descending order
                data_df = data_df.sort_values(by="Engagement", ascending=False)
                st.success(f"Successfully retrieved {len(data_df)} {platform} posts")
                
                # Save results to Google Sheet
                add_to_google_sheet(data_df, params['search_term'])
                return data_df
            else:
                st.warning(f"Could not retrieve {platform} data. Using mockup data instead.")
                mock_df = load_mock_data_from_sheet()
                # Filter to only platform posts if needed
                if platform != "All":
                    mock_df = mock_df[mock_df["Platform"] == platform]
                # Sort by engagement in descending order
                mock_df = mock_df.sort_values(by="Engagement", ascending=False)
                return mock_df
        except Exception as e:
            st.error(f"Error: {str(e)}")
            mock_df = load_mock_data_from_sheet()
            # Filter to only platform posts if needed
            if platform != "All":
                mock_df = mock_df[mock_df["Platform"] == platform]
            # Sort by engagement in descending order
            mock_df = mock_df.sort_values(by="Engagement", ascending=False)
            st.warning("Using mockup data due to API error.")
            return mock_df

# Load data based on selected platform
if platform == "LinkedIn" and linkedin_keyword and linkedin_keyword.lower() != "":
    params = {
        'keyword': linkedin_keyword,
        'sort': linkedin_sort,
        'date_posted': date_posted,
        'search_term': linkedin_keyword
    }
    df = fetch_platform_data("LinkedIn", params)
elif platform == "Twitter" and twitter_keyword and twitter_keyword.lower() != "":
    params = {
        'keyword': twitter_keyword,
        'section': twitter_section,
        'min_engagement': twitter_min_engagement,
        'start_date': twitter_start_date,
        'search_term': twitter_keyword
    }
    df = fetch_platform_data("Twitter", params)
elif platform == "Reddit" and ((reddit_search_type == "Keyword" and reddit_keyword and reddit_keyword.lower() != "") or 
                            (reddit_search_type == "Subreddit" and reddit_subreddit and reddit_subreddit.lower() != "")):
    # Create search term that includes both subreddit and keyword if applicable
    if reddit_search_type == "Keyword":
        search_term = reddit_keyword
    else:
        search_term = f"r/{reddit_subreddit}"
        if reddit_subreddit_keyword:
            search_term += f" - {reddit_subreddit_keyword}"
    
    params = {
        'keyword': reddit_keyword,
        'sort': reddit_sort,
        'min_engagement': reddit_min_engagement,
        'time': reddit_time.lower(),
        'subreddit': reddit_subreddit,
        'subreddit_keyword': reddit_subreddit_keyword,
        'search_term': search_term
    }
    df = fetch_platform_data("Reddit", params)
elif platform == "Big Data":
    # Load data from the Big Data Google Sheet
    df = load_big_data_from_sheet()
   
    # Add summary statistics
    st.header("Dataset Summary")
    
    # Display simplified statistics (removed average engagement)
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Records", len(df))
    with col2:
        st.metric("Unique URLs", df["URL"].nunique())
    
    # Add AI analysis section
    st.header("AI Analysis")
    analysis_prompt = st.text_area(
        "Enter your analysis request:",
        f"""Analyze the provided dataset to identify discussions that resemble a doctor talking about current clinical pathways. Extract key themes, challenges, and insights relevant to NHS treatment protocols, prescribing practices, and patient management."
            Key Objectives:
            1. Identify Clinical Pathway Mentions – Look for discussions about NHS treatment protocols, patient flow, and prescribing guidelines.
            2. Extract Pain Points & Challenges – Highlight frustrations, bottlenecks, and barriers in implementing guidelines.
            3. Track Pharma-Relevant Insights – Identify mentions of specific medications, drug access issues, or unmet needs in treatment.
            4. Suggest Implementation Strategies – Provide recommendations on how these insights can be used for pharma marketing, engagement, or strategy development.
        """,
        height=200
    )
    
    if st.button("Generate AI Analysis"):
        with st.spinner("Analyzing data with AI..."):
            analysis_result = analyze_with_openai(df, analysis_prompt)
            st.markdown("### AI Analysis Results")
            st.markdown(analysis_result)
else:
    # Load from Google Sheet by default
    df_all = load_mock_data_from_sheet()
    
    # Filter by platform if needed
    if platform != "All":
        df = df_all[df_all["Platform"] == platform]
        st.success(f"Successfully loaded {len(df)} {platform} posts from default dataset")
    else:
        df = df_all
        st.success(f"Successfully loaded {len(df)} posts from default dataset")
    
    # Sort by engagement in descending order
    df = df.sort_values(by="Engagement", ascending=False)

# Display posts
def display_posts(df):
    st.header("Posts")
    
    if not df.empty:
        # Create a single expander for all posts
        with st.expander("View All Posts", expanded=True):
            # Set fixed posts per page to 20
            posts_per_page = 20
            
            # Calculate total pages
            total_posts = len(df)
            total_pages = (total_posts + posts_per_page - 1) // posts_per_page
            
            # Get current page from session state
            current_page = st.session_state.get('current_page', 1)
            
            # Calculate start and end indices for current page
            start_idx = (current_page - 1) * posts_per_page
            end_idx = min(start_idx + posts_per_page, total_posts)
            
            # Display posts for current page
            for i, row in df.iloc[start_idx:end_idx].iterrows():
                with st.container():
                    col1, col2 = st.columns([1, 4])
                    
                    with col1:
                        # Display platform icon or logo
                        if row["Platform"] == "LinkedIn":
                            st.image("https://content.linkedin.com/content/dam/me/business/en-us/amp/brand-site/v2/bg/LI-Bug.svg.original.svg", width=50)
                        elif row["Platform"] == "Twitter":
                            st.image("https://about.twitter.com/content/dam/about-twitter/x/brand-toolkit/logo-black.png.twimg.1920.png", width=50)
                        elif row["Platform"] == "Reddit":
                            st.image("https://www.redditstatic.com/desktop2x/img/favicon/android-icon-192x192.png", width=50)
                        elif row["Platform"] == "External Source":
                            st.image("https://cdn-icons-png.flaticon.com/512/2906/2906274.png", width=50)
                        
                        # Display engagement metrics
                        st.metric("Engagement", row["Engagement"])
                    
                    with col2:
                        # Author and date
                        if row["Platform"] == "Reddit" and "Subreddit" in row:
                            st.markdown(f"**{row['Author']}** in r/{row['Subreddit']} • {row['Date'].strftime('%Y-%m-%d')}")
                        else:
                            st.markdown(f"**{row['Author']}** • {row['Date'].strftime('%Y-%m-%d')}")
                        
                        # Post content with character limit and expandable view
                        post_content = row["Post"]
                        char_limit = 300
                        
                        # If post is longer than character limit, show truncated version with "View more" option
                        if len(str(post_content)) > char_limit:
                            # Display truncated content
                            st.write(f"{str(post_content)[:char_limit]}...")
                            
                            # Use HTML details tag for expandable content
                            details_html = f"""
                            <details>
                                <summary style="cursor: pointer; color: #1E88E5; margin-bottom: 20px;">View full post</summary>
                                <div style="padding: 10px; border-left: 2px solid #1E88E5; margin-top: 8px;">
                                    {str(post_content).replace('"', '&quot;').replace('\n', '<br>')}
                                </div>
                            </details>
                            """
                            st.markdown(details_html, unsafe_allow_html=True)
                        else:
                            # Display short posts directly
                            st.write(post_content)
                        
                        # Display raw_content if available for Big Data
                        if row["Platform"] == "External Source" and "raw_content" in row and row["raw_content"]:
                            st.markdown("**Raw Content:**")
                            raw_content = str(row["raw_content"])
                            if len(raw_content) > char_limit:
                                st.write(f"{raw_content[:char_limit]}...")
                                st.expander("View full raw content").write(raw_content)
                            else:
                                st.write(raw_content)
                        
                        # Display media content for Reddit posts if available
                        if row["Platform"] == "Reddit" and "ContentType" in row and "MediaURL" in row and row["MediaURL"]:
                            if row["ContentType"] == "image":
                                st.image(row["MediaURL"], use_container_width=True)
                            elif row["ContentType"] == "video":
                                st.video(row["MediaURL"])
                        
                        # If URL exists, make it clickable
                        if "URL" in row and row["URL"]:
                            st.markdown(f"[View Source]({row['URL']})")
                    
                    st.divider()
            
            # Add page navigation at the bottom with improved styling
            st.markdown("""
            <style>
            .stButton {
                display: flex;
                width: 100%;
            }
            .stButton > button {
                width: 100%;
                padding: 0.5rem 1rem;
            }
            div[data-testid="column"] {
                display: flex;
                align-items: center;
            }
            div[data-testid="column"]:first-child {
                justify-content: flex-start;
            }
            div[data-testid="column"]:nth-child(2) {
                justify-content: center;
            }
            div[data-testid="column"]:last-child {
                justify-content: flex-end;
            }
            </style>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col1:
                if st.button("Previous Page", disabled=current_page <= 1, key="prev_button", use_container_width=True):
                    st.session_state.current_page = max(1, current_page - 1)
            
            with col2:
                st.markdown(f"<div style='text-align: center; width: 100%;'>Page {current_page} of {total_pages}</div>", unsafe_allow_html=True)
            
            with col3:
                if st.button("Next Page", disabled=current_page >= total_pages, key="next_button", use_container_width=True):
                    st.session_state.current_page = min(total_pages, current_page + 1)

        # Also provide the traditional dataframe view if needed
        if st.checkbox("Show as table"):
            display_df = df.copy()
            # Remove raw_content from display to save space
            if "raw_content" in display_df.columns:
                display_df = display_df.drop(columns=["raw_content"])
            st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No data available for the selected filters.")

# Display engagement metrics
def display_metrics(df):
    print(df)
    st.header("Engagement Metrics")
    if not df.empty:
        # Create metrics columns
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Posts", len(df))
        with col2:
            st.metric("Unique Authors", df["Author"].nunique())
        
        # Create a bar chart for engagement by platform
        if platform == "All":
            platform_stats = df.groupby("Platform")["Engagement"].mean().reset_index()
            st.bar_chart(platform_stats.set_index("Platform"))
        else:
            st.bar_chart(df.set_index("Date")["Engagement"])
            
        # Add AI Analysis section
        st.subheader("AI Topic Analysis")
        
        if (not df.empty):
               # Add 5 second delay
            time.sleep(5)
            with st.spinner("Analyzing posts with AI..."):
                # Prepare prompt for topic analysis
                analysis_prompt = f"""
                Analyze the following set of {len(df)} healthcare-related posts and provide:
                1. Key Topics: Identify the main themes and topics being discussed
                2. Sentiment Analysis: Overall sentiment and emotional tone
                3. Key Insights: Extract valuable insights for healthcare professionals
                4. Emerging Trends: Identify any emerging trends or patterns
                5. Action Items: Suggest potential action items based on the analysis
                
                Focus on healthcare-specific insights and professional implications.
                """
                
                # Get analysis from OpenAI
                analysis_result = analyze_with_openai(df, analysis_prompt)
                
             
                
                # Display results in an expander
                with st.expander("View Analysis Results", expanded=True):
                    st.markdown(analysis_result)
        elif df.empty:
            st.warning("No posts available for analysis. Try adjusting your search filter.")
    else:
        st.info("No data available for the selected filters.")

# Display posts and metrics
if platform != "Big Data":
    display_posts(df)
else:
    st.header("Big Data Records")
    
    # Add tab-based interface for better organization
    tabs = st.tabs(["Data Table", "Visualizations", "Summary Metrics"])
    
    with tabs[0]:
        # Data table view with search functionality
        search_term = st.text_input("Search in content", "")
        
        display_df = df.copy()
        # Remove raw_content from display to save space
        if "raw_content" in display_df.columns:
            display_df = display_df.drop(columns=["raw_content"])
            
        # Apply search filter if provided
        if search_term:
            mask = display_df['Post'].str.contains(search_term, case=False, na=False)
            display_df = display_df[mask]
            st.write(f"Found {len(display_df)} records containing '{search_term}'")
            
        st.dataframe(display_df, use_container_width=True)
    
    with tabs[1]:
        # Enhanced visualizations
        st.subheader("Post Distribution")
        fig_col1, fig_col2 = st.columns(2)
        
        with fig_col1:
            # Group posts by date and count them
            post_counts = df.groupby(df['Date'].dt.date).size().reset_index(name='Count')
            st.bar_chart(post_counts.set_index('Date'), use_container_width=True)
            st.caption("Posts by Date")
            
        with fig_col2:
            # Count posts by platform
            platform_counts = df['Platform'].value_counts().reset_index()
            platform_counts.columns = ['Platform', 'Count']
            st.bar_chart(platform_counts.set_index('Platform'))
            st.caption("Post Count by Platform")
    
    with tabs[2]:
        # Key metrics in a more visual format
        metric_cols = st.columns(2)
        with metric_cols[0]:
            st.metric("Total Posts", len(df))
        with metric_cols[1]:
            st.metric("Unique Authors", df["Author"].nunique())

# Always display metrics at the bottom
display_metrics(df)
