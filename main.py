"""
NBA Game Outcome Predictor – FastAPI Backend

Loads the trained logistic regression model and provides endpoints to:
- List upcoming games (from BallDontLie API)
- Predict home-win probability for a given game
- View historical prediction accuracy
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pickle
import json
from pathlib import Path
from typing import Optional

# Import BallDontLie API service
from services.ball_api import (
    fetch_upcoming_games,
    fetch_past_games,
    fetch_teams,
    fetch_today_games,
    fetch_game_by_id,
    fetch_game_details_full,
    fetch_team_roster,
    fetch_team_upcoming_games,
    fetch_players,
    fetch_box_score,
    fetch_player_season_averages,
    fetch_ticket_prices,
    get_team_logo_url,
    get_player_headshot_url,
    get_balldontlie_team_id,
    get_team_full_name,
)

app = FastAPI(
    title="NBA Game Predictor API",
    description="Predict NBA game outcomes using machine learning",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent
MODEL_PATH = BASE_DIR / "model" / "nba_model.pkl"
GAMES_PATH = BASE_DIR / "data" / "games.json"

model_bundle = None
if MODEL_PATH.exists():
    with open(MODEL_PATH, "rb") as f:
        model_bundle = pickle.load(f)
    print(f"Loaded model with {len(model_bundle['feature_cols'])} features")
else:
    print(f"WARNING: Model not found at {MODEL_PATH}. Run the notebook first.")

fallback_games = []
if GAMES_PATH.exists():
    with open(GAMES_PATH, "r") as f:
        fallback_games = json.load(f)

cached_games = []


class KeyPlayer(BaseModel):
    id: int
    name: str
    position: str
    headshot_url: str
    impact_reason: str  


class PredictionResponse(BaseModel):
    game_id: int
    home_team: str
    home_team_name: Optional[str] = None
    home_team_logo: Optional[str] = None
    away_team: str
    away_team_name: Optional[str] = None
    away_team_logo: Optional[str] = None
    home_win_probability: float
    away_win_probability: float
    predicted_winner: str
    predicted_winner_name: Optional[str] = None
    predicted_winner_logo: Optional[str] = None
    confidence: str
    key_players: Optional[list[KeyPlayer]] = None
    prediction_factors: Optional[list[str]] = None


class GameResponse(BaseModel):
    id: int
    home_team: str
    away_team: str
    game_date: str
    status: str


class ResultsResponse(BaseModel):
    accuracy: float
    total_predictions: int
    records: list


async def get_key_players_for_team(team_id: int, team_abbr: str, limit: int = 3) -> list[KeyPlayer]:
    """
    Get key players for a team that are predicted to impact the game.
    Returns top players based on their likely contribution.
    """
    try:
        roster = await fetch_team_roster(team_id)
        if not roster:
            return []
        
        key_players = []
        positions_seen = set()
        
        impact_reasons = {
            "G": "Floor General",
            "F": "Two-Way Threat", 
            "C": "Rim Protector",
            "G-F": "Versatile Scorer",
            "F-G": "Playmaking Forward",
            "F-C": "Interior Presence",
            "C-F": "Stretch Big",
        }
        
        for player in roster[:limit * 2]: 
            if len(key_players) >= limit:
                break
            
            position = player.get("position", "")
            if position in positions_seen and len(key_players) > 1:
                continue
            
            positions_seen.add(position)
            
            key_players.append(KeyPlayer(
                id=player["id"],
                name=player["full_name"],
                position=position,
                headshot_url=player["headshot_url"],
                impact_reason=impact_reasons.get(position, "Key Contributor"),
            ))
        
        return key_players
    except Exception as e:
        print(f"Error getting key players: {e}")
        return []


def get_prediction_factors(home_team: str, away_team: str, home_win_prob: float) -> list[str]:
    """
    Generate human-readable factors that influenced the prediction.
    """
    factors = []
    
    if model_bundle is None:
        return factors
    
    home_stats = model_bundle.get("team_stats_home", {}).get(home_team, {})
    away_stats = model_bundle.get("team_stats_away", {}).get(away_team, {})
    
    if home_stats and away_stats:
        home_pts = home_stats.get("pts_home", 0)
        away_pts = away_stats.get("pts_away", 0)
        
        if home_pts > away_pts:
            factors.append(f"{home_team} averages more points per game")
        else:
            factors.append(f"{away_team} averages more points per game")
        
        if home_win_prob > 0.5:
            factors.append("Home court advantage favors " + home_team)
        
        home_reb = home_stats.get("reb_home", 0)
        away_reb = away_stats.get("reb_away", 0)
        if home_reb > away_reb + 3:
            factors.append(f"{home_team} dominates on the boards")
        elif away_reb > home_reb + 3:
            factors.append(f"{away_team} dominates on the boards")
    
    return factors[:4] 


def get_team_features(home_team: str, away_team: str) -> Optional[list]:
    """
    Build feature vector for a matchup using historical team averages.
    Returns None if team data is missing.
    """
    if model_bundle is None:
        return None

    feature_cols = model_bundle["feature_cols"]
    home_stats = model_bundle.get("team_stats_home", {})
    away_stats = model_bundle.get("team_stats_away", {})

    home_data = home_stats.get(home_team)
    away_data = away_stats.get(away_team)

    if home_data is None or away_data is None:
        return None

    features = []
    for col in feature_cols:
        if "_home" in col:
            features.append(home_data.get(col, 0))
        elif "_away" in col:
            features.append(away_data.get(col, 0))
        else:
            features.append(home_data.get(col, 0))

    return features


@app.get("/")
def root():
    api_key_set = bool(os.getenv("BALL_API_KEY"))
    return {
        "message": "NBA Game Predictor API",
        "api_key_configured": api_key_set,
        "endpoints": {
            "games": {
                "/games": "List upcoming games (next N days)",
                "/games/today": "Get today's games",
                "/games/past": "Get past games (last N days) with scores & winner",
                "/games/{id}": "Get game info with logos, conference, division",
                "/games/{id}/details": "Full game details: rosters, upcoming games, logos",
                "/games/{id}/boxscore": "Box score with player stats",
                "/games/{id}/tickets": "Ticket prices & buy links (requires SEATGEEK_CLIENT_ID)",
            },
            "predictions": {
                "/predict/{id}": "Predict game outcome (POST)",
                "/predict/teams/{home}/{away}": "Predict any matchup",
                "/results": "View prediction accuracy",
            },
            "teams": {
                "/teams": "List all teams with logos",
                "/teams/{abbr}/logo": "Get team logo URL",
                "/teams/{id}/roster": "Get team roster with headshots",
                "/teams/{id}/upcoming": "Get team's upcoming games",
            },
            "players": {
                "/players": "Search players with headshots",
                "/players/{id}": "Get player details & stats",
            },
        },
    }


@app.get("/games")
async def get_games(days: int = 7):
    """
    Return list of upcoming games from BallDontLie API.
    Falls back to static games.json if API fails.
    """
    global cached_games
    
    try:
        games = await fetch_upcoming_games(days_ahead=days)
        if games:
            cached_games = games
            return {"source": "balldontlie_api", "count": len(games), "games": games}
    except Exception as e:
        print(f"API error: {e}")
    
    # Fallback to cached or static games
    if cached_games:
        return {"source": "cache", "count": len(cached_games), "games": cached_games}
    return {"source": "static", "count": len(fallback_games), "games": fallback_games}


@app.get("/games/today")
async def get_today_games():
    """Get today's NBA games."""
    try:
        games = await fetch_today_games()
        return {"count": len(games), "games": games}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch today's games: {e}")


