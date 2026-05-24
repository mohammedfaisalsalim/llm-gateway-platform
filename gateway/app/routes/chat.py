from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import time

router = APIRouter()

class ChatMessage(BaseModel):
    role: str = Field(..., description="e.g., 'system', 'user', 'assistant'")
    content: str

class ChatCompletionRequest(BaseModel):
    model: Optional[str] = "auto"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7

@router.post("/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest):
    try:
        # Day 1-2 Skeleton Echo Implementation
        user_content = request.messages[-1].content if request.messages else ""
        
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"[SKELETON ECHO]: Received your prompt: '{user_content}'"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 10,
                "total_tokens": 20
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))