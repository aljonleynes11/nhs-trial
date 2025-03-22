# HCP Research Tool

A Streamlit application for analyzing healthcare professional (HCP) content across various social media platforms.

## API Endpoints Used

This application uses the following RapidAPI endpoints:

1. LinkedIn API
   - Endpoint: `linkedin-api8.p.rapidapi.com`
   - Documentation: [LinkedIn API on RapidAPI](https://rapidapi.com/rockapis-rockapis-default/api/linkedin-api8)

2. Twitter API
   - Endpoint: `twitter154.p.rapidapi.com`
   - Documentation: [Twitter API on RapidAPI](https://rapidapi.com/omarmhaimdat/api/twitter154)

3. Reddit API
   - Endpoint: `reddit-scraper2.p.rapidapi.com`
   - Documentation: [Reddit API on RapidAPI](https://rapidapi.com/fkal094tiokg09w3vi095i/api/reddit-scraper2)

## Setup Instructions

1. Clone this repository
2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.streamlit/secrets.toml` file with your API keys:
   ```toml
   [rapidapi]
   key = "your-rapidapi-key"

   [openai]
   api_key = "your-openai-api-key"

   [webhook]
   url = "your-webhook-url"
   username = "your-webhook-username"
   password = "your-webhook-password"
   ```
4. Run the application:
   ```bash
   streamlit run app.py
   ```

## Features

- Search and filter content from LinkedIn, Twitter, and Reddit
- Analyze healthcare professional discussions
- View engagement metrics and visualizations
- AI-powered topic analysis
- Export data to Google Sheets

## Note

You'll need to subscribe to the respective RapidAPI endpoints to get API keys. Each endpoint has its own pricing and subscription options. 