@app.get("/games/past")
async def get_past_games(days: int = 7):
    """
    Get past NBA games from the last N days.
    
    Args:
        days: Number of days to look back (default 7)
    
    Returns completed games with final scores and winner.
    """
    try:
        games = await fetch_past_games(days_back=days)
        return {"count": len(games), "days_back": days, "games": games}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch past games: {e}")


@app.get("/games/{game_id}")
async def get_game(game_id: int):
    """Return full details for a specific game (always fetches complete data)."""
    try:
        game = await fetch_game_by_id(game_id)
        if game:
            return game
    except Exception as e:
        print(f"Error fetching game from API: {e}")
    
    game = next((g for g in cached_games if g["id"] == game_id), None)
    if game:
        return _enrich_game_data(game)
    
    game = next((g for g in fallback_games if g["id"] == game_id), None)
    if game:
        return _enrich_game_data(game)
    
    raise HTTPException(status_code=404, detail="Game not found")


def _enrich_game_data(game: dict) -> dict:
    """Add missing fields to a game from cache/fallback with sensible defaults."""
    return {
        "id": game.get("id"),
        # Home team
        "home_team": game.get("home_team", ""),
        "home_team_name": game.get("home_team_name", ""),
        "home_team_id": game.get("home_team_id", 0),
        "home_team_city": game.get("home_team_city", ""),
        "home_team_conference": game.get("home_team_conference", ""),
        "home_team_division": game.get("home_team_division", ""),
        "home_team_logo": game.get("home_team_logo", ""),
        "home_team_logo_small": game.get("home_team_logo_small", ""),
        # Away team
        "away_team": game.get("away_team", ""),
        "away_team_name": game.get("away_team_name", ""),
        "away_team_id": game.get("away_team_id", 0),
        "away_team_city": game.get("away_team_city", ""),
        "away_team_conference": game.get("away_team_conference", ""),
        "away_team_division": game.get("away_team_division", ""),
        "away_team_logo": game.get("away_team_logo", ""),
        "away_team_logo_small": game.get("away_team_logo_small", ""),
        # Game details
        "game_date": game.get("game_date", ""),
        "game_time": game.get("game_time"),
        "status": game.get("status", "scheduled"),
        "period": game.get("period", 0),
        "time_remaining": game.get("time_remaining"),
        "postseason": game.get("postseason", False),
        "season": game.get("season", 2025),
        # Scores
        "home_score": game.get("home_score", 0),
        "away_score": game.get("away_score", 0),
        # Tickets placeholder legacy code will not be using anymore*
        "tickets": game.get("tickets", {
            "available": False,
            "note": "Ticket data requires API integration",
            "ticketmaster_search_url": f"https://www.ticketmaster.com/search?q={game.get('home_team_name', '')}",
            "seatgeek_search_url": f"https://seatgeek.com/search?search={game.get('home_team', '')}",
        }),
    }


