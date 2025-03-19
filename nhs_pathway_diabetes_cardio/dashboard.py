import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud, STOPWORDS
import re
from collections import Counter
import openai
from datetime import datetime
import base64
import requests

# Set page config for better UI
st.set_page_config(
    page_title=" HCP Research Tool",
    page_icon="🏥",

)

st.title("🏥 HCP Research Tool")

# Configure OpenAI
openai.api_key = st.secrets["openai"]["api_key"]

# Google Sheets URL (CSV export link)
sheet_url = st.secrets["api_credentials"]["dataset"]

# List of countries to exclude
excluded_countries = [
    'United States', 'USA', 'US', 'America', 'American',
    'Canada', 'Canadian',
    'Australia', 'Australian',
    'New Zealand', 'NZ',
    'South Africa', 'SA',
    'India', 'Indian',
    'China', 'Chinese',
    'Japan', 'Japanese',
    'Germany', 'German',
    'France', 'French',
    'Italy', 'Italian',
    'Spain', 'Spanish',
    'Brazil', 'Brazilian',
    'Mexico', 'Mexican',
    'Russia', 'Russian',
    'South Korea', 'Korean',
    'Singapore', 'Singaporean',
    'Malaysia', 'Malaysian',
    'Thailand', 'Thai',
    'Vietnam', 'Vietnamese',
    'Philippines', 'Filipino',
    'Indonesia', 'Indonesian',
    'Pakistan', 'Pakistani',
    'Bangladesh', 'Bangladeshi',
    'Egypt', 'Egyptian',
    'Nigeria', 'Nigerian',
    'Kenya', 'Kenyan',
    'Ghana', 'Ghanaian',
    'Morocco', 'Moroccan',
    'Turkey', 'Turkish',
    'Israel', 'Israeli',
    'Saudi Arabia', 'Saudi',
    'UAE', 'United Arab Emirates',
    'Qatar', 'Qatari',
    'Kuwait', 'Kuwaiti',
    'Bahrain', 'Bahraini',
    'Oman', 'Omani',
    'Lebanon', 'Lebanese',
    'Jordan', 'Jordanian',
    'Iraq', 'Iraqi',
    'Iran', 'Iranian',
    'Afghanistan', 'Afghan',
    'Sri Lanka', 'Sri Lankan',
    'Nepal', 'Nepalese',
    'Myanmar', 'Burmese',
    'Cambodia', 'Cambodian',
    'Laos', 'Laotian',
    'Mongolia', 'Mongolian',
    'Kazakhstan', 'Kazakh',
    'Uzbekistan', 'Uzbek',
    'Azerbaijan', 'Azerbaijani',
    'Georgia', 'Georgian',
    'Armenia', 'Armenian',
    'Ukraine', 'Ukrainian',
    'Poland', 'Polish',
    'Czech Republic', 'Czech',
    'Slovakia', 'Slovak',
    'Hungary', 'Hungarian',
    'Romania', 'Romanian',
    'Bulgaria', 'Bulgarian',
    'Greece', 'Greek',
    'Portugal', 'Portuguese',
    'Netherlands', 'Dutch',
    'Belgium', 'Belgian',
    'Switzerland', 'Swiss',
    'Austria', 'Austrian',
    'Sweden', 'Swedish',
    'Norway', 'Norwegian',
    'Denmark', 'Danish',
    'Finland', 'Finnish',
]

def generate_related_terms(user_keywords):
    client = openai.OpenAI(api_key=openai.api_key)
   
    prompt = f"""
    User Keywords: {user_keywords}
    Expand the search to include all related terms.
    Return only a comma-separated list of words, with no explanations.
    """

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a data expert assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    # Ensuring only a clean comma-separated string is returned
    return response.choices[0].message.content.strip()


def get_auth_header():
    credentials = f"{st.secrets.api_credentials.username}:{st.secrets.api_credentials.password}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {encoded_credentials}"}

def fetch_prompts_from_api():
    headers = get_auth_header()
    try:
        response = requests.get(st.secrets.api_credentials.fetch_endpoint, headers=headers)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        
        data = response.json()
        if 'prompt' in data:
            return data['prompt']
        else:
            st.error("No 'prompt' attribute found in API response")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to fetch prompts: {str(e)}")
        return None

def update_prompt_api(new_prompt):
    headers = get_auth_header()
    try:
        response = requests.post(
            st.secrets.api_credentials.update_endpoint,
            headers=headers,
            json={"prompt": new_prompt}
        )
        response.raise_for_status()  # Raises an HTTPError for bad responses
        st.success("Prompt updated successfully.")
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to update prompt: {str(e)}")

