from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class ChatMessage(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    messages: List[ChatMessage]

class StandardResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    model_used: str
    latency_ms: float
    prompt_tokens: int       # Added to resolve critical schema crash validation
    completion_tokens: int   # Added to resolve critical schema crash validation
    total_tokens: int
    cost_usd: float
    output_text: str