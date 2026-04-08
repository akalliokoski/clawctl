#!/usr/bin/env python3
"""
NBA Game Review - Post-game analysis
Uses ESPN public API (free, no key required)
"""

import sys
import json
import urllib.request
from datetime import datetime

BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
SUMMARY_URL = "https://site.web.api.espn.com/apis/site/v2/sports/basketball/nba/summary"

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

def get_recent_finished_games(limit=5):
    """Get recently completed games"""
    url = f"{BASE_URL}/scoreboard"
    data = fetch_json(url)
    events = data.get('events', [])
    
    finished = []
    for event in events:
        status = event.get('status', {}).get('type', {}).get('description', '')
        if status == 'Final':
            finished.append(event)
            if len(finished) >= limit:
                break
    
    return finished

def format_time(seconds):
    """Format seconds into MM:SS"""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"

def analyze_game(event_id):
    """Get detailed game analysis"""
    url = f"{SUMMARY_URL}?event={event_id}"
    data = fetch_json(url)
    
    if not data:
        print("Could not fetch game details.")
        return
    
    header = data.get('header', {})
    boxscore = data.get('boxscore', {})
    plays = data.get('plays', [])
    
    # Get team info
    competitions = header.get('competitions', [])
    if not competitions:
        print("No game data available.")
        return
    
    comp = competitions[0]
    competitors = comp.get('competitors', [])
    if len(competitors) != 2:
        print("Incomplete game data.")
        return
    
    home = competitors[0] if competitors[0].get('homeAway') == 'home' else competitors[1]
    away = competitors[1] if competitors[0].get('homeAway') == 'home' else competitors[0]
    
    home_team = home.get('team', {}).get('displayName', 'Home')
    away_team = away.get('team', {}).get('displayName', 'Away')
    home_score = home.get('score', '-')
    away_score = away.get('score', '-')
    
    # Get game status
    status = header.get('competitions', [{}])[0].get('status', {}).get('type', {})
    game_status = status.get('description', '')
    
    print(f"\n{away_team} @ {home_team}")
    print("="*70)
    print(f"Final Score: {away_team} {away_score} - {home_team} {home_score}")
    print(f"Status: {game_status}")
    
    # Line scores (quarter by quarter)
    line_scores = boxscore.get('teams', [])
    if line_scores and len(line_scores) == 2:
        print("\nQuarter-by-Quarter Breakdown:")
        print("-"*70)
        
        away_ls = line_scores[0] if line_scores[0].get('team', {}).get('displayName') == away_team else line_scores[1]
        home_ls = line_scores[1] if line_scores[0].get('team', {}).get('displayName') == away_team else line_scores[0]
        
        away_lines = away_ls.get('linescores', [])
        home_lines = home_ls.get('linescores', [])
        
        quarters = ['Q1', 'Q2', 'Q3', 'Q4', 'OT']
        print(f"{'':<20}", end='')
        for i in range(len(away_lines)):
            q = quarters[i] if i < 4 else f"OT{i-3}" if i == 4 else f"OT{i-3}"
            print(f"{q:>8}", end='')
        print(f"{'Total':>10}")
        
        print(f"{away_team[:18]:<20}", end='')
        for ls in away_lines:
            print(f"{ls.get('displayValue', '-'):>8}", end='')
        print(f"{away_score:>10}")
        
        print(f"{home_team[:18]:<20}", end='')
        for ls in home_lines:
            print(f"{ls.get('displayValue', '-'):>8}", end='')
        print(f"{home_score:>10}")
    
    # Key statistics
    statistics = boxscore.get('statistics', [])
    if statistics:
        print("\nKey Stats:")
        print("-"*70)
        
        for stat_group in statistics:
            labels = stat_group.get('labels', [])
            away_stats = stat_group.get('away', [])
            home_stats = stat_group.get('home', [])
            
            if labels and away_stats and home_stats:
                print(f"\n{stat_group.get('name', 'Category')}:")
                for label, away_val, home_val in zip(labels, away_stats, home_stats):
                    print(f"  {label}: {away_team.split()[-1]} {away_val} | {home_team.split()[-1]} {home_val}")
            break  # Just show first stat group for brevity
    
    # Top performers
    players = boxscore.get('players', [])
    if players:
        print("\nTop Performers:")
        print("-"*70)
        
        for team_players in players[:2]:  # Both teams
            team_name = team_players.get('team', {}).get('displayName', '')
            print(f"\n{team_name}:")
            
            stats = team_players.get('statistics', [])
            for stat in stats[:1]:  # First stat category (usually points)
                athletes = stat.get('athletes', [])
                leaders = athletes[:3] if len(athletes) >= 3 else athletes
                
                for leader in leaders:
                    athlete = leader.get('athlete', {})
                    name = f"{athlete.get('firstName', '')} {athlete.get('lastName', '')}"
                    display = leader.get('displayValue', '')
                    print(f"  {name}: {display}")
    
    # Notable plays
    if plays:
        print("\nNotable Moments:")
        print("-"*70)
        
        scoring_plays = [p for p in plays if any(x in p.get('type', {}).get('text', '').lower() for x in ['made', 'field goal', 'three point', 'free throw'])][:5]
        
        for play in scoring_plays:
            period = play.get('period', {}).get('number', 0)
            clock = play.get('clock', {}).get('displayValue', '')
            text = play.get('text', '')
            away_score = play.get('awayScore', 0)
            home_score = play.get('homeScore', 0)
            
            q = ['Q1', 'Q2', 'Q3', 'Q4', 'OT'][period-1] if period <= 5 else f"OT{period-4}"
            print(f"  {q} {clock}: {text} ({away_score}-{home_score})")

def list_recent_games():
    """List recent finished games for selection"""
    games = get_recent_finished_games(10)
    
    if not games:
        print("No recent finished games found.")
        return []
    
    print("Recent Games:")
    print("-"*70)
    
    game_list = []
    for i, event in enumerate(games, 1):
        competitions = event.get('competitions', [])
        if not competitions:
            continue
        
        comp = competitions[0]
        competitors = comp.get('competitors', [])
        if len(competitors) != 2:
            continue
        
        home = competitors[0] if competitors[0].get('homeAway') == 'home' else competitors[1]
        away = competitors[1] if competitors[0].get('homeAway') == 'home' else competitors[0]
        
        home_team = home.get('team', {}).get('displayName', 'Home')
        away_team = away.get('team', {}).get('displayName', 'Away')
        home_score = home.get('score', '-')
        away_score = away.get('score', '-')
        event_id = event.get('id', '')
        
        print(f"{i}. {away_team} {away_score} @ {home_team} {home_score}")
        game_list.append((i, event_id, f"{away_team} @ {home_team}"))
    
    return game_list

def main():
    if len(sys.argv) < 2:
        print("Usage: nba_review.py <recent|game <event_id>|list>")
        print("\n  recent       - Analyze most recent finished game")
        print("  game <id>    - Analyze specific game by event ID")
        print("  list         - List recent games with IDs")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "recent":
        games = get_recent_finished_games(1)
        if games:
            analyze_game(games[0].get('id'))
        else:
            print("No recent finished games found.")
    
    elif command == "game" and len(sys.argv) >= 3:
        event_id = sys.argv[2]
        analyze_game(event_id)
    
    elif command == "list":
        list_recent_games()
    
    else:
        print("Usage: nba_review.py <recent|game <event_id>|list>")
        sys.exit(1)

if __name__ == "__main__":
    main()
