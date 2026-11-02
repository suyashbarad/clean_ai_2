import os
from typing import Dict, Any, List
from backend.config import SARVAM_API_KEY
from backend.database import get_connection

def query_cleanbot(user_message: str, user_role: str = "citizen", history: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    CleanBot AI Cleanliness Assistant powered by Sarvam AI (sarvam-105b-conversations).
    Enforces role-based awareness and incorporates real database state.
    """
    # 1. Fetch live system context from DB
    conn = get_connection()
    c = conn.cursor()

    total_complaints = c.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
    resolved_complaints = c.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Resolved'").fetchone()[0]
    pending_complaints = c.execute("SELECT COUNT(*) FROM complaints WHERE status NOT IN ('Resolved', 'Rejected')").fetchone()[0]
    total_bins = c.execute("SELECT COUNT(*) FROM waste_bins").fetchone()[0]

    top_wards = c.execute("""
        SELECT ward_name, COUNT(*) as cnt
        FROM complaints
        GROUP BY ward_name
        ORDER BY cnt DESC
        LIMIT 3
    """).fetchall()
    top_wards_str = ", ".join([f"{w['ward_name']} ({w['cnt']} complaints)" for w in top_wards])

    conn.close()

    resolution_rate = round((resolved_complaints / total_complaints * 100), 1) if total_complaints > 0 else 0

    system_prompt = f"""You are CleanBot, the intelligent AI Cleanliness Assistant for CleanGreen AI 2.0 (Pune Smart City Waste Management & Urban Cleanliness Intelligence Platform).
Current live Pune Municipal metrics:
- Total registered waste complaints: {total_complaints}
- Currently pending complaints: {pending_complaints}
- Successfully resolved complaints: {resolved_complaints} (Resolution Rate: {resolution_rate}%)
- Monitored smart & community dustbins: {total_bins}
- Top reported areas: {top_wards_str}
- Standard civic partner rewards: MahaMetro Pune (₹25 Metro Voucher), PMPML Bus Pass (₹50 Pass Rebate), PMC Property Tax Rebate (5% rebate voucher).

User Role: {user_role.upper()}
Guidelines:
1. If the user is a citizen: Help with waste segregation rules (wet vs dry vs hazardous vs e-waste), explain how to submit photo complaints, track complaints, earn Green Credits, and locate public dustbins.
2. If the user is an administrator: Provide analytical summaries, explain hotspot predictions (DBSCAN), recommend bin placement (MCLP), and summarize ward cleanliness performance.
3. Be helpful, concise, courteous, and authoritative on Indian municipal waste management standards (SWM Rules 2016)."""

    # Check if Sarvam API key is available
    if not SARVAM_API_KEY:
        return {
            "reply": f"CleanBot is online. (Note: SARVAM_API_KEY is not configured, running in local knowledge mode).\n\n"
                     f"City Summary: {total_complaints} complaints registered across Pune ({resolution_rate}% resolved). "
                     f"For waste segregation: Green bin for wet/organic, Blue bin for dry/recyclable, Red for domestic hazardous.",
            "model": "rule-based-fallback"
        }

    try:
        from sarvamai import SarvamAI
        client = SarvamAI(api_subscription_key=SARVAM_API_KEY)

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for turn in history[-4:]:
                messages.append({"role": turn.get("role", "user"), "content": turn.get("content", "")})

        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions(
            model="sarvam-105b-conversations",
            messages=messages
        )
        reply = response.choices[0].message.content
        return {
            "reply": reply,
            "model": "sarvam-105b-conversations"
        }
    except Exception as e:
        # Graceful fallback response
        print(f"Sarvam AI completion error: {e}")
        return {
            "reply": f"CleanBot Assistant Response:\n\nBased on Pune Municipal data, we have {total_complaints} logged complaints with a {resolution_rate}% resolution rate. Top hotspot sectors are {top_wards_str}. For proper disposal, ensure organic waste is separated from plastics and recyclables.",
            "model": "local-insights-fallback"
        }
