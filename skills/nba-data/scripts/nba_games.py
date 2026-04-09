#!/usr/bin/env python3
"""
NBA Games - Fetch live scores and game data
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

def fetch_todays_games():
    """Fetch today's games"""
    url = f"{BASE_URL}/scoreboard"
    return fetch_json(url)

def format_game(event):
    """Format a single game for display"""
    name = event.get('name', '')
    status = event.get('status', {}).get('type', {})
    status_desc = status.get('description', 'Unknown')
    status_detail = status.get('shortDetail', '')
    
    competitions = event.get('competitions', [])
    if not competitions:
        return f"{name} - No data available\n"
    
    comp = competitions[0]
    competitors = comp.get('competitors', [])
    if len(competitors) != 2:
        return f"{name} - Incomplete data\n"
    
    home = competitors[0] if competitors[0].get('homeAway') == 'home' else competitors[1]
    away = competitors[1] if competitors[0].get('homeAway') == 'home' else competitors[0]
    
    home_team = home.get('team', {}).get('displayName', 'Unknown')
    away_team = away.get('team', {}).get('displayName', 'Unknown')
    home_score = home.get('score', '-')
    away_score = away.get('score', '-')
    
    if status_desc == 'Final':
        return f"{away_team} @ {home_team}\n  Score: {away_score} - {home_score}\n  Status: FINAL\n"
    elif 'ET' in status_detail or ':' in status_detail:
        return f"{away_team} @ {home_team}\n  Time: {status_detail}\n  Status: Scheduled\n"
    else:
        return f"{away_team} @ {home_team}\n  Score: {away_score} - {home_score}\n  Status: {status_detail}\n"

def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "today"
    
    if command == "today":
        date = datetime.now().strftime("%Y-%m-%d")
        print(f"NBA Games for {date}\n" + "="*60)
    elif command == "date":
        print("Note: ESPN API fetches current schedule. For specific dates, use the website.")
        print(f"NBA Games\n" + "="*60)
    else:
        print("Usage: nba_games.py [today]")
        sys.exit(1)
    
    data = fetch_todays_games()
    events = data.get('events', [])
    
    if not events:
        print("No games found for today.")
        return
    
    for event in events:
        print(format_game(event))

if __name__ == "__main__":
    main()
