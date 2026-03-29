# AgentLedger 🔐

> On-chain reputation and trust scoring system for AI agents

## Problem

AI agents are executing real-world tasks autonomously — trading, automating workflows, making decisions — but there is **no way to verify if an agent is trustworthy**. No reputation system, no task history, no accountability layer.



## Solution

AgentLedger gives every AI agent:
- An **on-chain identity** (ERC-8004 on Base)
- A **tamper-proof task log** — every outcome recorded
- A **transparent trust score** — computed from verified task history
- A **queryable reputation API** — other agents check before delegating

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/agents/register` | Register a new AI agent |
| GET | `/agents` | List all agents with trust scores |
| GET | `/agents/{id}` | Get agent profile + full task history |
| POST | `/tasks/log` | Log a task outcome |
| GET | `/trust/{agent_id}` | Query trust score before delegating |
| GET | `/tasks` | List all logged tasks |

## Quick Start

```bash
pip install -r requirements.txt
uvicorn main:app --reload
Visit http://localhost:8000/docs for interactive API docs.
Demo Flow
# 1. Register an agent
curl -X POST http://localhost:8000/agents/register \
  -H "Content-Type: application/json" \
  -d '{"name":"TradingBot","description":"Autonomous DeFi trading agent","owner":"0xYourWallet"}'

# 2. Log a successful task
curl -X POST http://localhost:8000/tasks/log \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"AGENT_ID","task_description":"Execute ETH swap","success":true,"result_summary":"Swapped 1 ETH for 2150 USDC"}'

# 3. Query trust score
curl http://localhost:8000/trust/AGENT_ID
Tech Stack
Python + FastAPI — REST API backend
ERC-8004 — On-chain agent identity standard (Base Mainnet)
Base Network — Ethereum L2 for agent registrations
Built For
The Synthesis Hackathon 2026 — AI + Ethereum infrastructure track
Tracks
Agents With Receipts — ERC-8004
Agent Services on Base
Student Founder's Bet
ERC-8183 Open Build
## Demo Note
This is a hackathon MVP. Data is stored in-memory for demo purposes.
Full persistence with on-chain storage planned for post-hackathon version.
ERC-8004 references are currently mocked — full Base mainnet integration
is the next development milestone.
