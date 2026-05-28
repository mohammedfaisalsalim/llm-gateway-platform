from pydantic import BaseModel, ConfigDict
from typing import List

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    messages: List[ChatMessage]

# MUST BE NAMED EXACTLY 'StandardResponse' TO MATCH app/providers.py IMPORTS
class StandardResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    model_used: str
    latency_ms: float
    total_tokens: int
    cost_usd: float
    output_text: str