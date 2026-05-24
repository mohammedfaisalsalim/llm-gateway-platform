from pydantic import BaseModel, Field
from typing import List, Optional

class ChatMessage(BaseModel):
    role: str = Field(..., description="e.g., 'system', 'user', 'assistant'")
    content: str

class ChatCompletionRequest(BaseModel):
    model: Optional[str] = "auto"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7

class StandardResponse(BaseModel):
    output_text: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    cost_usd: float
    model_used: str