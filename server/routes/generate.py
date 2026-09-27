from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import os
import time
from collections import defaultdict
import logging
from auth import get_current_user, get_supabase_admin
import json

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("ai-app")

router = APIRouter()

class GenerateRequest(BaseModel):
    prompt: str

RATE_LIMIT = 20
RATE_WINDOW = 60
request_log = defaultdict(list)

FREE_MODELS = [
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "inclusionai/ling-3.0-flash-fin:free",
    "qwen/qwen3.8-27b:free",
    "google/gemma-4-26b-a4b-it:free",
]

def is_rate_limited(key: str) -> bool:
    now = time.time()
    request_log[key] = [t for t in request_log[key] if now - t < RATE_WINDOW]
    if len(request_log[key]) >= RATE_LIMIT:
        return True
    request_log[key].append(now)
    return False

@router.post("/generate")
async def generate(
    req: GenerateRequest,
    request: Request,
    user = Depends(get_current_user)
):
    client_ip = request.client.host
    user_id = user.id
    rate_key = f"{user_id}:{client_ip}"

    if is_rate_limited(rate_key):
        logger.warning(f"RATE LIMIT | user={user_id} | ip={client_ip}")
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a moment.")

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not set")

    last_error = None
    used_model = None
    text = None
    start_time = time.time()

    for model in FREE_MODELS:
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "http://localhost:8000",
                        "X-Title": "AI App",
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": req.prompt}],
                    },
                )

            if response.status_code == 200:
                data = response.json()
                text = data["choices"][0]["message"]["content"]
                used_model = model
                break

            last_error = response.text
        except Exception as e:
            last_error = str(e)
            continue

    if not text:
        logger.error(f"FAILED | user={user_id} | error={last_error}")
        raise HTTPException(
            status_code=503,
            detail="All free models are currently busy. Please try again in a moment."
        )

    # Opslaan in Supabase
    try:
        supabase = get_supabase_admin()
        supabase.table("conversations").insert({
            "user_id": user_id,
            "prompt": req.prompt,
            "answer": text,
            "model_used": used_model
        }).execute()
    except Exception as e:
        logger.error(f"DB SAVE FAILED | user={user_id} | {e}")

    duration = round(time.time() - start_time, 2)
    logger.info(f"SUCCESS | user={user_id} | model={used_model} | duration={duration}s")

    return {
        "text": text,
        "model_used": used_model
    }


@router.get("/conversations")
async def get_conversations(user = Depends(get_current_user)):
    supabase = get_supabase_admin()
    result = (
        supabase.table("conversations")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    return result.data

@router.post("/generate/stream")
async def generate_stream(
    req: GenerateRequest,
    request: Request,
    user=Depends(get_current_user),
):
    client_ip = request.client.host
    user_id = user.id
    rate_key = f"{user_id}:{client_ip}"

    if is_rate_limited(rate_key):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a moment.")

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not set")

    async def event_generator():
        collected = []
        used_model = None
        last_error = None

        for model in FREE_MODELS:
            used_model = model
            try:
                async with httpx.AsyncClient(timeout=90.0) as client:
                    async with client.stream(
                        "POST",
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "http://localhost:8000",
                            "X-Title": "AI App",
                        },
                        json={
                            "model": model,
                            "messages": [{"role": "user", "content": req.prompt}],
                            "stream": True,
                        },
                    ) as response:
                        if response.status_code != 200:
                            last_error = await response.aread()
                            continue

                        yield f"data: {json.dumps({'type': 'meta', 'model': model})}\n\n"

                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            if line.startswith("data: "):
                                payload = line[6:].strip()
                                if payload == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(payload)
                                    delta = chunk["choices"][0].get("delta", {})
                                    token = delta.get("content") or ""
                                    if token:
                                        collected.append(token)
                                        yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"
                                except Exception:
                                    continue

                # model werkte → klaar
                full_text = "".join(collected)
                if full_text:
                    try:
                        supabase = get_supabase_admin()
                        supabase.table("conversations").insert({
                            "user_id": user_id,
                            "prompt": req.prompt,
                            "answer": full_text,
                            "model_used": used_model,
                        }).execute()
                    except Exception as e:
                        logger.error(f"DB SAVE FAILED | user={user_id} | {e}")

                    yield f"data: {json.dumps({'type': 'done', 'model': used_model})}\n\n"
                    return

            except Exception as e:
                last_error = str(e)
                collected = []
                continue

        yield f"data: {json.dumps({'type': 'error', 'detail': 'All free models are currently busy.'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
