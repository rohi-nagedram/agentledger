from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
import time

app = FastAPI(
    title="AgentLedger",
    description="On-chain reputation and trust scoring system for AI agents",
    version="1.0.0"
)

agents = {}
tasks = {}

class AgentRegister(BaseModel):
    name: str
    description: str
    owner: str

class TaskLog(BaseModel):
    agent_id: str
    task_description: str
    success: bool
    result_summary: str
    verifier: Optional[str] = "self"

def calculate_trust_score(agent_id: str) -> float:
    agent_tasks = [t for t in tasks.values() if t["agent_id"] == agent_id]
    if not agent_tasks:
        return 0.0
    successful = sum(1 for t in agent_tasks if t["success"])
    return round((successful / len(agent_tasks)) * 100, 2)

@app.get("/")
def root():
    return {
        "project": "AgentLedger",
        "tagline": "On-chain reputation and trust scoring for AI agents",
        "version": "1.0.0",
        "endpoints": ["/agents", "/agents/{id}", "/tasks", "/trust/{agent_id}"]
    }

@app.post("/agents/register")
def register_agent(data: AgentRegister):
    agent_id = str(uuid.uuid4())[:8]
    agents[agent_id] = {
        "id": agent_id,
        "name": data.name,
        "description": data.description,
        "owner": data.owner,
        "registered_at": int(time.time()),
        "on_chain_ref": f"eip155:8453:0x8004...{agent_id}"
    }
    return {
        "agent_id": agent_id,
        "message": f"Agent '{data.name}' registered successfully",
        "on_chain_ref": agents[agent_id]["on_chain_ref"]
    }

@app.get("/agents")
def list_agents():
    result = []
    for agent_id, agent in agents.items():
        result.append({
            **agent,
            "trust_score": calculate_trust_score(agent_id),
            "total_tasks": len([t for t in tasks.values() if t["agent_id"] == agent_id])
        })
    return {"agents": result, "total": len(result)}

@app.get("/agents/{agent_id}")
def get_agent(agent_id: str):
    if agent_id not in agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent = agents[agent_id]
    agent_tasks = [t for t in tasks.values() if t["agent_id"] == agent_id]
    return {
        **agent,
        "trust_score": calculate_trust_score(agent_id),
        "total_tasks": len(agent_tasks),
        "successful_tasks": sum(1 for t in agent_tasks if t["success"]),
        "failed_tasks": sum(1 for t in agent_tasks if not t["success"]),
        "task_history": agent_tasks
    }

@app.post("/tasks/log")
def log_task(data: TaskLog):
    if data.agent_id not in agents:
        raise HTTPException(status_code=404, detail="Agent not found. Register first.")
    task_id = str(uuid.uuid4())[:8]
    tasks[task_id] = {
        "task_id": task_id,
        "agent_id": data.agent_id,
        "task_description": data.task_description,
        "success": data.success,
        "result_summary": data.result_summary,
        "verifier": data.verifier,
        "logged_at": int(time.time()),
        "on_chain_ref": f"eip155:8453:0xtask...{task_id}"
    }
    new_score = calculate_trust_score(data.agent_id)
    return {
        "task_id": task_id,
        "message": "Task logged successfully",
        "new_trust_score": new_score,
        "on_chain_ref": tasks[task_id]["on_chain_ref"]
    }

@app.get("/trust/{agent_id}")
def get_trust_score(agent_id: str):
    if agent_id not in agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent_tasks = [t for t in tasks.values() if t["agent_id"] == agent_id]
    score = calculate_trust_score(agent_id)
    return {
        "agent_id": agent_id,
        "agent_name": agents[agent_id]["name"],
        "trust_score": score,
        "rating": "HIGH" if score >= 80 else "MEDIUM" if score >= 50 else "LOW",
        "total_tasks": len(agent_tasks),
        "successful_tasks": sum(1 for t in agent_tasks if t["success"]),
        "recommendation": "Safe to delegate" if score >= 80 else "Proceed with caution" if score >= 50 else "Not recommended"
    }

@app.get("/tasks")
def list_tasks():
    return {"tasks": list(tasks.values()), "total": len(tasks)}
