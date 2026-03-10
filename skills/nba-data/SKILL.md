---
name: nba-data
description: Get NBA scores, standings, team information, schedules, news, game previews, and post-game analysis. Use when the user asks about NBA basketball, including live scores, game results, team records, schedules, headlines, game previews, or detailed game reviews.
---

# NBA Data Skill

Fetch live NBA scores, standings, team information, schedules, news, game previews, and post-game analysis using the free ESPN public API.

## Quick Start

### Get Today's Games
```python
python3 scripts/nba_games.py today
```

### Get Team Info
```python
python3 scripts/nba_teams.py info "Lakers"
```

### Get Standings
```python
python3 scripts/nba_standings.py
```

### Get News Headlines
```python
python3 scripts/nba_news.py 5
```

### Game Preview (Upcoming Games)
```python
python3 scripts/nba_preview.py today
```

### Game Review (Post-Game Analysis)
```python
python3 scripts/nba_review.py recent
python3 scripts/nba_review.py list
python3 scripts/nba_review.py game <event_id>
```

## Available Commands

### Games & Schedule
| Command | Description | Example |
|---------|-------------|---------|
| `nba_games.py today` | Today's games with scores | `nba_games.py today` |
| `nba_teams.py schedule` | Upcoming games schedule | `nba_teams.py schedule` |

### Teams & Standings
| Command | Description | Example |
|---------|-------------|---------|
| `nba_teams.py list` | List all NBA teams by conference | `nba_teams.py list` |
| `nba_teams.py info <name>` | Team details | `nba_teams.py info "Lakers"` |
| `nba_standings.py` | Conference standings | `nba_standings.py` |

### News & Analysis
| Command | Description | Example |
|---------|-------------|---------|
| `nba_news.py [count]` | Latest news headlines | `nba_news.py 5` |
| `nba_preview.py today` | Preview upcoming games | `nba_preview.py today` |
| `nba_review.py recent` | Analyze most recent game | `nba_review.py recent` |
| `nba_review.py list` | List recent games with IDs | `nba_review.py list` |
| `nba_review.py game <id>` | Analyze specific game | `nba_review.py game 401810731` |
| `nba_alerts.py` | Check for key matchups today | `nba_alerts.py` |

## Alerts System

The alerts script (`nba_alerts.py`) automatically identifies:
- **Rivalry games** (Lakers-Celtics, Warriors-Rockets, etc.)
- **Playoff contender matchups** (top teams facing each other)
- **High-stakes games** with playoff implications

Tags games as:
- `Rivalry Game` - Historic rivalries
- `Playoff Contenders` - Both teams are playoff bound

## Game Review Features

The game review (`nba_review.py`) provides:
- Final score and game status
- Quarter-by-quarter scoring breakdown
- Key team statistics comparison
- Top performers from each team
- Notable moments and scoring plays

## Game Preview Features

The game preview (`nba_preview.py`) provides:
- Matchup details (teams, tip-off time)
- Recent records for each team
- Last 5 games results with scores
- Venue and broadcast information

## Data Source

- **API**: ESPN Public API (site.api.espn.com)
- **Cost**: FREE, no API key required
- **Rate Limits**: Be respectful, cache when possible
- **Data**: Live scores, schedules, team info, standings, news, boxscores

## Limitations

- Standings calculated from recent games shown on scoreboard
- Some detailed player stats require authenticated endpoints
- Game previews limited to data available in ESPN's public API
