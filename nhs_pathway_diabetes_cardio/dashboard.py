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
    page_title="NHS Pathway Analysis",
    page_icon="🏥",

)


st.title("🏥 NHS Pathway Analysis Dashboard")

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

# Define relevant terms for each category
diabetes_terms = ['diabetes', 'diabetic', 'insulin', 'blood sugar', 'glucose', 'type 1', 'type 2', 'hba1c', 'diabetic ketoacidosis']
cardio_terms = ['cardio', 'cardiovascular', 'heart', 'hypertension', 'blood pressure', 'cholesterol', 'stroke', 'myocardial', 'angina', 'arrhythmia']

# Common medical terms to track
medical_terms = [
    'treatment', 'diagnosis', 'symptoms', 'patient', 'clinical', 'therapy', 'medicine',
    'disease', 'condition', 'infection', 'injury', 'surgery', 'procedure', 'rehabilitation',
    'prevention', 'management', 'care', 'health', 'medical', 'hospital', 'clinic',
    'doctor', 'nurse', 'specialist', 'consultant', 'prescription', 'medication', 'drug',
    'vaccine', 'test', 'examination', 'assessment', 'monitoring', 'follow-up', 'referral',
    'emergency', 'acute', 'chronic', 'severe', 'mild', 'moderate', 'risk', 'complication'
]



def generate_insights(prompt, data_sample):
    client = openai.OpenAI(api_key=openai.api_key)
   
    prompt = f"""
    {current_prompt}
    
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

try:
    # Add data loading indicator
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
    
    # Filter to include only UK and Ireland related content
    uk_ire_pattern = '|'.join(uk_ire_terms)
    uk_ire_mask = df['content'].str.contains(uk_ire_pattern, case=False, na=False)
    df = df[uk_ire_mask]
    
    # Filter for pathway-related terms (case insensitive)
    pathway_terms = ['pathway', 'path', 'route', 'track', 'course', 'roadmap']
    pathway_mask = df['title'].str.contains('|'.join(pathway_terms), case=False, na=False) | \
                  df['content'].str.contains('|'.join(pathway_terms), case=False, na=False)
    filtered_df = df[pathway_mask]
    
    # Remove duplicates based on content
    filtered_df = filtered_df.drop_duplicates(subset=['content'])

    
    with st.expander("🛣️ Pathway-related entries", expanded=False):  # expanded=False means minimized by default
        # st.write(f"{len(filtered_df)} found. UK/IRE only.")
        show_all = st.checkbox("Show all entries", value=False)
        if show_all:
            st.dataframe(df)
        else:
            st.dataframe(filtered_df)
    
    # Count occurrences of terms in content
    # Add OpenAI Insights section
    st.write("### 🤖 AI-Powered Clinical Pathway Analysis")
    
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
            help="Modify this prompt to change how the AI analyzes the pathway content. Click outside the textbox to save changes."
        )
        
        # Show the "Update Prompt" button only if the prompt has changed
        if current_prompt != st.session_state.original_prompt:
            if st.button("Update Prompt", type="primary", use_container_width=True):
                update_prompt_api(current_prompt)
                st.session_state.original_prompt = current_prompt  # Update the session state
                st.success("Prompt updated successfully.")
    
    # Add a button to generate insights
    if st.button("🔍 Generate Insights", type="primary", use_container_width=True):
        st.write("Generating insights...") 
        with st.spinner("Analyzing clinical pathways and generating insights..."):
            # Check if the "Show all entries" checkbox is checked
            if show_all:
                data_sample_df = df
            else:
                data_sample_df = filtered_df

            data_sample = "\n".join([
                f"Title: {row['title']}\nContent: {row['content']}\n"
                for _, row in data_sample_df.head(5).iterrows()
            ])
            insights = generate_insights(prompt, data_sample)
            st.write(insights)

    def count_terms(text, terms):
        if pd.isna(text):
            return 0
        text = text.lower()
        return sum(1 for term in terms if term.lower() in text)
    
    # # Calculate counts for each category
    # diabetes_counts = filtered_df['content'].apply(lambda x: count_terms(x, diabetes_terms))
    # cardio_counts = filtered_df['content'].apply(lambda x: count_terms(x, cardio_terms))
    
    # # Create bar chart
    # fig, ax = plt.subplots(figsize=(10, 6))
    # categories = ['Diabetes-related', 'Cardiovascular-related']
    # counts = [diabetes_counts.sum(), cardio_counts.sum()]
    
    # bars = ax.bar(categories, counts)
    # ax.set_title('📊 Frequency of Diabetes and Cardiovascular Terms')
    # ax.set_ylabel('Number of Occurrences')
    
    # # Add value labels on top of bars
    # for bar in bars:
    #     height = bar.get_height()
    #     ax.text(bar.get_x() + bar.get_width()/2., height,
    #             f'{int(height)}',
    #             ha='center', va='bottom')
    
    # st.write("### 🔍 Term Frequency Analysis")
    # st.pyplot(fig)
    
    # # Count medical terms
    # medical_counts = {}
    # for term in medical_terms:
    #     count = filtered_df['content'].apply(lambda x: count_terms(x, [term])).sum()
    #     medical_counts[term] = count
    
    # # Sort terms by frequency and get top 10
    # top_terms = dict(sorted(medical_counts.items(), key=lambda x: x[1], reverse=True)[:10])
    
    # # Create bar chart for top medical terms
    # fig2, ax2 = plt.subplots(figsize=(10, 6))
    # bars2 = ax2.bar(range(len(top_terms)), list(top_terms.values()))
    # ax2.set_title('🏥 Top 10 Most Frequent Medical Terms')
    # ax2.set_ylabel('Number of Occurrences')
    # ax2.set_xticks(range(len(top_terms)))
    # ax2.set_xticklabels(list(top_terms.keys()), rotation=45, ha='right')
    
    # # Add value labels on top of bars
    # for bar in bars2:
    #     height = bar.get_height()
    #     ax2.text(bar.get_x() + bar.get_width()/2., height,
    #             f'{int(height)}',
    #             ha='center', va='bottom')
    
    # st.write("### 💊 Medical Terms Analysis")
    # st.pyplot(fig2)
    
    # # Create word cloud
    # st.write("### 🌟 Word Cloud Analysis")
    # # Combine all content
    # text = ' '.join(filtered_df['content'].dropna().astype(str))
    
    # # Create word cloud with built-in stopwords
    # wordcloud = WordCloud(
    #     width=1200, 
    #     height=800, 
    #     background_color='white',
    #     stopwords=STOPWORDS,
    #     min_word_length=3
    # ).generate(text)
    
    # # Display word cloud
    # fig3, ax3 = plt.subplots(figsize=(15, 10))
    # ax3.imshow(wordcloud, interpolation='bilinear')
    # ax3.axis('off')
    # st.pyplot(fig3)
    

    
except Exception as e:
    st.error(f"❌ Failed to load data: {e}")
