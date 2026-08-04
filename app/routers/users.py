from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import hashlib

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/users", tags=["users"])


def hash_password(password: str) -> str:
    # Simplifié pour le MVP — à remplacer par bcrypt/passlib en production
    return hashlib.sha256(password.encode()).hexdigest()


@router.post("/", response_model=schemas.UserOut)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    new_user = models.User(
        email=user.email,
        name=user.name,
        password_hash=hash_password(user.password),
    )
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé")
    db.refresh(new_user)
    return new_user


@router.get("/", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()

from pydantic import BaseModel

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login", response_model=schemas.UserOut)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == credentials.email).first()
    if not user or user.password_hash != hash_password(credentials.password):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    return user

@router.get("/{user_id}", response_model=schemas.UserOut)
def get_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return user


class UserUpdate(BaseModel):
    name: str | None = None
    avatar_url: str | None = None
    objectives: str | None = None

@router.put("/{user_id}", response_model=schemas.UserOut)
def update_user(user_id: str, update: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    if update.name is not None:
        user.name = update.name
    if update.avatar_url is not None:
        user.avatar_url = update.avatar_url
    if update.objectives is not None:
        user.objectives = update.objectives
    db.commit()
    db.refresh(user)
    return user

@router.get("/search/{query}", response_model=list[schemas.UserSearchOut])
def search_users(query: str, db: Session = Depends(get_db)):
    results = db.query(models.User).filter(
        (models.User.name.ilike(f"%{query}%")) | (models.User.email.ilike(f"%{query}%"))
    ).limit(10).all()
    return results

@router.delete("/{user_id}")
def delete_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    db.delete(user)
    db.commit()
    return {"message": "Compte supprimé"}