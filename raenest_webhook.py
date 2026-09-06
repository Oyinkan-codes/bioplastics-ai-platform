import os
import sqlite3
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException, Header, status
from pydantic import BaseModel

app = FastAPI(
    title="BioMatX Raenest Webhook Listener",
    description="Processes multi-currency subscription payments and updates user tier permissions.",
    version="1.0.0"
)

# Configuration
DB_PATH = "bioplastics.db"
# Set this secret in your environment variables or Streamlit secrets
RAENEST_WEBHOOK_SECRET = os.getenv("RAENEST_WEBHOOK_SECRET", "raenest_sec_live_biomatx_98234")


def init_db():
    """Ensures the SQLite database and transactions table exist."""
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


# Initialize database schemas on startup
init_db()


def update_user_plan_in_db(email: str, plan: str, transaction_id: str, amount: float, currency: str):
    """Updates user plan status and records payment in SQLite."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Update or insert user plan
    cursor.execute("""
        INSERT INTO users (email, plan, updated_at) 
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(email) DO UPDATE SET 
            plan = excluded.plan,
            updated_at = CURRENT_TIMESTAMP
    """, (email, plan))

    # 2. Record transaction audit log
    cursor.execute("""
        INSERT OR IGNORE INTO transactions (user_email, transaction_id, amount, currency, plan, status)
        VALUES (?, ?, ?, ?, ?, 'completed')
    """, (email, transaction_id, amount, currency, plan))

    conn.commit()
    conn.close()


@app.get("/")
def health_check():
    """Health check endpoint to verify webhook service status."""
    return {"status": "online", "service": "BioMatX Raenest Webhook Processor"}


@app.post("/webhook/raenest", status_code=status.HTTP_200_OK)
async def handle_raenest_webhook(
    request: Request,
    x_raenest_signature: str = Header(None)
):
    """
    Receives Raenest payment notifications.
    Validates webhook signature and upgrades user account to Pro or Enterprise.
    """
    # Verify presence of signature header
    if not x_raenest_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing x-raenest-signature header"
        )

    # Simple secret verification (Replace with HMAC SHA256 in production)
    if x_raenest_signature != RAENEST_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook signature"
        )

    try:
        payload: Dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )

    event_type = payload.get("event")
    data = payload.get("data", {})

    # Process successful payment events
    if event_type == "payment.success":
        customer_email = data.get("customer", {}).get("email")
        transaction_id = data.get("reference")
        amount = float(data.get("amount", 0.0))
        currency = data.get("currency", "USD")
        
        # Determine plan based on amount paid
        # e.g., $99/mo = Pro Tier, $499/mo = Enterprise / SaaS Tier
        if amount >= 499.0:
            assigned_plan = "enterprise"
        elif amount >= 99.0:
            assigned_plan = "pro"
        else:
            assigned_plan = "free"

        if customer_email and transaction_id:
            update_user_plan_in_db(
                email=customer_email,
                plan=assigned_plan,
                transaction_id=transaction_id,
                amount=amount,
                currency=currency
            )
            return {
                "status": "success",
                "message": f"User {customer_email} upgraded to {assigned_plan.upper()} tier."
            }

    return {"status": "ignored", "message": f"Event type '{event_type}' handled without action."}


if __name__ == "__main__":
    import uvicorn
    # Runs the webhook server locally on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
