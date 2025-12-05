# NBA Game Outcome Predictor – ML Backend

This backend contains the **machine learning pipeline** for training a logistic regression model that predicts the **probability that the home team wins** an NBA game.

## Files & Structure

- `requirements.txt` – Python dependencies.
- `data/nba_training_data.csv` – Training dataset (features + label).
- `model/train_model.py` – End‑to‑end ML pipeline:
  - load data
  - build feature matrix `X` and label `y`
  - train/test split
  - fit logistic regression
  - evaluate
  - save model to `model/nba_model.pkl`

## Training Data Schema (`data/nba_training_data.csv`)

Each row represents **one historical NBA game**. The model predicts `home_win` (1 if home team won, 0 otherwise).

Required columns:

- `game_id` – Unique identifier for the game.
- `date` – Game date (ISO string recommended).
- `home_team` – Home team code (e.g. `LAL`).
- `away_team` – Away team code (e.g. `GSW`).
- `off_rating_home` – Home team offensive rating prior to the game.
- `off_rating_away` – Away team offensive rating prior to the game.
- `def_rating_home` – Home team defensive rating prior to the game.
- `def_rating_away` – Away team defensive rating prior to the game.
- `net_rating_home` – `off_rating_home - def_rating_home`.
- `net_rating_away` – `off_rating_away - def_rating_away`.
- `pace_home` – Estimated possessions per game for the home team.
- `pace_away` – Estimated possessions per game for the away team.
- `home_rest_days` – Days of rest for the home team before the game.
- `away_rest_days` – Days of rest for the away team before the game.
- `home_last10_win_pct` – Home team win percentage over last 10 games before this game.
- `away_last10_win_pct` – Away team win percentage over last 10 games before this game.
- `home_starters_out` – Number of expected starters missing for the home team.
- `away_starters_out` – Number of expected starters missing for the away team.
- `home_win` – **Label**: `1` if home team won the game, otherwise `0`.

## How to Train the Model

1. Create or export your historical dataset to `data/nba_training_data.csv` using the schema above.
2. Create and activate a virtual environment (optional but recommended).
3. Install dependencies:

```bash
pip install -r backend/requirements.txt
```

4. Run the training script from the project root:

```bash
python backend/model/train_model.py
```

This will:

- print basic evaluation metrics to the console
- save the trained model to `backend/model/nba_model.pkl`

## Using the Model in FastAPI (Preview)

Later, your FastAPI app can load this model and call `predict_proba`:

```python
import pickle
import numpy as np

MODEL_PATH = "backend/model/nba_model.pkl"

with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)

feature_order = [
    "off_rating_home", "off_rating_away",
    "def_rating_home", "def_rating_away",
    "net_rating_home", "net_rating_away",
    "pace_home", "pace_away",
    "home_rest_days", "away_rest_days",
    "home_last10_win_pct", "away_last10_win_pct",
    "home_starters_out", "away_starters_out",
]

def predict_home_win_probability(feature_dict: dict) -> float:
    x_row = np.array([[feature_dict[name] for name in feature_order]])
    proba = model.predict_proba(x_row)[0][1]
    return float(proba)
```

The FastAPI `/predict/{game_id}` endpoint can build `feature_dict` for a scheduled game, call this helper, and return the probability to your React Native app.
