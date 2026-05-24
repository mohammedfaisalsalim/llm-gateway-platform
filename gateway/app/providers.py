import time
import os
import asyncio
import ollama
import google.generativeai as genai
from fastapi import HTTPException
from app.models import StandardResponse

# Retrieve the API key from environment variables safely
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

async def send_request(prompt: str, provider: str, model_id: str, cost_per_input: float, cost_per_output: float) -> StandardResponse:
    start_time = time.time()
    output_text, p_tokens, c_tokens = "", 0, 0
    
    if provider == "ollama":
        try:
            # Offload heavy synchronous CPU/GPU local generation to worker threads
            res = await asyncio.to_thread(
                ollama.chat, 
                model=model_id, 
                messages=[{'role': 'user', 'content': prompt}]
            )
            output_text = res['message']['content']
            p_tokens = res.get('prompt_eval_count', len(prompt) // 4)
            c_tokens = res.get('eval_count', len(output_text) // 4)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Local Ollama Execution Failed: {str(e)}")
            
    elif provider == "gemini":
        if not GEMINI_KEY:
            raise HTTPException(status_code=501, detail="Gemini API key is missing from environment variables.")
        try:
            model = genai.GenerativeModel(model_id)
            res = await asyncio.to_thread(model.generate_content, prompt)
            output_text = res.text
            p_tokens, c_tokens = len(prompt) // 4, len(output_text) // 4
        except Exception as e: 
            raise HTTPException(status_code=502, detail=f"Gemini API Provider Error: {str(e)}")
            
    latency_ms = (time.time() - start_time) * 1000
    return StandardResponse(
        output_text=output_text, 
        prompt_tokens=p_tokens, 
        completion_tokens=c_tokens,
        total_tokens=p_tokens + c_tokens, 
        latency_ms=latency_ms,
        cost_usd=(p_tokens * cost_per_input) + (c_tokens * cost_per_output), 
        model_used=model_id
    )