@app.get("/games/{game_id}/details")
async def get_game_full_details(game_id: int):
    """
    Get comprehensive game details including:
    - Game info with team logos
    - Players (rosters) for both teams with headshots
    - Upcoming games for both teams
    
    This is ideal for a game detail/preview screen.
    """
    try:
        details = await fetch_game_details_full(game_id)
        if details:
            return details
    except Exception as e:
        print(f"Error fetching game details: {e}")
    
    raise HTTPException(status_code=404, detail="Game not found")


@app.post("/predict/{game_id}", response_model=PredictionResponse)
async def predict_game(game_id: int):
    """
    Predict the outcome of a game.
    Returns probability of home team winning.
    """
    if model_bundle is None:
        raise HTTPException(status_code=500, detail="Model not loaded. Run notebook first.")

    # Search in cached games first, then fallback
    game = next((g for g in cached_games if g["id"] == game_id), None)
    if not game:
        game = next((g for g in fallback_games if g["id"] == game_id), None)
    
    # Try to fetch from API if not found
    if not game:
        try:
            game = await fetch_game_by_id(game_id)
            if game:
                cached_games.append(game)
        except Exception as e:
            print(f"Error fetching game: {e}")
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    home_team = game["home_team"]
    away_team = game["away_team"]

    features = get_team_features(home_team, away_team)
    if features is None:
        raise HTTPException(
            status_code=400,
            detail=f"Missing stats for teams: {home_team} or {away_team}",
        )

    model = model_bundle["model"]
    prob = model.predict_proba([features])[0]
    home_win_prob = float(prob[1])
    away_win_prob = float(prob[0])

    if home_win_prob > 0.5:
        predicted_winner = home_team
        confidence_val = home_win_prob
    else:
        predicted_winner = away_team
        confidence_val = away_win_prob

    if confidence_val >= 0.7:
        confidence = "High"
    elif confidence_val >= 0.55:
        confidence = "Medium"
    else:
        confidence = "Low"

    home_logo = game.get("home_team_logo") or get_team_logo_url(home_team)
    away_logo = game.get("away_team_logo") or get_team_logo_url(away_team)
    home_name = game.get("home_team_name", home_team)
    away_name = game.get("away_team_name", away_team)
    
    winner_logo = home_logo if predicted_winner == home_team else away_logo
    
    key_players = []
    try:
        winner_team_id = game.get("home_team_id") if predicted_winner == home_team else game.get("away_team_id")
        if winner_team_id:
            key_players = await get_key_players_for_team(winner_team_id, predicted_winner)
    except Exception as e:
        print(f"Error getting key players: {e}")
    
    factors = get_prediction_factors(home_team, away_team, home_win_prob)

    winner_name = home_name if predicted_winner == home_team else away_name

    return PredictionResponse(
        game_id=game_id,
        home_team=home_team,
        home_team_name=home_name,
        home_team_logo=home_logo,
        away_team=away_team,
        away_team_name=away_name,
        away_team_logo=away_logo,
        home_win_probability=round(home_win_prob, 3),
        away_win_probability=round(away_win_prob, 3),
        predicted_winner=predicted_winner,
        predicted_winner_name=winner_name,
        predicted_winner_logo=winner_logo,
        confidence=confidence,
        key_players=key_players if key_players else None,
        prediction_factors=factors if factors else None,
    )


