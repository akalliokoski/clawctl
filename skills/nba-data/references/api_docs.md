# NBA API Reference

This skill uses the **ESPN Public API** - a free, no-key-required API for NBA data.

## API Base URL
```
https://site.api.espn.com/apis/site/v2/sports/basketball/nba
```

## Endpoints

### Teams

**Get All Teams**
```
GET /teams
```

Response includes:
- `id` - Team ID
- `displayName` - Full team name (e.g., "Los Angeles Lakers")
- `name` - Short name (e.g., "Lakers")
- `location` - City name
- `abbreviation` - 3-letter code (e.g., "LAL")
- `venue` - Home arena info
- `logos` - Team logo URLs

### Scoreboard (Games)

**Get Today's Games**
```
GET /scoreboard
```

Query parameters:
- `dates` - Specific date (YYYYMMDD format)
- `limit` - Number of games to return

Response includes:
- `events` - Array of games
  - `name` - Game name (e.g., "Lakers at Warriors")
  - `date` - Game date/time
  - `status` - Game status (Scheduled, In Progress, Final)
  - `competitions` - Game details including:
    - `competitors` - Home and away teams
    - `team` - Team details
    - `score` - Current/final score
    - `homeAway` - "home" or "away"

### News

**Get Latest News**
```
GET /news
```

Response includes:
- `articles` - Array of news articles
  - `headline` - Article title
  - `description` - Article summary
  - `published` - Publication date
  - `links` - Article URLs
  - `byline` - Author

### Team Details

**Get Team Info**
```
GET /teams/{team_id}
```

## Response Format

ESPN uses a nested structure:
```json
{
  "sports": [{
    "leagues": [{
      "teams": [{
        "team": { ... }
      }]
    }]
  }]
}
```

## Error Handling

Common HTTP status codes:
- `200` - Success
- `404` - Resource not found
- `429` - Rate limit (slow down requests)

## ESPN Website

For reference:
- https://www.espn.com/nba/
- https://www.espn.com/nba/standings
- https://www.espn.com/nba/schedule
