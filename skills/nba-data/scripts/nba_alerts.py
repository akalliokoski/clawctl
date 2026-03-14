#!/usr/bin/env python3
"""
NBA Alerts - Check for key matchups and send notifications
Uses ESPN public API (free, no key required)
"""

import sys
import json
import urllib.request
from datetime import datetime

BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"

# Key teams to watch (playoff contenders, rivals, etc.)
KEY_TEAMS = [
    "Lakers", "Clippers", "Warriors", "Suns", "Nuggets", "Thunder", "Timberwolves", "Mavericks",
    "Celtics", "Knicks", "76ers", "Bucks", "Heat", "Cavaliers"
]

# Rivalry matchups
RIVALRIES = [
    ("Lakers", "Celtics"), ("Lakers", "Warriors"), ("Lakers", "Clippers"),
    ("Celtics", "76ers"), ("Knicks", "Nets"),
    ("Warriors", "Rockets"), ("Thunder", "Warriors"),
    ("Bulls", "Pistons"), ("Heat", "Knicks")
]

def fetch_json(url):
    """Fetch JSON from ESPN API"""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (OpenClaw NBA Skill)'
        })
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return {}

def is_key_matchup(event):
    """Determine if a game is a key matchup"""
    competitions = event.get('competitions', [])
    if not competitions:
        return False, None
    
    comp = competitions[0]
    competitors = comp.get('competitors', [])
    if len(competitors) != 2:
        return False, None
    
    home = competitors[0] if competitors[0].get('homeAway') == 'home' else competitors[1]
    away = competitors[1] if competitors[0].get('homeAway') == 'home' else competitors[0]
    
    home_team = home.get('team', {}).get('displayName', '')
    away_team = away.get('team', {}).get('displayName', '')
    home_name = home.get('team', {}).get('name', '')
    away_name = away.get('team', {}).get('name', '')
    
    reasons = []
    
    # Check for rivalry
    for riv1, riv2 in RIVALRIES:
        if (riv1 in home_name and riv2 in away_name) or (riv2 in home_name and riv1 in away_name):
            reasons.append("Rivalry Game")
            break
    
    # Check for playoff contenders
    home_key = any(kt in home_name for kt in KEY_TEAMS)
    away_key = any(kt in away_name for kt in KEY_TEAMS)
    
    if home_key and away_key:
        reasons.append("Playoff Contenders")
    
    if reasons:
        return True, reasons
    
    return False, None

def format_alert(event, reasons):
    """Format a game alert"""
    competitions = event.get('competitions', [])
    comp = competitions[0]
    competitors = comp.get('competitors', [])
    
    home = competitors[0] if competitors[0].get('homeAway') == 'home' else competitors[1]
    away = competitors[1] if competitors[0].get('homeAway') == 'home' else competitors[0]
    
    home_team = home.get('team', {}).get('displayName', '')
    away_team = away.get('team', {}).get('displayName', '')
    time = event.get('status', {}).get('type', {}).get('shortDetail', 'TBD')
    
    output = f"\n{away_team} @ {home_team}"
    output += f"\n   Time: {time}"
    output += f"\n   Tags: {', '.join(reasons)}"
    
    return output

def check_todays_matchups():
    """Check for key matchups today"""
    url = f"{BASE_URL}/scoreboard"
    data = fetch_json(url)
    events = data.get('events', [])
    
    if not events:
        return None
    
    date = datetime.now().strftime("%Y-%m-%d")
    alerts = []
    
    for event in events:
        status = event.get('status', {}).get('type', {}).get('description', '')
        if status == 'Final':
            continue
        
        is_key, reasons = is_key_matchup(event)
        if is_key:
            alerts.append(format_alert(event, reasons))
    
    if not alerts:
        return None
    
    output = f"NBA Key Matchups Alert - {date}\n"
    output += "="*60
    output += "".join(alerts)
    output += "\n\nDon't miss these games!"
    
    return output

def main():
    alerts = check_todays_matchups()
    
    if alerts:
        print(alerts)
    else:
        url = f"{BASE_URL}/scoreboard"
        data = fetch_json(url)
        events = [e for e in data.get('events', []) if e.get('status', {}).get('type', {}).get('description') != 'Final']
        
        if events:
            print(f"NBA Schedule Today - {datetime.now().strftime('%Y-%m-%d')}")
            print("="*60)
            print(f"\n{len(events)} games scheduled today.")
            print("No major rivalry or top-tier matchups detected.")
        else:
            print("No games scheduled for today.")

if __name__ == "__main__":
    main()
