from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, apply_sqlite_migrations, engine
from app.routers import auth, media, projects

Base.metadata.create_all(bind=engine)
apply_sqlite_migrations()

app = FastAPI(title="Acceptance Model Pipeline")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(media.router)


@app.get("/health")
def health():
    return {"status": "ok"}
