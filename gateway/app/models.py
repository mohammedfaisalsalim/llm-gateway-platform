from pydantic import BaseModel, Field
from typing import Optional, List

class StandardResponse(BaseModel):
    output_text: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    cost_usd: float
    model_used: str

class ChatMessage(BaseModel):
    role: str = Field(..., description="'system', 'user', or 'assistant'")
    content: str

class ChatCompletionRequest(BaseModel):
    model: Optional[str] = "auto"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7