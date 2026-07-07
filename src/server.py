import os
import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.config.settings import Settings
from src.config.security import SecurityConfig
from src.database import init_db, MemoryModel, SessionLocal
from src.agents.router import RouterAgent
from src.agents.base import BaseAgent
from src.brain.dual import DualBrain
from src.utils.tokens import TokenManager
from src.utils.learner import Learner

app = FastAPI(
    title="Super Brain v2",
    version="2.0.0",
    debug=Settings.DEBUG
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
init_db()

# Initialize components
router_agent = RouterAgent()
dual_brain = DualBrain()
token_manager = TokenManager()

@app.on_event("startup")
async def startup_event():
    if not os.path.exists("data"):
        os.makedirs("data")
    print("Super Brain v2 started")

@app.on_event("shutdown")
async def shutdown_event():
    print("Super Brain v2 shutting down")

@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    prompt = body.get("prompt", "")
    
    # Route through security
    req_dict = {
        "url": request.url.path,
        "ip": request.client.host,
        "method": request.method,
        "body": body
    }
    
    route_result = await router_agent.execute(req_dict)
    if isinstance(route_result, tuple) and len(route_result) == 2:
        result, status_code = route_result
        if status_code != 200:
            raise HTTPException(status_code=status_code, detail=result.get("error", "Error"))
    
    # Process through brain
    response = dual_brain.process(prompt)
    
    # Store in memory
    db = SessionLocal()
    try:
        memory_entry = MemoryModel(key=prompt, value=response)
        db.add(memory_entry)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
    
    return {"response": response}

@app.post("/api/train")
async def train():
    dataset_path = "brain_dataset.jsonl"
    if os.path.exists(dataset_path):
        Learner.train(dataset_path, dual_brain)
        return {"status": "Training complete"}
    return {"error": "Dataset not found"}, 404

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.server:app", host="0.0.0.0", port=8000, reload=Settings.DEBUG)