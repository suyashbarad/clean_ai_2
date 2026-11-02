from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict
from backend.ml.cleanbot_service import query_cleanbot

router = APIRouter(prefix="/api/cleanbot", tags=["CleanBot"])

class ChatRequest(BaseModel):
    message: str
    role: Optional[str] = "citizen"
    history: Optional[List[Dict[str, str]]] = []

@router.post("/chat")
def cleanbot_chat(req: ChatRequest):
    result = query_cleanbot(user_message=req.message, user_role=req.role, history=req.history)
    return result
