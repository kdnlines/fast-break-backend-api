"""
BallDontLie API Integration

Fetches live NBA games and team data from the BallDontLie API.

For images (logos, headshots), we use the official NBA CDN.
"""

import os
import httpx
from datetime import datetime, timedelta
from typing import Optional

# API Configuration
BALL_API_KEY = os.getenv("BALL_API_KEY", "")
BASE_URL = "https://api.balldontlie.io/v1"

SEATGEEK_CLIENT_ID = os.getenv("SEATGEEK_CLIENT_ID", "")
SEATGEEK_BASE_URL = "https://api.seatgeek.com/2"

# NBA CDN for images (publicly accessible)
NBA_CDN_BASE = "https://cdn.nba.com"

# Team ID mapping for NBA CDN logos (Abbreviation -> NBA ID)
TEAM_NBA_IDS = {
    "ATL": 1610612737, "BOS": 1610612738, "BKN": 1610612751, "CHA": 1610612766,
    "CHI": 1610612741, "CLE": 1610612739, "DAL": 1610612742, "DEN": 1610612743,
    "DET": 1610612765, "GSW": 1610612744, "HOU": 1610612745, "IND": 1610612754,
    "LAC": 1610612746, "LAL": 1610612747, "MEM": 1610612763, "MIA": 1610612748,
    "MIL": 1610612749, "MIN": 1610612750, "NOP": 1610612740, "NYK": 1610612752,
    "OKC": 1610612760, "ORL": 1610612753, "PHI": 1610612755, "PHX": 1610612756,
    "POR": 1610612757, "SAC": 1610612758, "SAS": 1610612759, "TOR": 1610612761,
    "UTA": 1610612762, "WAS": 1610612764,
}

# BallDontLie API team IDs (Abbreviation -> BallDontLie ID)
BALLDONTLIE_TEAM_IDS = {
    "ATL": 1, "BOS": 2, "BKN": 3, "CHA": 4, "CHI": 5,
    "CLE": 6, "DAL": 7, "DEN": 8, "DET": 9, "GSW": 10,
    "HOU": 11, "IND": 12, "LAC": 13, "LAL": 14, "MEM": 15,
    "MIA": 16, "MIL": 17, "MIN": 18, "NOP": 19, "NYK": 20,
    "OKC": 21, "ORL": 22, "PHI": 23, "PHX": 24, "POR": 25,
    "SAC": 26, "SAS": 27, "TOR": 28, "UTA": 29, "WAS": 30,
}

# Team full names
TEAM_FULL_NAMES = {
    "ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "BKN": "Brooklyn Nets",
    "CHA": "Charlotte Hornets", "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets", "DET": "Detroit Pistons",
    "GSW": "Golden State Warriors", "HOU": "Houston Rockets", "IND": "Indiana Pacers",
    "LAC": "Los Angeles Clippers", "LAL": "Los Angeles Lakers", "MEM": "Memphis Grizzlies",
    "MIA": "Miami Heat", "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves",
    "NOP": "New Orleans Pelicans", "NYK": "New York Knicks", "OKC": "Oklahoma City Thunder",
    "ORL": "Orlando Magic", "PHI": "Philadelphia 76ers", "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers", "SAC": "Sacramento Kings", "SAS": "San Antonio Spurs",
    "TOR": "Toronto Raptors", "UTA": "Utah Jazz", "WAS": "Washington Wizards",
}


def get_balldontlie_team_id(team_abbr: str) -> Optional[int]:
    """Get BallDontLie team ID from abbreviation."""
    return BALLDONTLIE_TEAM_IDS.get(team_abbr.upper())


def get_team_full_name(team_abbr: str) -> str:
    """Get team full name from abbreviation."""
    return TEAM_FULL_NAMES.get(team_abbr.upper(), team_abbr)


