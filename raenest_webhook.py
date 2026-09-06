import os
import sqlite3
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException, Header, status

app = FastAPI(title="BioMatX Payment Processor", version="1.0.0")

DB_PATH = "bioplastics.db"
RAENEST_WEBHOOK_SECRET = os.getenv("RAENEST_WEBHOOK_SECRET", "raenest_sec_live_biomatx_98234")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            transaction_id TEXT UNIQUE NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            plan TEXT NOT NULL,
            status TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            plan TEXT DEFAULT 'free',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

def update_user_plan_in_db(email: str, plan: str, transaction_id: str, amount: float, currency: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (email, plan, updated_at) 
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(email) DO UPDATE SET plan = excluded.plan, updated_at = CURRENT_TIMESTAMP
    """, (email, plan))
    cursor.execute("""
        INSERT OR IGNORE INTO transactions (user_email, transaction_id, amount, currency, plan, status)
        VALUES (?, ?, ?, ?, ?, 'completed')
    """, (email, transaction_id, amount, currency, plan))
    conn.commit()
    conn.close()

@app.get("/")
def health():
    return {"status": "online"}

@app.post("/webhook/raenest", status_code=status.HTTP_200_OK)
async def handle_webhook(request: Request, x_raenest_signature: str = Header(None)):
    if x_raenest_signature != RAENEST_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload: Dict[str, Any] = await request.json()
    event_type = payload.get("event")
    data = payload.get("data", {})

    if event_type == "payment.success":
        customer_email = data.get("customer", {}).get("email")
        transaction_id = data.get("reference")
        amount = float(data.get("amount", 0.0))
        currency = data.get("currency", "USD")

        if amount >= 38.00:
            assigned_plan = "enterprise"
        elif amount >= 11.00:
            assigned_plan = "researcher"
        else:
            assigned_plan = "free"

        if customer_email and transaction_id:
            update_user_plan_in_db(customer_email, assigned_plan, transaction_id, amount, currency)
            return {"status": "success", "plan": assigned_plan}

    return {"status": "ignored"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
