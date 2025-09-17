from fastapi import FastAPI
from datetime import datetime

app = FastAPI(title="News API")

@app.get("/api/health")
def health():
    return {"ok": True, "ts": datetime.utcnow().isoformat()}

@app.get("/api/news")
def news():
    return {"items": [], "updated_at": datetime.utcnow().isoformat()}
