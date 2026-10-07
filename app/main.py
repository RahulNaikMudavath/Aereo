from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.config import APP_TITLE, APP_DESCRIPTION, APP_VERSION
from app.database import Base, engine
from app.routers import jobs, certificates

# Create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(jobs.router)
app.include_router(certificates.router)


@app.get("/", response_class=HTMLResponse, tags=["Health"])
def home():
    """
    Landing page and service health status.
    """
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Bulk Certificate Generator</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
            .card { background: #1e293b; border-radius: 12px; padding: 40px; max-width: 600px; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4); border: 1px solid #334155; }
            h1 { color: #38bdf8; margin-top: 0; font-size: 26px; }
            p { color: #94a3b8; line-height: 1.6; }
            .status { display: inline-block; background: #065f46; color: #34d399; padding: 4px 12px; border-radius: 9999px; font-weight: 600; font-size: 13px; margin-bottom: 20px; }
            .links { margin-top: 24px; display: flex; gap: 12px; }
            .btn { background: #2563eb; color: #fff; text-decoration: none; padding: 10px 18px; border-radius: 6px; font-weight: 500; font-size: 14px; transition: background 0.2s; }
            .btn:hover { background: #1d4ed8; }
            .btn-secondary { background: #334155; }
            .btn-secondary:hover { background: #475569; }
        </style>
    </head>
    <body>
        <div class="card">
            <span class="status">● System Operational</span>
            <h1>Bulk Certificate Generator API</h1>
            <p>A production-ready asynchronous backend service for bulk certificate issuance with failure isolation, status tracking, and single/ZIP download retrieval.</p>
            <div class="links">
                <a class="btn" href="/docs">Interactive API Docs (Swagger)</a>
                <a class="btn btn-secondary" href="/redoc">ReDoc Documentation</a>
            </div>
        </div>
    </body>
    </html>
    """


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": APP_TITLE,
        "version": APP_VERSION
    }
