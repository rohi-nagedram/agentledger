from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
import time
import os
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI(
    title="AgentLedger",
    description="On-chain reputation and trust scoring system for AI agents",
    version="1.0.0"
)

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    conn = psycopg2.connect(
        host="aws-0-ap-southeast-1.pooler.supabase.com",
        port=6543,
        database="postgres",
        user="postgres.lpwdmobxyfeebqzyrhkc",
        password="Indhu021733@"
    )
    return conn

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
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT success FROM tasks WHERE agent_id = %s", (agent_id,))
    agent_tasks = cur.fetchall()
    conn.close()
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
    on_chain_ref = f"eip155:8453:0x8004...{agent_id}"
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO agents (id, name, description, owner, registered_at, on_chain_ref) VALUES (%s, %s, %s, %s, %s, %s)",
        (agent_id, data.name, data.description, data.owner, int(time.time()), on_chain_ref)
    )
    conn.commit()
    conn.close()
    return {
        "agent_id": agent_id,
        "message": f"Agent '{data.name}' registered successfully",
        "on_chain_ref": on_chain_ref
    }

@app.get("/agents")
def list_agents():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM agents")
    all_agents = cur.fetchall()
    conn.close()
    result = []
    for agent in all_agents:
        result.append({
            **agent,
            "trust_score": calculate_trust_score(agent["id"]),
            "total_tasks": len([t for t in get_agent_tasks(agent["id"])])
        })
    return {"agents": result, "total": len(result)}

def get_agent_tasks(agent_id: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks WHERE agent_id = %s", (agent_id,))
    tasks = cur.fetchall()
    conn.close()
    return tasks

@app.get("/agents/{agent_id}")
def get_agent(agent_id: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM agents WHERE id = %s", (agent_id,))
    agent = cur.fetchone()
    conn.close()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent_tasks = get_agent_tasks(agent_id)
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
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM agents WHERE id = %s", (data.agent_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Agent not found. Register first.")
    task_id = str(uuid.uuid4())[:8]
    on_chain_ref = f"eip155:8453:0xtask...{task_id}"
    cur.execute(
        "INSERT INTO tasks (task_id, agent_id, task_description, success, result_summary, verifier, logged_at, on_chain_ref) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (task_id, data.agent_id, data.task_description, data.success, data.result_summary, data.verifier, int(time.time()), on_chain_ref)
    )
    conn.commit()
    conn.close()
    return {
        "task_id": task_id,
        "message": "Task logged successfully",
        "new_trust_score": calculate_trust_score(data.agent_id),
        "on_chain_ref": on_chain_ref
    }

@app.get("/trust/{agent_id}")
def get_trust_score(agent_id: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM agents WHERE id = %s", (agent_id,))
    agent = cur.fetchone()
    conn.close()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent_tasks = get_agent_tasks(agent_id)
    score = calculate_trust_score(agent_id)
    return {
        "agent_id": agent_id,
        "agent_name": agent["name"],
        "trust_score": score,
        "rating": "HIGH" if score >= 80 else "MEDIUM" if score >= 50 else "LOW",
        "total_tasks": len(agent_tasks),
        "successful_tasks": sum(1 for t in agent_tasks if t["success"]),
        "recommendation": "Safe to delegate" if score >= 80 else "Proceed with caution" if score >= 50 else "Not recommended"
    }

@app.get("/tasks")
def list_tasks():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks")
    all_tasks = cur.fetchall()
    conn.close()
    return {"tasks": all_tasks, "total": len(all_tasks)}
