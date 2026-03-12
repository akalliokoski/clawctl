#!/usr/bin/env python3
"""
NBA News - Fetch latest NBA headlines
Uses ESPN public API (free, no key required)
"""

import sys
import json
import urllib.request
from datetime import datetime

BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"

def fetch_json(url):
    """Fetch JSON from ESPN API"""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (OpenClaw NBA Skill)'
        })
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching data: {e}")
        return {}

def fetch_news(limit=10):
    """Fetch NBA news headlines"""
    url = f"{BASE_URL}/news"
    data = fetch_json(url)
    return data.get('articles', [])[:limit]

def format_article(article, index):
    """Format a news article"""
    headline = article.get('headline', 'No headline')
    description = article.get('description', '')
    published = article.get('published', '')
    link = article.get('links', {}).get('web', {}).get('href', '')
    byline = article.get('byline', '')
    
    # Format date
    date_str = ""
    if published:
        try:
            date = datetime.fromisoformat(published.replace('Z', '+00:00'))
            date_str = date.strftime("%b %d, %Y")
        except:
            date_str = published[:10]
    
    output = f"\n{index}. {headline}"
    if byline:
        output += f"\n   By: {byline}"
    if date_str:
        output += f" | {date_str}"
    if description:
        # Truncate long descriptions
        desc = description[:200] + "..." if len(description) > 200 else description
        output += f"\n   {desc}"
    if link:
        output += f"\n   {link}"
    
    return output

def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 10
    
    print(f"NBA News - Latest Headlines")
    print("="*60)
    
    articles = fetch_news(limit)
    
    if not articles:
        print("No news articles found.")
        return
    
    for i, article in enumerate(articles, 1):
        print(format_article(article, i))

if __name__ == "__main__":
    main()
