import time
from fastapi import APIRouter, Header, HTTPException
from app.models import ChatCompletionRequest, StandardResponse
from app.classifier import predict_complexity_tier
from app.database import log_request_to_db  # This is a synchronous DB function

router = APIRouter(prefix="/v1", tags=["Inference"])

@router.post("/chat/completions", response_model=StandardResponse)
async def chat_completions(
    body: ChatCompletionRequest,
    x_team_id: str = Header(..., alias="X-Team-Id")
):
    """
    Core Chat Completion router endpoint.
    Ingests payloads, maps cognitive prompt complexity via Scikit-Learn pipelines, 
    and commits multi-tenant analytics logs natively into the local SQLite engine layer.
    """
    # 1. Run input parsing and isolate the latest message content block
    user_content = body.messages[-1].content if body.messages else ""
    
    # 2. Execute Scikit-Learn routing optimization classification tier logic
    tier = predict_complexity_tier(user_content)
    
    # Track performance milestones for infrastructural metric dashboards
    start_time = time.time()
    
    # 3. Resolve downstream model assignments based on complexity prediction evaluations
    if tier == 0:
        model_assigned = "llama3.2"
        output_text = "Infrastructure response simulated payload from Tier 0 cluster."
        prompt_tk, comp_tk = 10, 15
    elif tier == 1:
        model_assigned = "gemini-flash"
        output_text = "Advanced logical processing handled by Tier 1 computing framework."
        prompt_tk, comp_tk = 20, 45
    else:
        model_assigned = "gpt-4o"
        output_text = "Deep analytical orchestration executed by Tier 2 heavy compute tier."
        prompt_tk, comp_tk = 40, 90

    latency = (time.time() - start_time) * 1000
    total_tk = prompt_tk + comp_tk
    cost = total_tk * 0.000002

    # 4. Invoke synchronous SQLite database execution natively without an illegal 'await'
    log_request_to_db(
        team_id=x_team_id,
        model_used=model_assigned,
        latency_ms=latency,
        prompt_tokens=prompt_tk,
        completion_tokens=comp_tk,
        total_tokens=total_tk,
        cost_usd=cost
    )

    # 5. Marshal the structured object back to the client interface layer
    return StandardResponse(
        model_used=model_assigned,
        latency_ms=latency,
        prompt_tokens=prompt_tk,
        completion_tokens=comp_tk,
        total_tokens=total_tk,
        cost_usd=cost,
        output_text=output_text
    )