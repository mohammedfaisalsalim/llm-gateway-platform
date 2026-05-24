from pydantic import BaseModel
from typing import Optional

class StandardResponse(BaseModel):
    output_text: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    cost_usd: float
    model_used: str