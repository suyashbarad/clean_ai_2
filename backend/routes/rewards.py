import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Form, HTTPException
from backend.database import get_connection

router = APIRouter(prefix="/api/rewards", tags=["Rewards"])

CATALOG = [
    {
        "id": "rew_metro",
        "partner": "MahaMetro Pune",
        "title": "₹25 Pune Metro Fare Voucher",
        "benefit": "1 Free Journey or ₹25 Smart Card Topup",
        "cost": 100,
        "instructions": "Redeemable at Vanaz, Garware College, Shivajinagar, Civil Court, or Swargate Metro stations.",
        "badge_color": "emerald"
    },
    {
        "id": "rew_pmpml",
        "partner": "PMPML Pune Bus",
        "title": "₹50 PMPML Bus Pass Rebate",
        "benefit": "₹50 Instant Discount on Monthly Bus Pass",
        "cost": 150,
        "instructions": "Present code at any PMPML Depot pass counter (Swargate, Kothrud Depot, Pune Station, Katraj).",
        "badge_color": "blue"
    },
    {
        "id": "rew_pmc_tax",
        "partner": "Pune Municipal Corporation",
        "title": "PMC Green Citizen Certificate & Tax Rebate",
        "benefit": "5% Property Tax Rebate Voucher Demonstration",
        "cost": 250,
        "instructions": "Demonstration incentive for top eco-conscious citizens under Swachh Pune 2026.",
        "badge_color": "purple"
    },
    {
        "id": "rew_cafe",
        "partner": "MIT-WPU Green Cafeteria",
        "title": "₹30 Campus Eco-Snack Coupon",
        "benefit": "₹30 Discount on Organic Juice or Fresh Salad",
        "cost": 60,
        "instructions": "Valid at all MIT-WPU Kothrud Campus food counters.",
        "badge_color": "amber"
    }
]

@router.get("/catalog")
def get_catalog():
    return {"catalog": CATALOG}

@router.get("/user/{user_id}")
def get_user_rewards(user_id: str):
    conn = get_connection()
    c = conn.cursor()

    user = c.execute("SELECT id, name, credits_balance FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    transactions = c.execute("""
        SELECT * FROM reward_transactions
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 20
    """, (user_id,)).fetchall()

    vouchers = c.execute("""
        SELECT * FROM vouchers
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,)).fetchall()

    conn.close()

    return {
        "user": dict(user),
        "credits_balance": user["credits_balance"],
        "transactions": [dict(t) for t in transactions],
        "vouchers": [dict(v) for v in vouchers]
    }

@router.get("/leaderboard")
def get_leaderboard():
    conn = get_connection()
    c = conn.cursor()
    # Dynamic mock leaderboard merged with actual user
    leaders = [
        {"rank": 1, "name": "Pooja Kulkarni", "area": "Kothrud", "credits": 820, "reports": 16, "badge": "Eco Champion"},
        {"rank": 2, "name": "Rohit Joshi", "area": "Shivajinagar", "credits": 640, "reports": 12, "badge": "Clean Warrior"},
        {"rank": 3, "name": "Aarav Sharma (You)", "area": "MIT-WPU Kothrud", "credits": 300, "reports": 6, "badge": "Green Guardian"},
        {"rank": 4, "name": "Ananya Sen", "area": "Aundh", "credits": 280, "reports": 5, "badge": "Civic Contributor"},
        {"rank": 5, "name": "Vikram Shinde", "area": "Viman Nagar", "credits": 210, "reports": 4, "badge": "Waste Scout"}
    ]
    # Update Aarav's balance from DB
    u1 = c.execute("SELECT credits_balance FROM users WHERE id = 'u1'").fetchone()
    if u1:
        leaders[2]["credits"] = u1["credits_balance"]
    conn.close()

    return {"leaderboard": leaders}

@router.post("/redeem")
def redeem_voucher(user_id: str = Form("u1"), reward_id: str = Form(...)):
    target_reward = next((r for r in CATALOG if r["id"] == reward_id), None)
    if not target_reward:
        raise HTTPException(status_code=404, detail="Reward not found in catalog")

    conn = get_connection()
    c = conn.cursor()

    user = c.execute("SELECT credits_balance, name FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    if user["credits_balance"] < target_reward["cost"]:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Need {target_reward['cost']} PTS, you have {user['credits_balance']} PTS."
        )

    # Deduct credits
    c.execute("UPDATE users SET credits_balance = credits_balance - ? WHERE id = ?", (target_reward["cost"], user_id))

    voucher_id = f"VCH-{uuid.uuid4().hex[:6].upper()}"
    code = f"PUN-{target_reward['partner'][:4].upper()}-{uuid.uuid4().hex[:5].upper()}"
    expires = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S")

    # Add voucher
    c.execute("""
        INSERT INTO vouchers (
            id, user_id, code, partner_name, title, benefit, cost_credits, status, qr_code_data, expires_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Active', ?, ?)
    """, (
        voucher_id, user_id, code, target_reward["partner"], target_reward["title"],
        target_reward["benefit"], target_reward["cost"], f"AUTH-PMC-VAL:{code}", expires
    ))

    # Add transaction
    c.execute("""
        INSERT INTO reward_transactions (id, user_id, amount, transaction_type, reason)
        VALUES (?, ?, ?, 'DEBIT', ?)
    """, (f"TXN-{uuid.uuid4().hex[:6].upper()}", user_id, target_reward["cost"], f"Redeemed: {target_reward['title']}"))

    # Add Notification
    c.execute("""
        INSERT INTO notifications (id, user_id, title, message, notification_type)
        VALUES (?, ?, 'Voucher Generated!', ?, 'reward')
    """, (f"N-{uuid.uuid4().hex[:6].upper()}", user_id, f"Successfully redeemed {target_reward['title']}. Code: {code}"))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "voucher_id": voucher_id,
        "voucher_code": code,
        "reward": target_reward,
        "expires_at": expires,
        "message": f"Successfully redeemed {target_reward['title']}!"
    }
