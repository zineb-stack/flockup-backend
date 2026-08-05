from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/channels", tags=["channels"])


def with_member_count(channel, db):
    count = db.query(models.ChannelMember).filter_by(
        channel_id=channel.id, status="approved"
    ).count()
    result = schemas.ChannelOut.model_validate(channel)
    result.member_count = count
    return result


@router.post("/{owner_id}", response_model=schemas.ChannelOut)
def create_channel(owner_id: str, channel: schemas.ChannelCreate, db: Session = Depends(get_db)):
    owner = db.query(models.User).filter(models.User.id == owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    new_channel = models.Channel(
        name=channel.name,
        description=channel.description,
        goal_topic=channel.goal_topic,
        owner_id=owner_id,
        is_private=channel.is_private,
    )
    db.add(new_channel)
    db.commit()
    db.refresh(new_channel)

    membership = models.ChannelMember(
        user_id=owner_id, channel_id=new_channel.id, role="admin", status="approved"
    )
    db.add(membership)
    db.commit()

    return with_member_count(new_channel, db)


@router.get("/", response_model=list[schemas.ChannelOut])
def list_channels(db: Session = Depends(get_db)):
    channels = db.query(models.Channel).all()
    return [with_member_count(c, db) for c in channels]


@router.get("/user/{user_id}", response_model=list[schemas.ChannelOut])
def list_my_channels(user_id: str, db: Session = Depends(get_db)):
    memberships = db.query(models.ChannelMember).filter_by(user_id=user_id, status="approved").all()
    channel_ids = [m.channel_id for m in memberships]
    channels = db.query(models.Channel).filter(models.Channel.id.in_(channel_ids)).all()
    return [with_member_count(c, db) for c in channels]


@router.post("/{channel_id}/join/{user_id}")
def join_channel(channel_id: str, user_id: str, db: Session = Depends(get_db)):
    existing = db.query(models.ChannelMember).filter_by(channel_id=channel_id, user_id=user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Déjà membre ou demande en attente")

    channel = db.query(models.Channel).filter(models.Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel introuvable")

    status = "pending" if channel.is_private else "approved"

    membership = models.ChannelMember(
        user_id=user_id, channel_id=channel_id, role="member", status=status
    )
    db.add(membership)
    db.commit()

    if status == "pending":
        return {"message": "Demande envoyée, en attente d'approbation"}
    return {"message": "Membre ajouté avec succès"}


@router.post("/{channel_id}/invite/{user_id}")
def invite_user(channel_id: str, user_id: str, db: Session = Depends(get_db)):
    existing = db.query(models.ChannelMember).filter_by(channel_id=channel_id, user_id=user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Déjà membre ou invité")

    membership = models.ChannelMember(
        user_id=user_id, channel_id=channel_id, role="member", status="approved"
    )
    db.add(membership)
    db.commit()
    return {"message": "Utilisateur invité avec succès"}


@router.get("/{channel_id}/pending", response_model=list[schemas.PendingMemberOut])
def list_pending(channel_id: str, db: Session = Depends(get_db)):
    pending = db.query(models.ChannelMember).filter_by(channel_id=channel_id, status="pending").all()
    result = []
    for p in pending:
        user = db.query(models.User).filter(models.User.id == p.user_id).first()
        if user:
            result.append(schemas.PendingMemberOut(
                user_id=user.id, name=user.name, email=user.email, avatar_url=user.avatar_url
            ))
    return result


@router.post("/{channel_id}/approve/{user_id}")
def approve_member(channel_id: str, user_id: str, db: Session = Depends(get_db)):
    membership = db.query(models.ChannelMember).filter_by(channel_id=channel_id, user_id=user_id).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    membership.status = "approved"
    db.commit()
    return {"message": "Membre approuvé"}


@router.post("/{channel_id}/reject/{user_id}")
def reject_member(channel_id: str, user_id: str, db: Session = Depends(get_db)):
    membership = db.query(models.ChannelMember).filter_by(channel_id=channel_id, user_id=user_id).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    db.delete(membership)
    db.commit()
    return {"message": "Demande rejetée"}

@router.get("/{channel_id}/ranking", response_model=list[schemas.RankingEntry])
def get_channel_ranking(channel_id: str, db: Session = Depends(get_db)):
    memberships = db.query(models.ChannelMember).filter_by(channel_id=channel_id, status="approved").all()
    ranking = []
    for m in memberships:
        user = db.query(models.User).filter(models.User.id == m.user_id).first()
        if not user:
            continue
        verified_count = db.query(models.Post).filter_by(
            channel_id=channel_id, user_id=m.user_id, ai_verified=True
        ).count()
        ranking.append(schemas.RankingEntry(
            user_id=user.id, name=user.name, avatar_url=user.avatar_url,
            verified_count=verified_count,
        ))
    ranking.sort(key=lambda r: r.verified_count, reverse=True)
    return ranking

@router.get("/recommended/{user_id}", response_model=list[schemas.ChannelOut])
def get_recommended_channels(user_id: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    my_channel_ids = [
        m.channel_id for m in db.query(models.ChannelMember).filter_by(user_id=user_id).all()
    ]

    all_channels = db.query(models.Channel).filter(
        ~models.Channel.id.in_(my_channel_ids) if my_channel_ids else True
    ).all()

    user_objectives = set(
        o.strip().lower() for o in (user.objectives or "").split(",") if o.strip()
    )

    def is_match(channel):
        if not channel.goal_topic or not user_objectives:
            return False
        return channel.goal_topic.strip().lower() in user_objectives

    matched = [c for c in all_channels if is_match(c)]
    others = [c for c in all_channels if not is_match(c)]

    ordered = matched + others
    return [with_member_count(c, db) for c in ordered]

@router.get("/{channel_id}/my-status/{user_id}")
def get_my_membership_status(channel_id: str, user_id: str, db: Session = Depends(get_db)):
    channel = db.query(models.Channel).filter(models.Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel introuvable")

    if channel.owner_id == user_id:
        return {"status": "owner"}

    membership = db.query(models.ChannelMember).filter_by(
        channel_id=channel_id, user_id=user_id
    ).first()

    if not membership:
        return {"status": "none"}
    return {"status": membership.status}
    