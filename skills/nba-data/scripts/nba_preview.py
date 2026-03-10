#!/usr/bin/env python3
"""
NBA Game Preview - Analyze upcoming matchups
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
        return {}

def get_team_record(team_name):
    """Get team record from recent games"""
    games = fetch_json(f"{BASE_URL}/scoreboard").get('events', [])
    
    wins = 0
    losses = 0
    last_5 = []
    
    for event in games:
        status = event.get('status', {}).get('type', {}).get('description', '')
        if status != 'Final':
            continue
        
        competitions = event.get('competitions', [])
        if not competitions:
            continue
        
        comp = competitions[0]
        competitors = comp.get('competitors', [])
        if len(competitors) != 2:
            continue
        
        home = competitors[0] if competitors[0].get('homeAway') == 'home' else competitors[1]
        away = competitors[1] if competitors[0].get('homeAway') == 'home' else competitors[0]
        
        home_team = home.get('team', {}).get('displayName', '')
        away_team = away.get('team', {}).get('displayName', '')
        home_score = int(home.get('score', 0) or 0)
        away_score = int(away.get('score', 0) or 0)
        
        if team_name in home_team or team_name in away_team:
            is_home = team_name in home_team
            team_score = home_score if is_home else away_score
            opp_score = away_score if is_home else home_score
            opponent = away_team if is_home else home_team
            
            if team_score > opp_score:
                wins += 1
                result = "W"
            else:
                losses += 1
                result = "L"
            
            last_5.append(f"{result} vs {opponent.split()[-1]} ({team_score}-{opp_score})")
            
            if len(last_5) >= 5:
                break
    
    return wins, losses, last_5[:5]

def preview_today_games():
    """Preview all games for today"""
    url = f"{BASE_URL}/scoreboard"
    data = fetch_json(url)
    events = data.get('events', [])
    
    if not events:
        print("No games scheduled for today.")
        return
    
    date = datetime.now().strftime("%Y-%m-%d")
    print(f"NBA Game Previews - {date}")
    print("="*70)
    
    for event in events:
        status = event.get('status', {}).get('type', {}).get('description', '')
        if status == 'Final':
            continue
        
        competitions = event.get('competitions', [])
        if not competitions:
            continue
        
        comp = competitions[0]
        competitors = comp.get('competitors', [])
        if len(competitors) != 2:
            continue
        
        home = competitors[0] if competitors[0].get('homeAway') == 'home' else competitors[1]
        away = competitors[1] if competitors[0].get('homeAway') == 'home' else competitors[0]
        
        home_team = home.get('team', {}).get('displayName', '')
        away_team = away.get('team', {}).get('displayName', '')
        time = event.get('status', {}).get('type', {}).get('shortDetail', 'TBD')
        
        print(f"\n{away_team} @ {home_team}")
        print("-"*70)
        print(f"Tip-off: {time}")
        
        # Get records
        home_wins, home_losses, home_last5 = get_team_record(home_team)
        away_wins, away_losses, away_last5 = get_team_record(away_team)
        
        total_home = home_wins + home_losses
        total_away = away_wins + away_losses
        
        if total_home > 0:
            home_pct = home_wins / total_home
            print(f"\n{home_team}: {home_wins}-{home_losses} ({home_pct:.3f})")
            print(f"  Last 5: {', '.join(home_last5) if home_last5 else 'No recent games'}")
        
        if total_away > 0:
            away_pct = away_wins / away_losses if away_losses > 0 else 1.0
            print(f"\n{away_team}: {away_wins}-{away_losses} ({away_pct:.3f})")
            print(f"  Last 5: {', '.join(away_last5) if away_last5 else 'No recent games'}")
        
        # Venue info
        venue = comp.get('venue', {}).get('fullName', 'TBD')
        print(f"\nVenue: {venue}")
        
        # Broadcast info
        broadcasts = comp.get('broadcasts', [])
        if broadcasts:
            networks = [b.get('names', ['Unknown'])[0] for b in broadcasts]
            print(f"Broadcast: {', '.join(networks)}")
        
        print()

def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'today':
        preview_today_games()
    else:
        print("Usage: nba_preview.py today")
        sys.exit(1)

if __name__ == "__main__":
    main()