def generate_insights(prompt, data_sample, user_keywords):
    generated_keywords = st.session_state.get('generated_keywords', user_keywords)
    print(generated_keywords)
    client = openai.OpenAI(api_key=openai.api_key)
   
    prompt = f"""
    {current_prompt}
    
    User Keywords: {generated_keywords}
    From this, please expand the search to include all related terms.
    
    Dataset Sample:
    {data_sample}
    """

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a data analysis expert."},
            {"role": "user", "content": prompt}
        ]
    )
    
    return response.choices[0].message.content


try:
    # Add data loading indicator
    st.session_state.generated_keywords = st.session_state.get('generated_keywords', 'diabetes, heart disease')
    with st.spinner("📊 Loading data..."):
        df = pd.read_csv(sheet_url)
    prompt = fetch_prompts_from_api()
    # Define UK and Ireland related terms
    uk_ire_terms = [
        'UK', 'U.K.', 'United Kingdom', 
        'Britain', 'British', 'GB', 'Great Britain',
        'England', 'English', 'NHS',
        'Scotland', 'Scottish', 
        'Wales', 'Welsh',
        'Northern Ireland', 'NI',
        'Ireland', 'Irish', 'IRE',
        'NICE', 'National Institute for Health and Care Excellence',
        'ICB', 'ICBs', 'Integrated Care Board'
    ]
    
    
    st.write("### 🔑 Enter keywords (comma-separated)")
    user_keywords = st.text_area(
        "",
        help="Provide keywords to filter the content. For example: diabetes, heart disease.",
        value="diabetes, heart disease",
        key="key_editor",
    )

    if st.button("🔍 Apply Keywords", type="primary", use_container_width=True):
        with st.spinner("Generating related terms..."):
            new_keywords = generate_related_terms(user_keywords)
            st.session_state.generated_keywords = new_keywords
            st.success(f"Related keywords generated \n\n {new_keywords}")


    # Filter to include only UK and Ireland related content
    uk_ire_pattern = '|'.join(uk_ire_terms)
    uk_ire_mask = df['content'].str.contains(uk_ire_pattern, case=False, na=False)
    df = df[uk_ire_mask]
    
    # Filter for pathway-related terms (case insensitive)
    pathway_terms = st.session_state.generated_keywords.split(',')
    pathway_mask = df['title'].str.contains('|'.join(pathway_terms), case=False, na=False) | \
                  df['content'].str.contains('|'.join(pathway_terms), case=False, na=False)
    filtered_df = df[pathway_mask]
    
    # Remove duplicates based on content
    filtered_df = filtered_df.drop_duplicates(subset=['content'])
    
    st.write("### 📊 Data Set")

    with st.expander("📂 Show All Entries", expanded=False):
        show_all = st.dataframe(filtered_df, use_container_width=True, hide_index=True)

    # placeholder = st.empty()  # Create a placeholder

    # # Hide the dataframe by clearing the placeholder
    # placeholder.empty()
    
    
    # Count occurrences of terms in content
    # Add OpenAI Insights section


    
    st.write("### 🤖 Enter Prompt")
    
    # Add prompt configuration section right before the generate button
    with st.expander("⚙️ Analysis Prompt Configuration", expanded=True):

        # Initialize session state for the prompt if it doesn't exist
        if "original_prompt" not in st.session_state:
            st.session_state.original_prompt = prompt

        current_prompt = st.text_area(
            "Analysis prompt:",
            value=st.session_state.original_prompt,
            height=500,
            key="prompt_editor",
            help="Modify this prompt to change how the AI analyzes the data content. Click outside the textbox to save changes."
        )
        
        # Show the "Update Prompt" button only if the prompt has changed
        if current_prompt != st.session_state.original_prompt:
            if st.button("Update Prompt", type="primary", use_container_width=True):
                update_prompt_api(current_prompt)
                st.session_state.original_prompt = current_prompt  # Update the session state
                st.success("Prompt updated successfully.")
        
        # Update the session state when the prompt is changed
        st.session_state.original_prompt = current_prompt  # Ensure session state is updated
    
    

    # Update the button to generate insights to include user keywords
    if st.button("🔍 Generate Insights", type="primary", use_container_width=True):
        st.write("") 
        with st.spinner("Analyzing keywords and generating insights..."):
            # Check if the "Show all entries" checkbox is checked
            if show_all:
                data_sample_df = df
            else:
                data_sample_df = filtered_df

            data_sample = "\n".join([
                f"Title: {row['title']}\nContent: {row['content']}\n"
                for _, row in data_sample_df.head(5).iterrows()
            ])
            insights = generate_insights(prompt, data_sample, user_keywords)  # Pass user keywords
            st.write(insights)
    
    
except Exception as e:
    st.error(f"❌ Failed to load data: {e}")
