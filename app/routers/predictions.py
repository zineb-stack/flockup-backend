from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, timedelta
import joblib
import pandas as pd
import os

from ..database import get_db
from .. import models

router = APIRouter(prefix="/predict", tags=["predictions"])

MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ml", "habit_predictor.pkl")

_bundle = None

def get_model_bundle():
    global _bundle
    if _bundle is None:
        if not os.path.exists(MODEL_PATH):
            raise HTTPException(status_code=503, detail="Modèle non entraîné. Lancez ml/train_model.py")
        _bundle = joblib.load(MODEL_PATH)
    return _bundle


@router.get("/{habit_id}")
def predict_habit_success(habit_id: str, db: Session = Depends(get_db)):
    bundle = get_model_bundle()
    model = bundle["model"]
    user_mapping = bundle["user_mapping"]
    feature_names = bundle["features"]

    habit = db.query(models.Habit).filter(models.Habit.id == habit_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habitude introuvable")

    user_id_str = str(habit.user_id)
    today = date.today()

    # Récupérer les 30 derniers logs pour calculer les features glissantes
    logs = (
        db.query(models.HabitLog)
        .filter(models.HabitLog.habit_id == habit_id)
        .order_by(models.HabitLog.log_date.desc())
        .limit(30)
        .all()
    )

    if not logs:
        return {
            "habit_id": habit_id,
            "success_probability": None,
            "message": "Pas assez d'historique pour prédire (0 log trouvé)",
        }

    completions = [1 if l.completed else 0 for l in reversed(logs)]  # ordre chronologique

    completion_rate_14d = sum(completions[-14:]) / len(completions[-14:])
    completion_rate_30d = sum(completions) / len(completions)
    completed_yesterday = completions[-1] if completions else 0

    missed_last_7 = sum(1 for c in completions[-7:] if c == 0)

    day_of_week = today.weekday()  # 0=lundi ... attention: Postgres DOW=0 dimanche, ajuster si besoin
    is_weekend = 1 if today.weekday() >= 5 else 0

    user_id_encoded = user_mapping.get(user_id_str, -1)  # -1 si user inconnu du training

    features = pd.DataFrame([{
        "streak_count": habit.streak_count,
        "day_of_week": day_of_week,
        "is_weekend": is_weekend,
        "missed_last_7_days": missed_last_7,
        "completion_rate_14d": completion_rate_14d,
        "completion_rate_30d": completion_rate_30d,
        "completed_yesterday": completed_yesterday,
        "user_id_encoded": user_id_encoded,
    }])[feature_names]

    probability = model.predict_proba(features)[0][1]  # proba de la classe "completed=1"

    return {
        "habit_id": habit_id,
        "habit_title": habit.title,
        "success_probability": round(float(probability), 3),
        "streak_count": habit.streak_count,
    }