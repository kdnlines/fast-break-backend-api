"""
Train a logistic regression model to predict NBA home team win probability.

Input data: backend/data/nba_training_data.csv
Output model: backend/model/nba_model.pkl
"""

import os
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "backend" / "data" / "nba_training_data.csv"
MODEL_PATH = PROJECT_ROOT / "backend" / "model" / "nba_model.pkl"


FEATURE_COLUMNS = [
    "off_rating_home",
    "off_rating_away",
    "def_rating_home",
    "def_rating_away",
    "net_rating_home",
    "net_rating_away",
    "pace_home",
    "pace_away",
    "home_rest_days",
    "away_rest_days",
    "home_last10_win_pct",
    "away_last10_win_pct",
    "home_starters_out",
    "away_starters_out",
]

LABEL_COLUMN = "home_win"


def load_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Training data not found at: {path}")

    df = pd.read_csv(path)
    missing_cols = [c for c in FEATURE_COLUMNS + [LABEL_COLUMN] if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns in CSV: {missing_cols}")

    return df


def build_pipeline() -> Pipeline:
    numeric_features = FEATURE_COLUMNS

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric_features),
        ],
        remainder="drop",
    )

    clf = LogisticRegression(
        max_iter=500,
        solver="lbfgs",
    )

    pipeline = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("clf", clf),
        ]
    )
    return pipeline


def train_and_evaluate(df: pd.DataFrame) -> Pipeline:
    X = df[FEATURE_COLUMNS]
    y = df[LABEL_COLUMN].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y if y.nunique() > 1 else None
    )

    model = build_pipeline()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    print("=== Model Evaluation ===")
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.3f}")
    try:
        auc = roc_auc_score(y_test, y_prob)
        print(f"ROC AUC: {auc:.3f}")
    except ValueError:
        print("ROC AUC: cannot be computed (only one class present in y_test).")

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, digits=3))

    return model


def save_model(model: Pipeline, path: Path) -> None:
    os.makedirs(path.parent, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(
            {
                "model": model,
                "feature_columns": FEATURE_COLUMNS,
                "label_column": LABEL_COLUMN,
            },
            f,
        )
    print(f"\nSaved trained model to: {path}")


def main() -> None:
    print(f"Loading data from {DATA_PATH} ...")
    df = load_data(DATA_PATH)
    print(f"Loaded {len(df)} rows.")

    model = train_and_evaluate(df)
    save_model(model, MODEL_PATH)


if __name__ == "__main__":
    main()




