from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routes.user import router as user_router
from routes.project import router as project_router
from routes.screenplay import router as screenplay_router
from routes.screenplay_scenes import router as screenplay_scenes_router
from routes.agent import router as agent_router
from routes.voice import router as voice_router
from routes.beatsheet import router as beatsheet_router
from db_conn.mongo.mongo import init_mongo, close_mongo

# Load environment variables
load_dotenv()

app = FastAPI(title="Production System API")

# Google Cloud Run deployment proof
import os
print("=" * 60)
print("APS Backend — Running on Google Cloud Run")
print(f"PORT: {os.getenv('PORT', '8000')}")
print(f"K_SERVICE: {os.getenv('K_SERVICE', 'local')}")
print(f"K_REVISION: {os.getenv('K_REVISION', 'local')}")
print("=" * 60)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://aps-frontend-iota.vercel.app"
    ],
    allow_origin_regex=r"https://.*\.run\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    init_mongo()
    print("MongoDB connection initialized")

@app.on_event("shutdown")
async def shutdown_event():
    close_mongo()
    print("MongoDB connection closed")

# Include routers
app.include_router(user_router)
app.include_router(project_router)
app.include_router(screenplay_router)
app.include_router(screenplay_scenes_router)
app.include_router(agent_router)
app.include_router(voice_router)
app.include_router(beatsheet_router)

@app.get("/")
async def root():
    return {"message": "Production System API is running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "platform": "Google Cloud Run",
        "service": os.getenv("K_SERVICE", "local"),
        "revision": os.getenv("K_REVISION", "local"),
    }
