import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .config import settings
from .api import auth, problems, submissions, ai, discussion, websocket_router
from .services.websocket import websocket_manager
from .database import engine, Base

app = FastAPI(
    title="Submittery v2 API",
    description="AI-powered distributed online judge and real-time pair programming platform.",
    version="2.0"
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event: Connect to Redis Pub/Sub listener
@app.on_event("startup")
async def startup_event():
    # Attempt to build database tables on startup if they don't exist
    try:
        print("[*] Ensuring database tables are created...")
        Base.metadata.create_all(bind=engine)
        
        # Initialize RAG pgvector tables and embed-once knowledge base
        from .services.rag_service import rag_service
        from .database import SessionLocal
        db = SessionLocal()
        try:
            rag_service.seed_problem_knowledge_if_needed(db)
        finally:
            db.close()
    except Exception as e:
        print(f"[!] Error auto-creating database tables / RAG: {e}")
        
    await websocket_manager.start_redis_listener()

# Shutdown event: Cancel background tasks
@app.on_event("shutdown")
async def shutdown_event():
    await websocket_manager.stop_redis_listener()

# Include REST API Routers
app.include_router(auth.router, prefix="/api")
app.include_router(problems.router, prefix="/api")
app.include_router(submissions.router, prefix="/api")
app.include_router(discussion.router, prefix="/api")
app.include_router(ai.router, prefix="/api")

# Include WebSocket Router
app.include_router(websocket_router.router, prefix="/api")

# Serve Frontend static files
# Make sure static directory exists
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)

# Mount static files to serve the SPA UI
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

@app.get("/health")
def health_check():
    return {"status": "ok", "environment": settings.ENV}
