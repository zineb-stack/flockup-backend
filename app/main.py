from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from .database import Base, engine
from .routers import users, habits, tasks, channels, posts, predictions

Base.metadata.create_all(bind=engine)

app = FastAPI(title="FlockUp API")

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(habits.router)
app.include_router(tasks.router)
app.include_router(channels.router)
app.include_router(posts.router)
app.include_router(predictions.router)


@app.get("/")
def root():
    return {"message": "FlockUp API is running 🚀"}