from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/{user_id}", response_model=schemas.TaskOut)
def create_task(user_id: str, task: schemas.TaskCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    new_task = models.Task(
        user_id=user_id,
        title=task.title,
        description=task.description,
        due_date=task.due_date,
        priority=task.priority,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


@router.get("/{user_id}", response_model=list[schemas.TaskOut])
def list_tasks(user_id: str, db: Session = Depends(get_db)):
    return db.query(models.Task).filter(models.Task.user_id == user_id).all()


@router.put("/{task_id}/toggle", response_model=schemas.TaskOut)
def toggle_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tâche introuvable")
    task.done = not task.done
    db.commit()
    db.refresh(task)
    return task