import sys
import os
import random
from datetime import date, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import SessionLocal
from app import models

db = SessionLocal()

# ============================================
# Profils d'utilisateurs différents (comportements variés)
# ============================================
PROFILES = [
    {"name": "Motivated Mona", "email": "mona@flockup.com", "base_prob": 0.85, "streak_bonus": 0.01, "weekend_drop": 0.0},
    {"name": "Regular Reda",   "email": "reda@flockup.com", "base_prob": 0.65, "streak_bonus": 0.015, "weekend_drop": 0.1},
    {"name": "Irregular Iman", "email": "iman@flockup.com", "base_prob": 0.35, "streak_bonus": 0.02, "weekend_drop": 0.2},
    {"name": "Weekend Walid",  "email": "walid@flockup.com", "base_prob": 0.30, "streak_bonus": 0.01, "weekend_drop": -0.4},
    {"name": "Dropout Driss",  "email": "driss@flockup.com", "base_prob": 0.75, "streak_bonus": -0.02, "weekend_drop": 0.15},
    {"name": "Steady Sara",    "email": "sara@flockup.com", "base_prob": 0.70, "streak_bonus": 0.005, "weekend_drop": 0.05},
    {"name": "Consistent Karim", "email": "karim@flockup.com", "base_prob": 0.90, "streak_bonus": 0.005, "weekend_drop": 0.02},
    {"name": "Slacker Salma",    "email": "salma@flockup.com", "base_prob": 0.20, "streak_bonus": 0.01, "weekend_drop": 0.05},
    {"name": "Improving Ilyas",  "email": "ilyas@flockup.com", "base_prob": 0.40, "streak_bonus": 0.03, "weekend_drop": 0.1},
    {"name": "Burnout Btissam",  "email": "btissam@flockup.com", "base_prob": 0.80, "streak_bonus": -0.03, "weekend_drop": 0.1},
]

DAYS_HISTORY = 365

for profile in PROFILES:
    # Créer ou récupérer le user
    user = db.query(models.User).filter_by(email=profile["email"]).first()
    if not user:
        user = models.User(email=profile["email"], password_hash="seedhash", name=profile["name"])
        db.add(user)
        db.commit()
        db.refresh(user)

    # Créer ou récupérer l'habit
    habit = db.query(models.Habit).filter_by(user_id=user.id, title="Lecture 20min").first()
    if not habit:
        habit = models.Habit(
            user_id=user.id, title="Lecture 20min", frequency="daily",
            category="lecture", streak_count=0, best_streak=0,
        )
        db.add(habit)
        db.commit()
        db.refresh(habit)

    # Nettoyer les anciens logs
    db.query(models.HabitLog).filter_by(habit_id=habit.id).delete()
    db.commit()

    # Générer les logs selon le profil
    start_date = date.today() - timedelta(days=DAYS_HISTORY)
    streak = 0
    best_streak = 0

    for i in range(DAYS_HISTORY):
        log_date = start_date + timedelta(days=i)
        is_weekend = log_date.weekday() >= 5  # samedi=5, dimanche=6

        prob = profile["base_prob"] + min(streak, 20) * profile["streak_bonus"]
        if is_weekend:
            prob -= profile["weekend_drop"]
        prob = max(0.02, min(0.98, prob))

        completed = random.random() < prob

        if completed:
            streak += 1
            best_streak = max(best_streak, streak)
        else:
            streak = 0

        db.add(models.HabitLog(
            habit_id=habit.id, user_id=user.id, log_date=log_date, completed=completed,
        ))

    habit.streak_count = streak
    habit.best_streak = best_streak
    db.commit()

    print(f"{profile['name']:20s} -> {DAYS_HISTORY} logs, streak final: {streak}, best: {best_streak}")

print("\nSeed multi-utilisateurs terminé ✅")
db.close()