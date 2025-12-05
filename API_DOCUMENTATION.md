# NBA Game Predictor API Documentation

**Base URL:** `http://localhost:8000`

**Version:** 1.0.0

**Description:** Predict NBA game outcomes using machine learning. This API fetches live game data from the BallDontLie API and uses a trained logistic regression model to predict win probabilities.

---

## Table of Contents

1. [Authentication](#authentication)
2. [Endpoints](#endpoints)
   - [GET /](#get-)
   - [GET /games](#get-games)
   - [GET /games/today](#get-gamestoday)
   - [GET /games/{game_id}](#get-gamesgame_id)
   - [POST /predict/{game_id}](#post-predictgame_id)
   - [GET /predict/teams/{home_team}/{away_team}](#get-predictteamshome_teamaway_team)
   - [GET /results](#get-results)
   - [GET /teams](#get-teams)
3. [Response Models](#response-models)
4. [Error Handling](#error-handling)
5. [Examples](#examples)

---

## Authentication

This API does not require authentication for consumers. However, the server requires a `BALL_API_KEY` environment variable to fetch live NBA data from BallDontLie.

```bash
export BALL_API_KEY="your_balldontlie_api_key"
```

---

## Endpoints

### GET /

Returns API information and available endpoints.

**Request:**

```http
GET / HTTP/1.1
Host: localhost:8000
```

**Response:**

```json
{
  "message": "NBA Game Predictor API",
  "api_key_configured": true,
  "endpoints": {
    "/games": "List upcoming games (from BallDontLie API)",
    "/games/today": "Get today's games",
    "/games/{id}": "Get game details",
    "/predict/{id}": "Predict game outcome",
    "/predict/teams/{home}/{away}": "Predict any matchup",
    "/results": "View prediction accuracy",
    "/teams": "List available teams"
  }
}
```

---

### GET /games

Fetch upcoming NBA games for the next N days.

**Request:**

```http
GET /games?days=7 HTTP/1.1
Host: localhost:8000
```

**Query Parameters:**

| Parameter | Type    | Required | Default | Description                         |
| --------- | ------- | -------- | ------- | ----------------------------------- |
| `days`    | integer | No       | 7       | Number of days ahead to fetch games |

**Response (200 OK):**

```json
{
  "source": "balldontlie_api",
  "count": 15,
  "games": [
    {
      "id": 1234567,
      "home_team": "LAL",
      "home_team_name": "Los Angeles Lakers",
      "away_team": "GSW",
      "away_team_name": "Golden State Warriors",
      "game_date": "2025-12-05",
      "status": "scheduled",
      "home_score": null,
      "away_score": null,
      "season": 2025
    },
    {
      "id": 1234568,
      "home_team": "BOS",
      "home_team_name": "Boston Celtics",
      "away_team": "MIA",
      "away_team_name": "Miami Heat",
      "game_date": "2025-12-05",
      "status": "scheduled",
      "home_score": null,
      "away_score": null,
      "season": 2025
    }
  ]
}
```

**Response Fields:**

| Field                    | Type         | Description                                                |
| ------------------------ | ------------ | ---------------------------------------------------------- |
| `source`                 | string       | Data source: `"balldontlie_api"`, `"cache"`, or `"static"` |
| `count`                  | integer      | Number of games returned                                   |
| `games`                  | array        | List of game objects                                       |
| `games[].id`             | integer      | Unique game identifier                                     |
| `games[].home_team`      | string       | Home team abbreviation (e.g., "LAL")                       |
| `games[].home_team_name` | string       | Home team full name                                        |
| `games[].away_team`      | string       | Away team abbreviation                                     |
| `games[].away_team_name` | string       | Away team full name                                        |
| `games[].game_date`      | string       | Game date (YYYY-MM-DD)                                     |
| `games[].status`         | string       | Game status                                                |
| `games[].home_score`     | integer/null | Home team score (null if not started)                      |
| `games[].away_score`     | integer/null | Away team score (null if not started)                      |
| `games[].season`         | integer      | NBA season year                                            |

---

### GET /games/today

Fetch today's NBA games.

**Request:**

```http
GET /games/today HTTP/1.1
Host: localhost:8000
```

**Response (200 OK):**

```json
{
  "count": 5,
  "games": [
    {
      "id": 1234567,
      "home_team": "LAL",
      "home_team_name": "Los Angeles Lakers",
      "away_team": "GSW",
      "away_team_name": "Golden State Warriors",
      "game_date": "2025-12-04",
      "status": "in_progress",
      "home_score": 54,
      "away_score": 48,
      "season": 2025
    }
  ]
}
```

---

### GET /games/{game_id}

Get details for a specific game.

**Request:**

```http
GET /games/1234567 HTTP/1.1
Host: localhost:8000
```

**Path Parameters:**

| Parameter | Type    | Required | Description            |
| --------- | ------- | -------- | ---------------------- |
| `game_id` | integer | Yes      | Unique game identifier |

**Response (200 OK):**

```json
{
  "id": 1234567,
  "home_team": "LAL",
  "home_team_name": "Los Angeles Lakers",
  "away_team": "GSW",
  "away_team_name": "Golden State Warriors",
  "game_date": "2025-12-05",
  "status": "scheduled",
  "home_score": null,
  "away_score": null,
  "season": 2025
}
```

**Response (404 Not Found):**

```json
{
  "detail": "Game not found"
}
```

---

### POST /predict/{game_id}

Predict the outcome of a specific game.

**Request:**

```http
POST /predict/1234567 HTTP/1.1
Host: localhost:8000
Content-Type: application/json
```

**Path Parameters:**

| Parameter | Type    | Required | Description                    |
| --------- | ------- | -------- | ------------------------------ |
| `game_id` | integer | Yes      | Game ID from `/games` endpoint |

**Request Body:** None required

**Response (200 OK):**

```json
{
  "game_id": 1234567,
  "home_team": "LAL",
  "away_team": "GSW",
  "home_win_probability": 0.623,
  "away_win_probability": 0.377,
  "predicted_winner": "LAL",
  "confidence": "Medium"
}
```

**Response Fields:**

| Field                  | Type    | Description                                                            |
| ---------------------- | ------- | ---------------------------------------------------------------------- |
| `game_id`              | integer | Game identifier                                                        |
| `home_team`            | string  | Home team abbreviation                                                 |
| `away_team`            | string  | Away team abbreviation                                                 |
| `home_win_probability` | float   | Probability home team wins (0.0 - 1.0)                                 |
| `away_win_probability` | float   | Probability away team wins (0.0 - 1.0)                                 |
| `predicted_winner`     | string  | Team abbreviation of predicted winner                                  |
| `confidence`           | string  | Confidence level: `"High"` (≥70%), `"Medium"` (55-70%), `"Low"` (<55%) |

**Response (404 Not Found):**

```json
{
  "detail": "Game not found"
}
```

**Response (400 Bad Request):**

```json
{
  "detail": "Missing stats for teams: LAL or GSW"
}
```

**Response (500 Internal Server Error):**

```json
{
  "detail": "Model not loaded. Run notebook first."
}
```

---

### GET /predict/teams/{home_team}/{away_team}

Predict the outcome for any two teams (not limited to scheduled games).

**Request:**

```http
GET /predict/teams/LAL/BOS HTTP/1.1
Host: localhost:8000
```

**Path Parameters:**

| Parameter   | Type   | Required | Description                               |
| ----------- | ------ | -------- | ----------------------------------------- |
| `home_team` | string | Yes      | Home team abbreviation (case-insensitive) |
| `away_team` | string | Yes      | Away team abbreviation (case-insensitive) |

**Response (200 OK):**

```json
{
  "game_id": 0,
  "home_team": "LAL",
  "away_team": "BOS",
  "home_win_probability": 0.487,
  "away_win_probability": 0.513,
  "predicted_winner": "BOS",
  "confidence": "Low"
}
```

**Valid Team Abbreviations:**

| Abbreviation | Team Name              |
| ------------ | ---------------------- |
| ATL          | Atlanta Hawks          |
| BOS          | Boston Celtics         |
| BKN          | Brooklyn Nets          |
| CHA          | Charlotte Hornets      |
| CHI          | Chicago Bulls          |
| CLE          | Cleveland Cavaliers    |
| DAL          | Dallas Mavericks       |
| DEN          | Denver Nuggets         |
| DET          | Detroit Pistons        |
| GSW          | Golden State Warriors  |
| HOU          | Houston Rockets        |
| IND          | Indiana Pacers         |
| LAC          | Los Angeles Clippers   |
| LAL          | Los Angeles Lakers     |
| MEM          | Memphis Grizzlies      |
| MIA          | Miami Heat             |
| MIL          | Milwaukee Bucks        |
| MIN          | Minnesota Timberwolves |
| NOP          | New Orleans Pelicans   |
| NYK          | New York Knicks        |
| OKC          | Oklahoma City Thunder  |
| ORL          | Orlando Magic          |
| PHI          | Philadelphia 76ers     |
| PHX          | Phoenix Suns           |
| POR          | Portland Trail Blazers |
| SAC          | Sacramento Kings       |
| SAS          | San Antonio Spurs      |
| TOR          | Toronto Raptors        |
| UTA          | Utah Jazz              |
| WAS          | Washington Wizards     |

---

### GET /results

View historical prediction accuracy.

**Request:**

```http
GET /results HTTP/1.1
Host: localhost:8000
```

**Response (200 OK):**

```json
{
  "accuracy": 0.85,
  "total_predictions": 42,
  "records": [
    {
      "game": "LAL vs GSW",
      "predicted": 0.72,
      "actual": 1,
      "correct": true
    },
    {
      "game": "BOS vs MIA",
      "predicted": 0.65,
      "actual": 1,
      "correct": true
    },
    {
      "game": "PHX vs DEN",
      "predicted": 0.48,
      "actual": 0,
      "correct": true
    }
  ]
}
```

**Response Fields:**

| Field                 | Type    | Description                                 |
| --------------------- | ------- | ------------------------------------------- |
| `accuracy`            | float   | Overall prediction accuracy (0.0 - 1.0)     |
| `total_predictions`   | integer | Total number of predictions made            |
| `records`             | array   | List of past predictions                    |
| `records[].game`      | string  | Game matchup description                    |
| `records[].predicted` | float   | Predicted home win probability              |
| `records[].actual`    | integer | Actual outcome (1 = home win, 0 = away win) |
| `records[].correct`   | boolean | Whether prediction was correct              |

---

### GET /teams

List all NBA teams available for prediction.

**Request:**

```http
GET /teams HTTP/1.1
Host: localhost:8000
```

**Response (200 OK) - From API:**

```json
{
  "source": "balldontlie_api",
  "count": 30,
  "teams": [
    {
      "id": 1,
      "abbreviation": "ATL",
      "city": "Atlanta",
      "name": "Hawks",
      "full_name": "Atlanta Hawks",
      "conference": "East",
      "division": "Southeast"
    },
    {
      "id": 2,
      "abbreviation": "BOS",
      "city": "Boston",
      "name": "Celtics",
      "full_name": "Boston Celtics",
      "conference": "East",
      "division": "Atlantic"
    }
  ]
}
```

**Response (200 OK) - From Model (fallback):**

```json
{
  "source": "model",
  "count": 30,
  "teams": ["ATL", "BOS", "BKN", "CHA", "CHI", "..."]
}
```

---

## Response Models

### PredictionResponse

```json
{
  "game_id": "integer",
  "home_team": "string",
  "away_team": "string",
  "home_win_probability": "float (0.0 - 1.0)",
  "away_win_probability": "float (0.0 - 1.0)",
  "predicted_winner": "string",
  "confidence": "string (High | Medium | Low)"
}
```

### GameResponse

```json
{
  "id": "integer",
  "home_team": "string",
  "away_team": "string",
  "game_date": "string (YYYY-MM-DD)",
  "status": "string"
}
```

### ResultsResponse

```json
{
  "accuracy": "float (0.0 - 1.0)",
  "total_predictions": "integer",
  "records": "array"
}
```

---

## Error Handling

All errors follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

| Code | Description                                              |
| ---- | -------------------------------------------------------- |
| 200  | Success                                                  |
| 400  | Bad Request - Invalid parameters or missing team data    |
| 404  | Not Found - Game or resource not found                   |
| 500  | Internal Server Error - Model not loaded or server error |

---

## Examples

### cURL Examples

**Get upcoming games:**

```bash
curl -X GET "http://localhost:8000/games?days=7"
```

**Get today's games:**

```bash
curl -X GET "http://localhost:8000/games/today"
```

**Predict a specific game:**

```bash
curl -X POST "http://localhost:8000/predict/1234567"
```

**Predict any matchup:**

```bash
curl -X GET "http://localhost:8000/predict/teams/LAL/BOS"
```

**List all teams:**

```bash
curl -X GET "http://localhost:8000/teams"
```

### Python Examples

```python
import requests

BASE_URL = "http://localhost:8000"

# Get upcoming games
response = requests.get(f"{BASE_URL}/games", params={"days": 7})
games = response.json()
print(f"Found {games['count']} upcoming games")

# Predict a matchup
response = requests.get(f"{BASE_URL}/predict/teams/LAL/GSW")
prediction = response.json()
print(f"Predicted winner: {prediction['predicted_winner']}")
print(f"Confidence: {prediction['confidence']}")
print(f"Home win probability: {prediction['home_win_probability']:.1%}")
```

### JavaScript/React Native Examples

```javascript
const BASE_URL = "http://localhost:8000";

// Fetch upcoming games
async function getGames() {
  const response = await fetch(`${BASE_URL}/games?days=7`);
  const data = await response.json();
  return data.games;
}

// Predict game outcome
async function predictGame(gameId) {
  const response = await fetch(`${BASE_URL}/predict/${gameId}`, {
    method: "POST",
  });
  return response.json();
}

// Predict any matchup
async function predictMatchup(homeTeam, awayTeam) {
  const response = await fetch(
    `${BASE_URL}/predict/teams/${homeTeam}/${awayTeam}`
  );
  return response.json();
}

// Usage
const prediction = await predictMatchup("LAL", "BOS");
console.log(
  `Winner: ${prediction.predicted_winner} (${prediction.confidence})`
);
```

---

## Interactive Documentation

When the server is running, visit:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

These provide interactive API documentation where you can test endpoints directly in your browser.

---

## Rate Limits

The BallDontLie API has rate limits. If you exceed them, the server will fall back to cached or static data. Consider implementing caching on the client side for production use.

---

## Model Information

The prediction model is a **Logistic Regression** classifier trained on historical NBA game data with the following features:

- Points (home/away)
- Field goals made/attempted
- 3-point field goals made/attempted
- Free throws made/attempted
- Rebounds (offensive/defensive/total)
- Assists, steals, blocks, turnovers, personal fouls
- Paint points, 2nd chance points, fastbreak points
- Team turnovers, team rebounds

The model predicts `P(home_win)` and outputs probabilities between 0 and 1.
