import streamlit as st
import pandas as pd
import http.client
import json
import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta
import gspread
from google.oauth2 import service_account
import os

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
    options=["All", "LinkedIn", "Reddit", "Twitter"],
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
        "past-24h": "Past 24 Hours",
        "past-week": "Past Week",
        "past-month": "Past Month"
    }
    date_posted = st.sidebar.selectbox(
        "Date Posted",
        options=list(date_options.keys()),
        format_func=lambda x: date_options[x],
        index=0,
        help="Filter posts by when they were posted"
    )

# Function to connect to Google Sheets
def connect_to_gsheets():
    # Create a connection object
    try:
        # Check if credentials exist as environment variables
        if 'GOOGLE_CREDENTIALS' in os.environ:
            # Use credentials from environment variables
            credentials = service_account.Credentials.from_service_account_info(
                json.loads(os.environ['GOOGLE_CREDENTIALS'])
            )
        else:
            # For local development - show instructions
            st.sidebar.warning(
                "Google Sheets integration requires credentials. "
                "To add data to Google Sheets, you'll need to set up a service account and credentials."
            )
            return None
            
        # Create a client using the credentials
        gc = gspread.authorize(credentials)
        
        # Open the Google Sheets document
        sheet_url = "https://docs.google.com/spreadsheets/d/1g_jOglUhuARGoDFLeHG0jNAXCFMF7Z5JIFZS_WoFOk8/edit?usp=sharing"
        sheet_id = sheet_url.split('/')[5]  # Extract the sheet ID from the URL
        sh = gc.open_by_key(sheet_id)
        
        # Select the first worksheet
        worksheet = sh.sheet1
        
        return worksheet
    except Exception as e:
        st.sidebar.error(f"Error connecting to Google Sheets: {str(e)}")
        st.sidebar.info("Adding data to Google Sheets is currently unavailable. Data will only be displayed locally.")
        return None

