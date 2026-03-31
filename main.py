from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
import time
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from web3 import Web3

app = FastAPI(
    title="AgentLedger",
    description="On-chain reputation and trust scoring system for AI agents",
    version="2.0.0"
)

# ------------------ DATABASE ------------------

def get_db():
    DATABASE_URL = os.getenv("DATABASE_URL")
    print("DB URL:", os.getenv("DATABASE_URL"))

    if not DATABASE_URL:
        raise Exception("DATABASE_URL not set in environment")

    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        raise Exception(f"Database connection failed: {str(e)}")


# ------------------ WEB3 ------------------

w3 = Web3(Web3.HTTPProvider("https://sepolia.base.org"))
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
WALLET_ADDRESS = "0x3e8558996272732Ec59682641317D45ECe99465f"

ERC8004_ABI = [
    {
        "inputs": [
            {"name": "agentId", "type": "uint256"},
            {"name": "agentURI", "type": "string"}
        ],
        "name": "register",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

ERC8004_ADDRESS = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"


def register_on_chain(agent_name: str) -> str:
    try:
        if not PRIVATE_KEY:
            return f"mock_{agent_name[:6]}"

        contract = w3.eth.contract(
            address=Web3.to_checksum_address(ERC8004_ADDRESS),
            abi=ERC8004_ABI
        )

        nonce = w3.eth.get_transaction_count(WALLET_ADDRESS)
        agent_id = int(time.time())

        tx = contract.functions.register(
            agent_id,
            f"Agent:{agent_name}"
        ).build_transaction({
            "from": WALLET_ADDRESS,
            "nonce": nonce,
            "gas": 200000,
            "gasPrice": w3.to_wei("0.001", "gwei"),
            "chainId": 84532
        })

        signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)

        return f"https://sepolia.basescan.org/tx/{tx_hash.hex()}"

    except Exception as e:
        return f"fallback_{str(e)[:20]}"


# ------------------ MODELS ------------------

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


# ------------------ LOGIC ------------------

def calculate_trust_score(agent_id: str) -> float:
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT success FROM tasks WHERE agent_id = %s", (agent_id,))
    tasks = cur.fetchall()

    conn.close()

    if not tasks:
        return 0.0

    success_count = sum(1 for t in tasks if t["success"])
    return round((success_count / len(tasks)) * 100, 2)


def get_agent_tasks(agent_id: str):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM tasks WHERE agent_id = %s", (agent_id,))
    tasks = cur.fetchall()

    conn.close()
    return tasks


# ------------------ ROUTES ------------------

@app.get("/")
def root():
    return {"status": "AgentLedger running"}


@app.post("/agents/register")
def register_agent(data: AgentRegister):
    agent_id = str(uuid.uuid4())[:8]
    on_chain_ref = register_on_chain(data.name)

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO agents VALUES (%s, %s, %s, %s, %s, %s)",
        (agent_id, data.name, data.description, data.owner, int(time.time()), on_chain_ref)
    )

    conn.commit()
    conn.close()

    return {
        "agent_id": agent_id,
        "on_chain_ref": on_chain_ref
    }


@app.get("/agents")
def list_agents():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM agents")
    agents = cur.fetchall()

    conn.close()

    for agent in agents:
        agent["trust_score"] = calculate_trust_score(agent["id"])

    return {"agents": agents}


@app.post("/tasks/log")
def log_task(data: TaskLog):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id FROM agents WHERE id = %s", (data.agent_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Agent not found")

    task_id = str(uuid.uuid4())[:8]

    cur.execute(
        "INSERT INTO tasks VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (
            task_id,
            data.agent_id,
            data.task_description,
            data.success,
            data.result_summary,
            data.verifier,
            int(time.time()),
            f"task_{task_id}"
        )
    )

    conn.commit()
    conn.close()

    return {
        "task_id": task_id,
        "trust_score": calculate_trust_score(data.agent_id)
    }


@app.get("/trust/{agent_id}")
def get_trust(agent_id: str):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM agents WHERE id = %s", (agent_id,))
    agent = cur.fetchone()

    conn.close()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    score = calculate_trust_score(agent_id)

    return {
        "agent_id": agent_id,
        "trust_score": score,
        "rating": "HIGH" if score >= 80 else "LOW"
    }
