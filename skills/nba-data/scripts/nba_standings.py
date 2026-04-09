#!/usr/bin/env python3
"""
NBA Standings - Fetch current conference standings
Uses ESPN public API (free, no key required)
Calculates standings from game results
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

def get_teams():
    """Get all teams with their conference info"""
    url = f"{BASE_URL}/teams"
    data = fetch_json(url)
    
    sports = data.get('sports', [])
    if not sports:
        return {}
    
    leagues = sports[0].get('leagues', [])
    if not leagues:
        return {}
    
    teams_data = leagues[0].get('teams', [])
    teams = {}
    
    # East teams by abbreviation
    east_abbr = ['ATL', 'BOS', 'BKN', 'CHA', 'CHI', 'CLE', 'DET', 'IND', 'MIA', 'MIL', 'NYK', 'ORL', 'PHI', 'TOR', 'WAS']
    
    for team_data in teams_data:
        team = team_data.get('team', {})
        team_id = team.get('id')
        abbr = team.get('abbreviation', '')
        if team_id:
            teams[team_id] = {
                'id': team_id,
                'name': team.get('displayName', ''),
                'abbr': abbr,
                'conference': 'East' if abbr in east_abbr else 'West',
                'wins': 0,
                'losses': 0
            }
    
    return teams

def fetch_recent_games(days=30):
    """Fetch recent completed games"""
    url = f"{BASE_URL}/scoreboard"
    data = fetch_json(url)
    return data.get('events', [])

def calculate_standings():
    """Calculate standings from game results"""
    teams = get_teams()
    games = fetch_recent_games()
    
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
        
        home_id = home.get('team', {}).get('id')
        away_id = away.get('team', {}).get('id')
        home_score = int(home.get('score', 0) or 0)
        away_score = int(away.get('score', 0) or 0)
        
        if home_id in teams and away_id in teams:
            if home_score > away_score:
                teams[home_id]['wins'] += 1
                teams[away_id]['losses'] += 1
            else:
                teams[away_id]['wins'] += 1
                teams[home_id]['losses'] += 1
    
    return teams

def display_standings():
    """Display conference standings"""
    teams = calculate_standings()
    
    if not teams:
        print("No standings data available.")
        return
    
    # Split by conference
    east = [t for t in teams.values() if t['conference'] == 'East']
    west = [t for t in teams.values() if t['conference'] == 'West']
    
    # Sort by wins (descending)
    east.sort(key=lambda x: x['wins'], reverse=True)
    west.sort(key=lambda x: x['wins'], reverse=True)
    
    print(f"NBA Standings {datetime.now().year}-{datetime.now().year+1}")
    print("="*70)
    
    print("\nEastern Conference")
    print("-"*70)
    print(f"{'Rank':<6}{'Team':<28}{'W':<6}{'L':<6}{'PCT':<8}{'GB':<6}")
    print("-"*70)
    
    first_wins = east[0]['wins'] if east else 0
    first_losses = east[0]['losses'] if east else 0
    
    for i, team in enumerate(east, 1):
        wins = team['wins']
        losses = team['losses']
        total = wins + losses
        pct = wins / total if total > 0 else 0.0
        
        # Calculate games back
        gb = (first_wins - wins + losses - first_losses) / 2
        gb_str = f"{gb:.1f}" if gb > 0 else "-"
        
        name = team['name'][:27]
        print(f"{i:<6}{name:<28}{wins:<6}{losses:<6}{pct:.3f}  {gb_str:<6}")
    
    print("\nWestern Conference")
    print("-"*70)
    print(f"{'Rank':<6}{'Team':<28}{'W':<6}{'L':<6}{'PCT':<8}{'GB':<6}")
    print("-"*70)
    
    first_wins = west[0]['wins'] if west else 0
    first_losses = west[0]['losses'] if west else 0
    
    for i, team in enumerate(west, 1):
        wins = team['wins']
        losses = team['losses']
        total = wins + losses
        pct = wins / total if total > 0 else 0.0
        
        # Calculate games back
        gb = (first_wins - wins + losses - first_losses) / 2
        gb_str = f"{gb:.1f}" if gb > 0 else "-"
        
        name = team['name'][:27]
        print(f"{i:<6}{name:<28}{wins:<6}{losses:<6}{pct:.3f}  {gb_str:<6}")

def main():
    display_standings()

if __name__ == "__main__":
    main()
