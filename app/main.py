from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.firebase import init_firebase
from app.tasks.router import router as tasks_router
from app.ai.router import router as ai_router
from app.auth.router import router as auth_router

app = FastAPI(title="TaskMaster AI v5 — FastAPI + Firestore + GPT-5")

# Mengatur CORS agar semua origin bisa mengakses API
origins = ["*"]  # Semua origin diizinkan
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Menginisialisasi Firebase
init_firebase()

@app.get("/")
def root():
    return {"message": "TaskMaster AI v5 up & running."}

# Menyertakan router untuk auth, tasks, dan ai
app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(ai_router)