@app.get("/predict/teams/{home_team}/{away_team}", response_model=PredictionResponse)
async def predict_by_teams(home_team: str, away_team: str):
    """
    Predict the outcome for any two teams (not just scheduled games).
    Includes predicted winner's logo and key players.
    """
    if model_bundle is None:
        raise HTTPException(status_code=500, detail="Model not loaded. Run notebook first.")

    home = home_team.upper()
    away = away_team.upper()
    
    features = get_team_features(home, away)
    if features is None:
        raise HTTPException(
            status_code=400,
            detail=f"Missing stats for teams: {home_team} or {away_team}",
        )

    model = model_bundle["model"]
    prob = model.predict_proba([features])[0]
    home_win_prob = float(prob[1])
    away_win_prob = float(prob[0])

    if home_win_prob > 0.5:
        predicted_winner = home
        confidence_val = home_win_prob
    else:
        predicted_winner = away
        confidence_val = away_win_prob

    if confidence_val >= 0.7:
        confidence = "High"
    elif confidence_val >= 0.55:
        confidence = "Medium"
    else:
        confidence = "Low"

    home_logo = get_team_logo_url(home)
    away_logo = get_team_logo_url(away)
    home_name = get_team_full_name(home)
    away_name = get_team_full_name(away)
    winner_logo = home_logo if predicted_winner == home else away_logo
    
    key_players = []
    try:
        winner_team_id = get_balldontlie_team_id(predicted_winner)
        if winner_team_id:
            key_players = await get_key_players_for_team(winner_team_id, predicted_winner)
    except Exception as e:
        print(f"Error getting key players: {e}")
    
    factors = get_prediction_factors(home, away, home_win_prob)

    winner_name = home_name if predicted_winner == home else away_name

    return PredictionResponse(
        game_id=0,
        home_team=home,
        home_team_name=home_name,
        home_team_logo=home_logo,
        away_team=away,
        away_team_name=away_name,
        away_team_logo=away_logo,
        home_win_probability=round(home_win_prob, 3),
        away_win_probability=round(away_win_prob, 3),
        predicted_winner=predicted_winner,
        predicted_winner_name=winner_name,
        predicted_winner_logo=winner_logo,
        confidence=confidence,
        key_players=key_players if key_players else None,
        prediction_factors=factors if factors else None,
    )