async def fetch_ticket_prices(home_team: str, away_team: str, game_date: str) -> dict:
    """
    Fetch ticket prices from SeatGeek API.
    
    Args:
        home_team: Home team name (e.g., "Philadelphia 76ers")
        away_team: Away team name (e.g., "Golden State Warriors")
        game_date: Game date in YYYY-MM-DD format
    
    Returns:
        Ticket information including prices and buy links
    """
    if not SEATGEEK_CLIENT_ID:
        return {
            "available": False,
            "error": "SEATGEEK_CLIENT_ID not configured",
            "ticketmaster_url": f"https://www.ticketmaster.com/search?q={home_team}",
            "seatgeek_url": f"https://seatgeek.com/search?search={home_team}",
        }
    
    try:
        async with httpx.AsyncClient() as client:
            # Search for NBA games matching the teams and date
            response = await client.get(
                f"{SEATGEEK_BASE_URL}/events",
                params={
                    "client_id": SEATGEEK_CLIENT_ID,
                    "q": f"{away_team} at {home_team}",
                    "type": "nba",
                    "datetime_local.gte": game_date,
                    "datetime_local.lte": game_date + "T23:59:59",
                    "per_page": 1,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            
            events = data.get("events", [])
            if not events:
                return {
                    "available": False,
                    "message": "No ticket listings found",
                    "seatgeek_search_url": f"https://seatgeek.com/search?search={home_team}",
                }
            
            event = events[0]
            stats = event.get("stats", {})
            
            return {
                "available": True,
                "event_id": event.get("id"),
                "event_url": event.get("url"),
                "venue": {
                    "name": event.get("venue", {}).get("name"),
                    "city": event.get("venue", {}).get("city"),
                    "state": event.get("venue", {}).get("state"),
                    "capacity": event.get("venue", {}).get("capacity"),
                    "address": event.get("venue", {}).get("address"),
                },
                "prices": {
                    "lowest_price": stats.get("lowest_price"),
                    "average_price": stats.get("average_price"),
                    "highest_price": stats.get("highest_price"),
                    "listing_count": stats.get("listing_count"),
                },
                "popularity": event.get("score"),
                "buy_url": event.get("url"),
            }
    except Exception as e:
        print(f"Error fetching ticket prices: {e}")
        return {
            "available": False,
            "error": str(e),
            "seatgeek_search_url": f"https://seatgeek.com/search?search={home_team}",
        }


def get_team_logo_url(team_abbr: str, size: str = "L") -> str:
    """
    Get NBA team logo URL from official CDN.
    
    Args:
        team_abbr: Team abbreviation (e.g., "LAL", "BOS")
        size: Logo size - "L" (large), "D" (default), "S" (small)
    
    Returns:
        URL to team logo SVG
    """
    nba_id = TEAM_NBA_IDS.get(team_abbr.upper())
    if nba_id:
        return f"{NBA_CDN_BASE}/logos/nba/{nba_id}/primary/{size}/logo.svg"
    return ""


def get_player_headshot_url(player_id: int, size: str = "260x190") -> str:
    """
    Get NBA player headshot URL from official CDN.
    
    Args:
        player_id: NBA player ID
        size: Image size - "260x190", "1040x760"
    
    Returns:
        URL to player headshot PNG
    """
    return f"{NBA_CDN_BASE}/headshots/nba/latest/{size}/{player_id}.png"


def get_headers() -> dict:
    """Return headers with API key authorization."""
    if not BALL_API_KEY:
        raise ValueError("BALL_API_KEY environment variable not set")
    return {
        "Authorization": BALL_API_KEY,
    }


async def fetch_games(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    team_ids: Optional[list[int]] = None,
    per_page: int = 25,
) -> dict:
    """
    Fetch NBA games from BallDontLie API.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        team_ids: Optional list of team IDs to filter
        per_page: Number of results per page (default 25)
    
    Returns:
        API response with games data
    """
    params = {"per_page": per_page}
    
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if team_ids:
        params["team_ids[]"] = team_ids

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/games",
            headers=get_headers(),
            params=params,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()


async def fetch_upcoming_games(days_ahead: int = 7) -> list[dict]:
    """
    Fetch upcoming NBA games for the next N days.
    
    Returns list of games formatted for our API with team logos.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    
    try:
        data = await fetch_games(start_date=today, end_date=end_date, per_page=100)
        games = data.get("data", [])
        
        # Format games for  API
        formatted_games = []
        for game in games:
            home_abbr = game["home_team"]["abbreviation"]
            away_abbr = game["visitor_team"]["abbreviation"]
            formatted_games.append({
                "id": game["id"],
                "home_team": home_abbr,
                "home_team_name": game["home_team"]["full_name"],
                "home_team_logo": get_team_logo_url(home_abbr),
                "home_team_logo_small": get_team_logo_url(home_abbr, "S"),
                "away_team": away_abbr,
                "away_team_name": game["visitor_team"]["full_name"],
                "away_team_logo": get_team_logo_url(away_abbr),
                "away_team_logo_small": get_team_logo_url(away_abbr, "S"),
                "game_date": game["date"][:10],  # YYYY-MM-DD
                "status": game.get("status", "scheduled"),
                "home_score": game.get("home_team_score"),
                "away_score": game.get("visitor_team_score"),
                "season": game.get("season"),
            })
        
        return formatted_games
    except Exception as e:
        print(f"Error fetching games: {e}")
        return []


async def fetch_today_games() -> list[dict]:
    """Fetch today's NBA games."""
    today = datetime.now().strftime("%Y-%m-%d")
    return await fetch_upcoming_games(days_ahead=0)


async def fetch_past_games(days_back: int = 7) -> list[dict]:
    """
    Fetch past NBA games from the last N days.
    
    Returns list of completed games with scores.
    """
    today = datetime.now()
    start_date = (today - timedelta(days=days_back)).strftime("%Y-%m-%d")
    end_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")  # Yesterday
    
    try:
        data = await fetch_games(start_date=start_date, end_date=end_date, per_page=100)
        games = data.get("data", [])
        
        # Format games for our API (only completed games)
        formatted_games = []
        for game in games:
            # Skip games that aren't finished
            status = game.get("status", "")
            if status not in ["Final", "final"] and game.get("home_team_score", 0) == 0:
                continue
                
            home_abbr = game["home_team"]["abbreviation"]
            away_abbr = game["visitor_team"]["abbreviation"]
            
            home_score = game.get("home_team_score", 0)
            away_score = game.get("visitor_team_score", 0)
            
            # Determine winner
            winner = home_abbr if home_score > away_score else away_abbr
            winner_logo = get_team_logo_url(winner)
            
            formatted_games.append({
                "id": game["id"],
                "home_team": home_abbr,
                "home_team_name": game["home_team"]["full_name"],
                "home_team_logo": get_team_logo_url(home_abbr),
                "home_team_logo_small": get_team_logo_url(home_abbr, "S"),
                "away_team": away_abbr,
                "away_team_name": game["visitor_team"]["full_name"],
                "away_team_logo": get_team_logo_url(away_abbr),
                "away_team_logo_small": get_team_logo_url(away_abbr, "S"),
                "game_date": game["date"][:10],
                "status": "Final",
                "home_score": home_score,
                "away_score": away_score,
                "winner": winner,
                "winner_logo": winner_logo,
                "season": game.get("season"),
            })
        
        # Sort by date descending (most recent first)
        formatted_games.sort(key=lambda x: x["game_date"], reverse=True)
        
        return formatted_games
    except Exception as e:
        print(f"Error fetching past games: {e}")
        return []


async def fetch_game_by_id(game_id: int) -> Optional[dict]:
    """
    Fetch a specific game by ID from BallDontLie API.
    Returns all available game details.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/games/{game_id}",
                headers=get_headers(),
                timeout=30.0,
            )
            response.raise_for_status()
            game = response.json().get("data", {})
            
            if not game:
                return None
            
            home_abbr = game["home_team"]["abbreviation"]
            away_abbr = game["visitor_team"]["abbreviation"]
            home_team = game["home_team"]
            away_team = game["visitor_team"]
            
            return {
                "id": game["id"],
                # Home team details
                "home_team": home_abbr,
                "home_team_name": home_team.get("full_name", ""),
                "home_team_id": home_team.get("id"),
                "home_team_city": home_team.get("city", ""),
                "home_team_conference": home_team.get("conference", ""),
                "home_team_division": home_team.get("division", ""),
                "home_team_logo": get_team_logo_url(home_abbr),
                "home_team_logo_small": get_team_logo_url(home_abbr, "S"),
                # Away team details
                "away_team": away_abbr,
                "away_team_name": away_team.get("full_name", ""),
                "away_team_id": away_team.get("id"),
                "away_team_city": away_team.get("city", ""),
                "away_team_conference": away_team.get("conference", ""),
                "away_team_division": away_team.get("division", ""),
                "away_team_logo": get_team_logo_url(away_abbr),
                "away_team_logo_small": get_team_logo_url(away_abbr, "S"),
                # Game details
                "game_date": game.get("date", "")[:10] if game.get("date") else None,
                "game_time": game.get("time", None),
                "status": game.get("status", "scheduled"),
                "period": game.get("period", 0),
                "time_remaining": game.get("time", None),
                "postseason": game.get("postseason", False),
                "season": game.get("season"),
                # Scores
                "home_score": game.get("home_team_score", 0),
                "away_score": game.get("visitor_team_score", 0),
                # Note: Ticket prices require Ticketmaster/SeatGeek API
                "tickets": {
                    "available": False,
                    "note": "Ticket data requires Ticketmaster or SeatGeek API integration",
                    "ticketmaster_search_url": f"https://www.ticketmaster.com/search?q={home_team.get('full_name', '')}",
                    "seatgeek_search_url": f"https://seatgeek.com/search?search={home_abbr}",
                },
            }
    except Exception as e:
        print(f"Error fetching game {game_id}: {e}")
        return None


async def fetch_team_roster(team_id: int) -> list[dict]:
    """
    Fetch players for a specific team.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/players",
                headers=get_headers(),
                params={"team_ids[]": [team_id], "per_page": 50},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            
            players = []
            for player in data.get("data", []):
                players.append({
                    "id": player["id"],
                    "first_name": player["first_name"],
                    "last_name": player["last_name"],
                    "full_name": f"{player['first_name']} {player['last_name']}",
                    "position": player.get("position", ""),
                    "jersey_number": player.get("jersey_number", ""),
                    "height": player.get("height", ""),
                    "weight": player.get("weight", ""),
                    "headshot_url": get_player_headshot_url(player["id"]),
                })
            return players
    except Exception as e:
        print(f"Error fetching roster for team {team_id}: {e}")
        return []


async def fetch_team_upcoming_games(team_id: int, limit: int = 5) -> list[dict]:
    """
    Fetch upcoming games for a specific team.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/games",
                headers=get_headers(),
                params={
                    "team_ids[]": [team_id],
                    "start_date": today,
                    "end_date": end_date,
                    "per_page": limit,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            
            games = []
            for game in data.get("data", []):
                home_abbr = game["home_team"]["abbreviation"]
                away_abbr = game["visitor_team"]["abbreviation"]
                games.append({
                    "id": game["id"],
                    "home_team": home_abbr,
                    "home_team_name": game["home_team"]["full_name"],
                    "home_team_logo": get_team_logo_url(home_abbr),
                    "away_team": away_abbr,
                    "away_team_name": game["visitor_team"]["full_name"],
                    "away_team_logo": get_team_logo_url(away_abbr),
                    "game_date": game["date"][:10],
                    "status": game.get("status", "scheduled"),
                })
            return games
    except Exception as e:
        print(f"Error fetching upcoming games for team {team_id}: {e}")
        return []


async def fetch_game_details_full(game_id: int) -> Optional[dict]:
    """
    Fetch comprehensive game details including:
    - Game info with logos
    - Players (rosters) for both teams
    - Upcoming games for both teams
    """
    # First get the basic game info
    game = await fetch_game_by_id(game_id)
    if not game:
        return None
    
    home_team_id = game.get("home_team_id")
    away_team_id = game.get("away_team_id")
    
    # Fetch additional data in parallel
    home_roster = await fetch_team_roster(home_team_id) if home_team_id else []
    away_roster = await fetch_team_roster(away_team_id) if away_team_id else []
    home_upcoming = await fetch_team_upcoming_games(home_team_id, limit=5) if home_team_id else []
    away_upcoming = await fetch_team_upcoming_games(away_team_id, limit=5) if away_team_id else []
    
    return {
        "game": game,
        "home_team_details": {
            "abbreviation": game["home_team"],
            "name": game["home_team_name"],
            "logo_url": game["home_team_logo"],
            "logo_url_small": get_team_logo_url(game["home_team"], "S"),
            "roster": home_roster,
            "upcoming_games": home_upcoming,
        },
        "away_team_details": {
            "abbreviation": game["away_team"],
            "name": game["away_team_name"],
            "logo_url": game["away_team_logo"],
            "logo_url_small": get_team_logo_url(game["away_team"], "S"),
            "roster": away_roster,
            "upcoming_games": away_upcoming,
        },
    }


async def fetch_teams() -> list[dict]:
    """Fetch all NBA teams from BallDontLie API with logo URLs."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/teams",
            headers=get_headers(),
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        
        teams = []
        for team in data.get("data", []):
            abbr = team["abbreviation"]
            teams.append({
                "id": team["id"],
                "abbreviation": abbr,
                "city": team["city"],
                "name": team["name"],
                "full_name": team["full_name"],
                "conference": team["conference"],
                "division": team["division"],
                # Add logo URLs from NBA CDN
                "logo_url": get_team_logo_url(abbr, "L"),
                "logo_url_small": get_team_logo_url(abbr, "S"),
            })
        
        return teams


async def fetch_team_stats(team_id: int, season: int = 2024) -> dict:
    """
    Fetch team stats for a specific season.
    Note: BallDontLie may require different endpoints for detailed stats.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/season_averages",
            headers=get_headers(),
            params={"season": season, "team_id": team_id},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()


async def fetch_players(
    search: Optional[str] = None,
    team_ids: Optional[list[int]] = None,
    per_page: int = 25,
) -> list[dict]:
    """
    Fetch NBA players from BallDontLie API.
    
    Args:
        search: Search by player name
        team_ids: Filter by team IDs
        per_page: Results per page
    
    Returns:
        List of player objects with headshot URLs added
    """
    params = {"per_page": per_page}
    if search:
        params["search"] = search
    if team_ids:
        params["team_ids[]"] = team_ids

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/players",
            headers=get_headers(),
            params=params,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        players = []
        for player in data.get("data", []):
            player_data = {
                "id": player["id"],
                "first_name": player["first_name"],
                "last_name": player["last_name"],
                "full_name": f"{player['first_name']} {player['last_name']}",
                "position": player.get("position", ""),
                "height": player.get("height", ""),
                "weight": player.get("weight", ""),
                "jersey_number": player.get("jersey_number", ""),
                "college": player.get("college", ""),
                "country": player.get("country", ""),
                "draft_year": player.get("draft_year"),
                "draft_round": player.get("draft_round"),
                "draft_number": player.get("draft_number"),
                "team": player.get("team", {}).get("abbreviation", ""),
                "team_name": player.get("team", {}).get("full_name", ""),
                # Add headshot URL (uses NBA player ID if available)
                "headshot_url": get_player_headshot_url(player["id"]),
            }
            players.append(player_data)

        return players


async def fetch_box_score(game_id: int) -> dict:
    """
    Fetch box score (player stats) for a specific game.
    
    Returns player stats for both teams in the game.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/box_scores",
            headers=get_headers(),
            params={"game_ids[]": [game_id]},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        
        if not data.get("data"):
            return {"game_id": game_id, "home_players": [], "away_players": []}
        
        box_score = data["data"][0] if data["data"] else {}
        
        return {
            "game_id": game_id,
            "home_team": box_score.get("home_team", {}).get("abbreviation", ""),
            "away_team": box_score.get("visitor_team", {}).get("abbreviation", ""),
            "home_players": [
                {
                    "player_id": p.get("player", {}).get("id"),
                    "name": f"{p.get('player', {}).get('first_name', '')} {p.get('player', {}).get('last_name', '')}",
                    "position": p.get("player", {}).get("position", ""),
                    "minutes": p.get("min", ""),
                    "points": p.get("pts", 0),
                    "rebounds": p.get("reb", 0),
                    "assists": p.get("ast", 0),
                    "steals": p.get("stl", 0),
                    "blocks": p.get("blk", 0),
                    "turnovers": p.get("turnover", 0),
                    "fg_made": p.get("fgm", 0),
                    "fg_attempted": p.get("fga", 0),
                    "fg3_made": p.get("fg3m", 0),
                    "fg3_attempted": p.get("fg3a", 0),
                    "ft_made": p.get("ftm", 0),
                    "ft_attempted": p.get("fta", 0),
                    "headshot_url": get_player_headshot_url(p.get("player", {}).get("id", 0)),
                }
                for p in box_score.get("home_team_stats", [])
            ],
            "away_players": [
                {
                    "player_id": p.get("player", {}).get("id"),
                    "name": f"{p.get('player', {}).get('first_name', '')} {p.get('player', {}).get('last_name', '')}",
                    "position": p.get("player", {}).get("position", ""),
                    "minutes": p.get("min", ""),
                    "points": p.get("pts", 0),
                    "rebounds": p.get("reb", 0),
                    "assists": p.get("ast", 0),
                    "steals": p.get("stl", 0),
                    "blocks": p.get("blk", 0),
                    "turnovers": p.get("turnover", 0),
                    "fg_made": p.get("fgm", 0),
                    "fg_attempted": p.get("fga", 0),
                    "fg3_made": p.get("fg3m", 0),
                    "fg3_attempted": p.get("fg3a", 0),
                    "ft_made": p.get("ftm", 0),
                    "ft_attempted": p.get("fta", 0),
                    "headshot_url": get_player_headshot_url(p.get("player", {}).get("id", 0)),
                }
                for p in box_score.get("visitor_team_stats", [])
            ],
        }


async def fetch_player_season_averages(player_id: int, season: int = 2024) -> dict:
    """
    Fetch season averages for a specific player.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/season_averages",
            headers=get_headers(),
            params={"season": season, "player_id": player_id},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        
        if not data.get("data"):
            return {}
        
        stats = data["data"][0] if data["data"] else {}
        return {
            "player_id": player_id,
            "season": season,
            "games_played": stats.get("games_played", 0),
            "minutes": stats.get("min", 0),
            "points": stats.get("pts", 0),
            "rebounds": stats.get("reb", 0),
            "assists": stats.get("ast", 0),
            "steals": stats.get("stl", 0),
            "blocks": stats.get("blk", 0),
            "turnovers": stats.get("turnover", 0),
            "fg_pct": stats.get("fg_pct", 0),
            "fg3_pct": stats.get("fg3_pct", 0),
            "ft_pct": stats.get("ft_pct", 0),
        }


# Synchronous versions for simpler use cases
def fetch_games_sync(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> list[dict]:
    """Synchronous version of fetch_games."""
    import asyncio
    
    async def _fetch():
        return await fetch_upcoming_games(days_ahead=7)
    
    return asyncio.run(_fetch())


def fetch_teams_sync() -> list[dict]:
    """Synchronous version of fetch_teams."""
    import asyncio
    return asyncio.run(fetch_teams())

