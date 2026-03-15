#!/usr/bin/env python3
"""
NBA Teams - Fetch team information and schedules
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

def get_teams(data):
    """Extract team list from API response"""
    sports = data.get('sports', [])
    if not sports:
        return []
    leagues = sports[0].get('leagues', [])
    if not leagues:
        return []
    teams_data = leagues[0].get('teams', [])
    return [t.get('team', {}) for t in teams_data]

def list_teams():
    """List all NBA teams"""
    url = f"{BASE_URL}/teams"
    data = fetch_json(url)
    teams = get_teams(data)
    
    if not teams:
        print("No team data available.")
        return
    
    print("NBA Teams\n" + "="*40)
    
    # Group by conference using team IDs (approximation)
    # East: ATL, BOS, BKN, CHA, CHI, CLE, DET, IND, MIA, MIL, NYK, ORL, PHI, TOR, WAS
    east_abbr = ['ATL', 'BOS', 'BKN', 'CHA', 'CHI', 'CLE', 'DET', 'IND', 'MIA', 'MIL', 'NYK', 'ORL', 'PHI', 'TOR', 'WAS']
    
    east = []
    west = []
    
    for team in teams:
        abbr = team.get('abbreviation', '')
        name = team.get('displayName', '')
        if abbr in east_abbr:
            east.append(name)
        else:
            west.append(name)
    
    print("\nEastern Conference:")
    for name in sorted(east):
        print(f"  {name}")
    
    print("\nWestern Conference:")
    for name in sorted(west):
        print(f"  {name}")

def show_team_info(name):
    """Show team details"""
    url = f"{BASE_URL}/teams"
    data = fetch_json(url)
    teams = get_teams(data)
    
    if not teams:
        print("No team data available.")
        return
    
    name_lower = name.lower()
    matches = []
    
    for team in teams:
        full_name = team.get('displayName', '').lower()
        short_name = team.get('name', '').lower()
        if name_lower in full_name or name_lower in short_name:
            matches.append(team)
    
    if not matches:
        print(f"No team found matching '{name}'")
        return
    
    if len(matches) > 1:
        print(f"Multiple matches found for '{name}':")
        for team in matches:
            print(f"  - {team['displayName']}")
        return
    
    team = matches[0]
    print(f"\n{team['displayName']}")
    print("="*40)
    print(f"Abbreviation: {team.get('abbreviation', 'N/A')}")
    print(f"Location: {team.get('location', 'N/A')}")
    print(f"Venue: {team.get('venue', {}).get('fullName', 'N/A')}")

def show_schedule():
    """Fetch upcoming games"""
    url = f"{BASE_URL}/scoreboard"
    data = fetch_json(url)
    
    events = data.get('events', [])
    if not events:
        print("No upcoming games found.")
        return
    
    print(f"\nUpcoming NBA Games")
    print("="*60)
    
    for event in events[:10]:
        date = event.get('date', '').split('T')[0]
        status = event.get('status', {}).get('type', {}).get('description', 'Unknown')
        
        competitions = event.get('competitions', [])
        if competitions:
            comp = competitions[0]
            competitors = comp.get('competitors', [])
            if len(competitors) == 2:
                home = competitors[0] if competitors[0].get('homeAway') == 'home' else competitors[1]
                away = competitors[1] if competitors[0].get('homeAway') == 'home' else competitors[0]
                
                home_team = home.get('team', {}).get('displayName', 'Unknown')
                away_team = away.get('team', {}).get('displayName', 'Unknown')
                home_score = home.get('score', '-')
                away_score = away.get('score', '-')
                
                if status == 'Final':
                    print(f"{date}: {away_team} {away_score} @ {home_team} {home_score} (FINAL)")
                else:
                    time = event.get('status', {}).get('type', {}).get('shortDetail', 'TBD')
                    print(f"{date}: {away_team} @ {home_team} ({time})")

def main():
    if len(sys.argv) < 2:
        print("Usage: nba_teams.py <list|info <name>|schedule>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        list_teams()
    elif command == "info" and len(sys.argv) >= 3:
        show_team_info(sys.argv[2])
    elif command == "schedule":
        show_schedule()
    else:
        print("Usage: nba_teams.py <list|info <name>|schedule>")
        sys.exit(1)

if __name__ == "__main__":
    main()