# Add data to Google Sheet using API
def add_to_google_sheet(df, search_query=""):
    try:
        # Get the token from secrets
        # Get the token from secrets
        sheets_token = st.secrets["gsheets"]["api_token"]

        print(sheets_token)
        
        
        # Google Sheet ID from the URL
        sheet_url = "https://docs.google.com/spreadsheets/d/1g_jOglUhuARGoDFLeHG0jNAXCFMF7Z5JIFZS_WoFOk8/edit?usp=sharing"
        sheet_id = sheet_url.split('/')[5]  # Extract the sheet ID from the URL
        
        # Endpoint for the Google Sheets API
        api_endpoint = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/Sheet1!A:G:append?valueInputOption=RAW"
        
        # Authorization header
        headers = {
            "Authorization": f"Bearer {sheets_token}",
            "Content-Type": "application/json"
        }
        
        # Convert DataFrame to list of lists for the API
        rows = []
        for _, row in df.iterrows():
            rows.append([
                row.get('Platform', ''),
                row.get('Post', ''),
                row.get('Date', '').strftime('%Y-%m-%d %H:%M:%S') if isinstance(row.get('Date'), datetime) else str(row.get('Date', '')),
                row.get('Engagement', 0),
                row.get('Author', ''),
                row.get('URL', ''),
                search_query  # Add the search query
            ])
        
        # Prepare the request body
        data = {
            "values": rows
        }
        
        # Make the API request
        response = requests.post(api_endpoint, headers=headers, json=data)
        
        # Check the response
        if response.status_code == 200:
            st.sidebar.success(f"Successfully saved {len(rows)} posts with search term '{search_query}'")
            return True
        else:
            st.sidebar.error(f"Error saving data: {response.json().get('error', {}).get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        st.sidebar.error(f"Error saving data: {str(e)}")
        return False

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
        
        # Process the LinkedIn API response into a DataFrame
        if 'success' in response and response['success'] and 'data' in response and 'items' in response['data']:
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
        else:
            st.error("Failed to retrieve LinkedIn data. API response format unexpected.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching LinkedIn data: {str(e)}")
        return pd.DataFrame()

# Mock data from Google Sheet
def load_mock_data_from_sheet():
    try:
        with st.spinner("Loading test data from Google Sheet..."):
            sheet_url = "https://docs.google.com/spreadsheets/d/1g_jOglUhuARGoDFLeHG0jNAXCFMF7Z5JIFZS_WoFOk8/edit?usp=sharing"
            sheet_url = sheet_url.replace('/edit?usp=sharing', '/export?format=csv')
            df = pd.read_csv(sheet_url)
            
            # Convert Date column to datetime
            df["Date"] = pd.to_datetime(df["Date"])
            
            if not df.empty:
                st.success(f"Successfully loaded {len(df)} posts from Google Sheet as default dataset")
                return df
    except Exception as e:
        st.error(f"Error loading data from Google Sheet: {str(e)}")
    
    # Return empty DataFrame if failed
    return generate_mock_data()

# Mock data for demonstration (empty fallback)
def generate_mock_data():
    data = {
        "Platform": [],
        "Post": [],
        "Date": [],
        "Engagement": [],
        "Author": []
    }
    # Create an empty DataFrame with proper data types
    df = pd.DataFrame(data)
    # Ensure Date column is datetime type
    df["Date"] = pd.to_datetime(df["Date"])
    return df

# Function to fetch Twitter data
def get_twitter_data(keyword="nhs pathway", max_results=10):
    conn = http.client.HTTPSConnection("twitter-api45.p.rapidapi.com")
    
    # Replace spaces with %20 for URL encoding
    encoded_keyword = keyword.replace(" ", "%20")
    
    # Get API key from secrets
    try:
        api_key = st.secrets["rapidapi"]["key"]
    except Exception:
        # Fallback to hardcoded key if not in secrets
        api_key = "3eca41dc64msh3451e843edfa53ap1c8f67jsn11d94a78f291"
    
    headers = {
        'x-rapidapi-key': api_key,
        'x-rapidapi-host': "twitter-api45.p.rapidapi.com"
    }
    
    # Construct the endpoint to search tweets
    endpoint = f"/search.php?query={encoded_keyword}&max_results={max_results}"
    
    try:
        conn.request("GET", endpoint, headers=headers)
        res = conn.getresponse()
        data = res.read()
        response = json.loads(data.decode("utf-8"))
        
        # Process the Twitter API response into a DataFrame
        if 'timeline' in response:
            posts = []
            for tweet in response['timeline']:
                if tweet.get('type') == 'tweet':
                    # Calculate engagement as sum of interactions
                    engagement = (
                        tweet.get('favorites', 0) + 
                        tweet.get('retweets', 0) + 
                        tweet.get('replies', 0) + 
                        tweet.get('quotes', 0) +
                        tweet.get('bookmarks', 0)
                    )
                    
                    # Get media URL if available
                    media_url = ""
                    if 'media' in tweet:
                        if 'photo' in tweet['media'] and len(tweet['media']['photo']) > 0:
                            media_url = tweet['media']['photo'][0].get('media_url_https', '')
                        elif 'video' in tweet['media'] and len(tweet['media']['video']) > 0:
                            media_url = tweet['media']['video'][0].get('media_url_https', '')
                    
                    created_time = datetime.strptime(tweet.get('created_at', ''), "%a %b %d %H:%M:%S %z %Y") if 'created_at' in tweet else datetime.now()
                    
                    posts.append({
                        "Platform": "Twitter",
                        "Post": tweet.get('text', 'No content'),
                        "Date": created_time,
                        "Engagement": engagement,
                        "Author": tweet.get('screen_name', 'Unknown'),
                        "URL": f"https://twitter.com/{tweet.get('screen_name')}/status/{tweet.get('tweet_id')}"
                    })
            return pd.DataFrame(posts)
        else:
            st.error("Failed to retrieve Twitter data. API response format unexpected.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching Twitter data: {str(e)}")
        return pd.DataFrame()

# Twitter specific filters (only show when Twitter is selected)
twitter_keyword = ""
if platform == "Twitter":
    st.sidebar.subheader("Twitter Filters")
    twitter_keyword = st.sidebar.text_input("Search Keyword", "")
    twitter_max_results = 50

# Load data based on selected platform
if platform == "LinkedIn" and linkedin_keyword and linkedin_keyword.lower() != "":
    # Only use the API if a keyword is provided and it's not empty
    with st.spinner("Fetching LinkedIn data..."):
        try:
            linkedin_df = get_linkedin_data(linkedin_keyword, linkedin_sort, date_posted)
            if not linkedin_df.empty:
                df = linkedin_df
                # Sort by engagement in descending order
                df = df.sort_values(by="Engagement", ascending=False)
                st.success(f"Successfully retrieved {len(df)} LinkedIn posts")
                
                # Automatically save results to Google Sheet
                add_to_google_sheet(df, linkedin_keyword)
            else:
                st.warning("Could not retrieve LinkedIn data. Using mockup data instead.")
                df = load_mock_data_from_sheet()
                # Sort by engagement in descending order
                df = df.sort_values(by="Engagement", ascending=False)
        except Exception as e:
            st.error(f"Error: {str(e)}")
            df = load_mock_data_from_sheet()
            # Sort by engagement in descending order
            df = df.sort_values(by="Engagement", ascending=False)
            st.warning("Using mockup data due to API error.")
elif platform == "Twitter" and twitter_keyword and twitter_keyword.lower() != "":
    # Use Twitter API if a keyword is provided for Twitter
    with st.spinner("Fetching Twitter data..."):
        try:
            twitter_df = get_twitter_data(twitter_keyword, twitter_max_results)
            if not twitter_df.empty:
                df = twitter_df
                # Sort by engagement in descending order
                df = df.sort_values(by="Engagement", ascending=False)
                st.success(f"Successfully retrieved {len(df)} Twitter posts")
                
                # Automatically save results to Google Sheet
                add_to_google_sheet(df, twitter_keyword)
            else:
                st.warning("Could not retrieve Twitter data. Using mockup data instead.")
                df = load_mock_data_from_sheet()
                # Filter to only Twitter posts
                df = df[df["Platform"] == "Twitter"]
                # Sort by engagement in descending order
                df = df.sort_values(by="Engagement", ascending=False)
        except Exception as e:
            st.error(f"Error: {str(e)}")
            df = load_mock_data_from_sheet()
            # Filter to only Twitter posts
            df = df[df["Platform"] == "Twitter"]
            # Sort by engagement in descending order
            df = df.sort_values(by="Engagement", ascending=False)
            st.warning("Using mockup data due to API error.")
else:
    # Load from Google Sheet by default
    df = load_mock_data_from_sheet()
    
    # Filter by platform if needed
    if platform != "All":
        df = df[df["Platform"] == platform]
    
    # Sort by engagement in descending order
    df = df.sort_values(by="Engagement", ascending=False)

# Display filtered data
st.header("Posts")

# Create a more detailed display for posts
if not df.empty:
    for i, row in df.iterrows():
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
                
                # Display engagement metrics
                st.metric("Engagement", row["Engagement"])
            
            with col2:
                # Author and date
                st.markdown(f"**{row['Author']}** • {row['Date'].strftime('%Y-%m-%d')}")
                
                # Post content
                st.write(row["Post"])
                
                # If URL exists, make it clickable
                if "URL" in row and row["URL"]:
                    st.markdown(f"[View on {row['Platform']}]({row['URL']})")
            
            st.divider()

    # Also provide the traditional dataframe view if needed
    if st.checkbox("Show as table"):
        st.dataframe(df, use_container_width=True)
else:
    st.info("No data available for the selected filters.")

# Show engagement metrics
st.header("Engagement Metrics")
if not df.empty:
    # Create metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Posts", len(df))
    with col2:
        st.metric("Average Engagement", round(df["Engagement"].mean(), 2))
    with col3:
        st.metric("Max Engagement", df["Engagement"].max())
    
    # Create a bar chart for engagement by platform
    if platform == "All":
        platform_stats = df.groupby("Platform")["Engagement"].mean().reset_index()
        st.bar_chart(platform_stats.set_index("Platform"))
    else:
        st.bar_chart(df.set_index("Date")["Engagement"])
else:
    st.info("No data available for the selected filters.")

# Remove date filter section and replace with just min engagement
# st.sidebar.header("Additional Filters")
# I DONT NEED ENGAGEMENT FILTER
min_engagement = 0

# Apply additional filters
if st.sidebar.button("Apply Filters"):
    if not df.empty:
        # Filter by platform
        if platform != "All":
            filtered_df = df[df["Platform"] == platform]
        else:
            filtered_df = df.copy()
        
        # Filter by engagement
        filtered_df = filtered_df[filtered_df["Engagement"] >= min_engagement]
        
        # Update display
        st.dataframe(filtered_df, use_container_width=True)
        
        # Update metrics
        if not filtered_df.empty:
            st.metric("Total Posts", len(filtered_df))
            st.metric("Average Engagement", round(filtered_df["Engagement"].mean(), 2))
            st.metric("Max Engagement", filtered_df["Engagement"].max())
        else:
            st.info("No data available for the selected filters.")
    else:
        st.info("No data available for filtering.") 