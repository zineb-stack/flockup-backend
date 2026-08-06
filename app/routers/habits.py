from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from .. import models, schemas


router = APIRouter(prefix="/habits", tags=["habits"])


@router.post("/{user_id}", response_model=schemas.HabitOut)
def create_habit(user_id: str, habit: schemas.HabitCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    new_habit = models.Habit(
        user_id=user_id,
        title=habit.title,
        description=habit.description,
        frequency=habit.frequency,
        category=habit.category,
    )
    db.add(new_habit)
    db.commit()
    db.refresh(new_habit)
    return new_habit


@router.get("/{user_id}", response_model=list[schemas.HabitOut])
def list_habits(user_id: str, db: Session = Depends(get_db)):
    return db.query(models.Habit).filter(models.Habit.user_id == user_id).all()


@router.delete("/{habit_id}")
def delete_habit(habit_id: str, db: Session = Depends(get_db)):
    habit = db.query(models.Habit).filter(models.Habit.id == habit_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habitude introuvable")
    db.delete(habit)
    db.commit()
    return {"message": "Habitude supprimée"}


class HabitUpdate(schemas.BaseModel):
    title: str | None = None
    category: str | None = None
    frequency: str | None = None


@router.put("/{habit_id}", response_model=schemas.HabitOut)
def update_habit(habit_id: str, update: HabitUpdate, db: Session = Depends(get_db)):
    habit = db.query(models.Habit).filter(models.Habit.id == habit_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habitude introuvable")
    if update.title is not None:
        habit.title = update.title
    if update.category is not None:
        habit.category = update.category
    if update.frequency is not None:
        habit.frequency = update.frequency
    db.commit()
    db.refresh(habit)
    return habit

from datetime import date

@router.post("/{habit_id}/log")
def log_habit(habit_id: str, completed: bool = True, db: Session = Depends(get_db)):
    habit = db.query(models.Habit).filter(models.Habit.id == habit_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habitude introuvable")

    today = date.today()
    existing_log = db.query(models.HabitLog).filter_by(habit_id=habit_id, log_date=today).first()
    if existing_log:
        raise HTTPException(status_code=400, detail="Déjà enregistré aujourd'hui")

    new_log = models.HabitLog(
        habit_id=habit_id,
        user_id=habit.user_id,
        log_date=today,
        completed=completed,
    )
    db.add(new_log)

    if completed:
        habit.streak_count += 1
        if habit.streak_count > habit.best_streak:
            habit.best_streak = habit.streak_count
    else:
        habit.streak_count = 0

    db.commit()
    return {"message": "Log enregistré", "streak_count": habit.streak_count}

from sqlalchemy import extract

@router.get("/{habit_id}/calendar")
def get_habit_calendar(habit_id: str, year: int, month: int, db: Session = Depends(get_db)):
    logs = (
        db.query(models.HabitLog)
        .filter(
            models.HabitLog.habit_id == habit_id,
            extract("year", models.HabitLog.log_date) == year,
            extract("month", models.HabitLog.log_date) == month,
        )
        .all()
    )
    return [{"date": l.log_date.isoformat(), "completed": l.completed} for l in logs]    