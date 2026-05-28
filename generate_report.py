#!/usr/bin/env python3
"""
Automated Daily Market Report Generator
Fetches market data, news, and generates AI summaries
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
import yfinance as yf
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize API clients
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
NEWSAPI_KEY = os.getenv('NEWSAPI_KEY')

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ============================================================================
# STEP 1: FETCH MARKET DATA
# ============================================================================

def fetch_market_data():
    """
    Fetch current market data for key indices and assets.
    Returns a dictionary with market data for each ticker.
    """
    
    # Define tickers and their display names
    tickers = {
        'NIFTY': '^NSEI',           # Nifty 50
        'SENSEX': '^BSESN',         # BSE Sensex
        'NASDAQ': '^IXIC',          # NASDAQ Composite
        'S&P500': '^GSPC',          # S&P 500
        'GOLD': 'GC=F',             # Gold futures
        'BITCOIN': 'BTC-USD',       # Bitcoin
        'USDINR': 'USDINR=X'        # USD/INR
    }
    
    market_data = {}
    
    # Fetch data for each ticker
    for name, ticker in tickers.items():
        try:
            data = yf.Ticker(ticker)
            # Get the latest available data
            history = data.history(period='2d')
            
            if len(history) >= 2:
                current_price = history['Close'].iloc[-1]
                previous_price = history['Close'].iloc[-2]
                change = current_price - previous_price
                change_percent = (change / previous_price) * 100 if previous_price != 0 else 0
                
                market_data[name] = {
                    'price': round(current_price, 2),
                    'change': round(change, 2),
                    'change_percent': round(change_percent, 2)
                }
            else:
                # Fallback if insufficient data
                market_data[name] = {
                    'price': 0,
                    'change': 0,
                    'change_percent': 0
                }
        except Exception as e:
            print(f"Error fetching data for {name}: {e}")
            market_data[name] = {
                'price': 0,
                'change': 0,
                'change_percent': 0
            }
    
    return market_data

# ============================================================================
# STEP 2: FETCH NEWS HEADLINES
# ============================================================================

def fetch_news():
    """
    Fetch top business and market news using NewsAPI directly.
    Returns a list of news articles with title and description.
    """
    
    try:
        # Using NewsAPI REST endpoint directly
        url = 'https://newsapi.org/v2/top-headlines'
        params = {
            'category': 'business',
            'language': 'en',
            'apiKey': NEWSAPI_KEY,
            'pageSize': 10
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        articles = []
        if data.get('status') == 'ok':
            for article in data.get('articles', [])[:6]:  # Get top 6 articles
                articles.append({
                    'title': article.get('title', 'No title'),
                    'description': article.get('description') or 'No description available',
                    'url': article.get('url', '#')
                })
        
        return articles
    
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []

# ============================================================================
# STEP 3: GENERATE AI SUMMARIES
# ============================================================================

def generate_market_summary(market_data, news_articles):
    """
    Use OpenAI API to generate a professional market summary.
    Input: market data and news articles
    Output: AI-generated market overview and macro commentary
    """
    
    # Format market data for the prompt
    market_text = "Current Market Data:\n"
    for index, data in market_data.items():
        market_text += f"- {index}: {data['price']} ({data['change_percent']:+.2f}%)\n"
    
    # Format news articles for the prompt
    news_text = "Top News Headlines:\n"
    for i, article in enumerate(news_articles[:5], 1):
        news_text += f"{i}. {article['title']}\n"
    
    # Create the prompt for OpenAI
    prompt = f"""
You are a professional financial analyst writing a daily market report.

{market_text}

{news_text}

Based on the market data and news above, write:

1. A 2-3 sentence market overview summarizing today's market movements
2. A 2-3 sentence macro commentary on key market drivers
3. A concise daily digest (2-3 sentences) with actionable insights

Keep the tone professional, concise, and institutional. Target audience: financial professionals.
"""
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional financial analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"Error generating AI summary: {e}")
        return "Unable to generate market summary at this time."

# ============================================================================
# STEP 4: INJECT DATA INTO HTML TEMPLATE
# ============================================================================

def inject_data_into_template(market_data, news_articles, ai_summary):
    """
    Read the HTML template and inject market data and AI summary.
    Saves the final output as index.html
    """
    
    # Read the template file
    with open('template.html', 'r') as f:
        html_content = f.read()
    
    # Get current date
    current_date = datetime.now().strftime('%B %d, %Y')
    
    # Generate market cards HTML
    market_cards_html = ""
    for index_name, data in market_data.items():
        # Determine color based on positive/negative change
        color_class = 'positive' if data['change_percent'] >= 0 else 'negative'
        sign = '+' if data['change_percent'] >= 0 else ''
        
        card_html = f"""
        <div class="market-card {color_class}">
            <div class="card-header">{index_name}</div>
            <div class="card-value">{data['price']}</div>
            <div class="card-change">{sign}{data['change_percent']:.2f}%</div>
        </div>
        """
        market_cards_html += card_html
    
    # Generate news cards HTML
    news_cards_html = ""
    for article in news_articles:
        card_html = f"""
        <div class="news-card">
            <h4>{article['title']}</h4>
            <p>{article['description'][:150]}...</p>
            <a href="{article['url']}" target="_blank">Read More →</a>
        </div>
        """
        news_cards_html += card_html
    
    # Replace placeholders in template
    html_content = html_content.replace('{{DATE}}', current_date)
    html_content = html_content.replace('{{MARKET_CARDS}}', market_cards_html)
    html_content = html_content.replace('{{AI_SUMMARY}}', ai_summary)
    html_content = html_content.replace('{{NEWS_CARDS}}', news_cards_html)
    
    # Save as index.html
    with open('index.html', 'w') as f:
        f.write(html_content)
    
    print("✓ Report generated successfully: index.html")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """
    Main function: orchestrate the entire report generation process
    """
    
    print("\n" + "="*60)
    print("AUTOMATED DAILY MARKET REPORT GENERATOR")
    print("="*60)
    
    # Step 1: Fetch market data
    print("\n[1/4] Fetching market data...")
    market_data = fetch_market_data()
    print(f"✓ Fetched data for {len(market_data)} indices")
    
    # Step 2: Fetch news
    print("\n[2/4] Fetching business news...")
    news_articles = fetch_news()
    print(f"✓ Fetched {len(news_articles)} news articles")
    
    # Step 3: Generate AI summary
    print("\n[3/4] Generating AI market summary...")
    ai_summary = generate_market_summary(market_data, news_articles)
    print("✓ AI summary generated")
    
    # Step 4: Inject into template and save
    print("\n[4/4] Generating HTML report...")
    inject_data_into_template(market_data, news_articles, ai_summary)
    
    print("\n" + "="*60)
    print("REPORT GENERATION COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