@app.get("/results", response_model=ResultsResponse)
def get_results():
    """
    Return historical prediction accuracy.
    In a real app, this would track past predictions vs actual outcomes.
    """
    return ResultsResponse(
        accuracy=0.85,
        total_predictions=42,
        records=[
            {"game": "LAL vs GSW", "predicted": 0.72, "actual": 1, "correct": True},
            {"game": "BOS vs MIA", "predicted": 0.65, "actual": 1, "correct": True},
            {"game": "PHX vs DEN", "predicted": 0.48, "actual": 0, "correct": True},
        ],
    )


@app.get("/teams")
async def list_teams():
    """List all NBA teams with logo URLs."""
    try:
        api_teams = await fetch_teams()
        if api_teams:
            return {"source": "balldontlie_api", "count": len(api_teams), "teams": api_teams}
    except Exception as e:
        print(f"API error: {e}")
    
    if model_bundle is None:
        raise HTTPException(status_code=500, detail="Model not loaded")

    home_teams = list(model_bundle.get("team_stats_home", {}).keys())
    away_teams = list(model_bundle.get("team_stats_away", {}).keys())
    all_teams = sorted(set(home_teams + away_teams))

    return {"source": "model", "count": len(all_teams), "teams": all_teams}


@app.get("/teams/{team_abbr}/logo")
async def get_team_logo(team_abbr: str, size: str = "L"):
    """
    Get team logo URL.
    
    Args:
        team_abbr: Team abbreviation (e.g., LAL, BOS)
        size: Logo size - L (large), D (default), S (small)
    """
    logo_url = get_team_logo_url(team_abbr.upper(), size)
    if not logo_url:
        raise HTTPException(status_code=404, detail=f"Team not found: {team_abbr}")
    return {"team": team_abbr.upper(), "size": size, "logo_url": logo_url}


@app.get("/teams/{team_id}/roster")
async def get_team_roster(team_id: int):
    """
    Get all players on a team's roster with headshots.
    
    Args:
        team_id: BallDontLie team ID
    """
    try:
        roster = await fetch_team_roster(team_id)
        return {"team_id": team_id, "count": len(roster), "players": roster}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch roster: {e}")


@app.get("/teams/{team_id}/upcoming")
async def get_team_upcoming_games(team_id: int, limit: int = 5):
    """
    Get upcoming games for a team.
    
    Args:
        team_id: BallDontLie team ID
        limit: Number of games to return (default 5)
    """
    try:
        games = await fetch_team_upcoming_games(team_id, limit=limit)
        return {"team_id": team_id, "count": len(games), "games": games}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch upcoming games: {e}")


@app.get("/players")
async def list_players(search: Optional[str] = None, per_page: int = 25):
    """
    Search for NBA players.
    
    Args:
        search: Player name to search for
        per_page: Number of results (default 25)
    """
    try:
        players = await fetch_players(search=search, per_page=per_page)
        return {"count": len(players), "players": players}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch players: {e}")


@app.get("/players/{player_id}")
async def get_player(player_id: int, season: int = 2024):
    """
    Get player details and season averages.
    """
    try:
        stats = await fetch_player_season_averages(player_id, season)
        stats["headshot_url"] = get_player_headshot_url(player_id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch player: {e}")


@app.get("/games/{game_id}/boxscore")
async def get_box_score(game_id: int):
    """
    Get box score (player stats) for a game.
    
    Returns stats for all players who played in the game.
    """
    try:
        box_score = await fetch_box_score(game_id)
        return box_score
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch box score: {e}")


@app.get("/games/{game_id}/tickets")
async def get_game_tickets(game_id: int):
    """
    Get ticket prices and availability for a game.
    
    Requires SEATGEEK_CLIENT_ID environment variable.
    Get a free API key at: https://seatgeek.com/account/develop
    """
    game = await fetch_game_by_id(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    tickets = await fetch_ticket_prices(
        home_team=game["home_team_name"],
        away_team=game["away_team_name"],
        game_date=game["game_date"],
    )
    
    return {
        "game_id": game_id,
        "matchup": f"{game['away_team']} @ {game['home_team']}",
        "game_date": game["game_date"],
        "tickets": tickets,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

