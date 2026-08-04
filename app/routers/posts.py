import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas

router = APIRouter(prefix="/posts", tags=["posts"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/{user_id}/upload", response_model=schemas.PostOut)
async def create_post_with_photo(
    user_id: str,
    channel_id: str = Form(...),
    habit_id: str | None = Form(None),
    caption: str | None = Form(None),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    membership = db.query(models.ChannelMember).filter_by(
        user_id=user_id, channel_id=channel_id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas membre de ce channel")

    # Sauvegarde du fichier
    ext = os.path.splitext(photo.filename)[1] or ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    contents = await photo.read()
    with open(filepath, "wb") as f:
        f.write(contents)

    # Déterminer la catégorie de l'habitude (pour la vérification IA)
    category = None
    if habit_id:
        habit = db.query(models.Habit).filter(models.Habit.id == habit_id).first()
        if habit:
            category = habit.category

    # Vérification IA avec CLIP
    ai_verified = False
    ai_score = None
    # CLIP désactivé temporairement (hosting gratuit, RAM limitée)
    # Pour réactiver: décommenter les lignes ci-dessous
    # try:
    #     from ml.photo_verify import verify_photo
    #     ai_verified, ai_score = verify_photo(filepath, category)
    # except Exception as e:
    #     print(f"Erreur de vérification IA: {e}")

    new_post = models.Post(
        user_id=user_id,
        channel_id=channel_id,
        habit_id=habit_id if habit_id else None,
        photo_url=f"/uploads/{filename}",
        caption=caption,
        ai_verified=ai_verified,
        ai_confidence_score=ai_score,
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post


@router.post("/{user_id}", response_model=schemas.PostOut)
def create_post(user_id: str, post: schemas.PostCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    membership = db.query(models.ChannelMember).filter_by(
        user_id=user_id, channel_id=str(post.channel_id)
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas membre de ce channel")
    new_post = models.Post(
        user_id=user_id,
        channel_id=post.channel_id,
        habit_id=post.habit_id,
        photo_url=post.photo_url,
        caption=post.caption,
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post


@router.get("/channel/{channel_id}", response_model=list[schemas.PostOut])
def list_posts_by_channel(channel_id: str, db: Session = Depends(get_db)):
    return db.query(models.Post).filter(models.Post.channel_id == channel_id).order_by(
        models.Post.created_at.desc()
    ).all()

REACTION_EMOJIS = ["👏", "❤️", "🔥"]


def build_full_post(post, db):
    user = db.query(models.User).filter(models.User.id == post.user_id).first()
    habit = db.query(models.Habit).filter(models.Habit.id == post.habit_id).first() if post.habit_id else None

    reactions_out = []
    for emoji in REACTION_EMOJIS:
        count = db.query(models.PostReaction).filter_by(post_id=post.id, emoji=emoji).count()
        reactions_out.append(schemas.ReactionOut(emoji=emoji, count=count, reacted_by_me=False))

    comment_count = db.query(models.PostComment).filter_by(post_id=post.id).count()

    return schemas.PostOutFull(
        id=post.id,
        user_id=post.user_id,
        user_name=user.name if user else "Utilisateur",
        user_avatar=user.avatar_url if user else None,
        habit_id=post.habit_id,
        habit_title=habit.title if habit else None,
        habit_streak=habit.streak_count if habit else None,
        photo_url=post.photo_url,
        caption=post.caption,
        ai_verified=post.ai_verified,
        ai_confidence_score=post.ai_confidence_score,
        created_at=post.created_at,
        reactions=reactions_out,
        comment_count=comment_count,
    )


@router.get("/channel/{channel_id}/full", response_model=list[schemas.PostOutFull])
def list_posts_full(channel_id: str, db: Session = Depends(get_db)):
    posts = db.query(models.Post).filter(models.Post.channel_id == channel_id).order_by(
        models.Post.created_at.desc()
    ).all()
    return [build_full_post(p, db) for p in posts]


@router.post("/{post_id}/react/{user_id}")
def react_to_post(post_id: str, user_id: str, reaction: schemas.ReactionCreate, db: Session = Depends(get_db)):
    existing = db.query(models.PostReaction).filter_by(
        post_id=post_id, user_id=user_id, emoji=reaction.emoji
    ).first()
    if existing:
        db.delete(existing)
        db.commit()
        return {"message": "Réaction retirée"}
    new_reaction = models.PostReaction(post_id=post_id, user_id=user_id, emoji=reaction.emoji)
    db.add(new_reaction)
    db.commit()
    return {"message": "Réaction ajoutée"}


@router.get("/{post_id}/comments", response_model=list[schemas.CommentOut])
def list_comments(post_id: str, db: Session = Depends(get_db)):
    comments = db.query(models.PostComment).filter_by(post_id=post_id).order_by(
        models.PostComment.created_at.asc()
    ).all()
    result = []
    for c in comments:
        user = db.query(models.User).filter(models.User.id == c.user_id).first()
        result.append(schemas.CommentOut(
            id=c.id, user_id=c.user_id,
            user_name=user.name if user else "Utilisateur",
            user_avatar=user.avatar_url if user else None,
            text=c.text, created_at=c.created_at,
        ))
    return result


@router.post("/{post_id}/comments/{user_id}", response_model=schemas.CommentOut)
def add_comment(post_id: str, user_id: str, comment: schemas.CommentCreate, db: Session = Depends(get_db)):
    new_comment = models.PostComment(post_id=post_id, user_id=user_id, text=comment.text)
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    return schemas.CommentOut(
        id=new_comment.id, user_id=user_id,
        user_name=user.name if user else "Utilisateur",
        user_avatar=user.avatar_url if user else None,
        text=new_comment.text, created_at=new_comment.created_at,
    )


@router.delete("/{post_id}")
def delete_post(post_id: str, db: Session = Depends(get_db)):
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post introuvable")
    db.delete(post)
    db.commit()
    return {"message": "Post supprimé"}


@router.delete("/comments/{comment_id}")
def delete_comment(comment_id: str, db: Session = Depends(get_db)):
    comment = db.query(models.PostComment).filter(models.PostComment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Commentaire introuvable")
    db.delete(comment)
    db.commit()
    return {"message": "Commentaire supprimé"}