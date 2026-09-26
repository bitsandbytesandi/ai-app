from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import httpx
import os
import asyncio
import time
from collections import defaultdict
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("ai-app")

router = APIRouter()

class GenerateRequest(BaseModel):
    prompt: str

# Simple in-memory rate limiter (per IP)
RATE_LIMIT = 12          # max requests
RATE_WINDOW = 60         # per 60 seconds
request_log = defaultdict(list)

FREE_MODELS = [
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "inclusionai/ling-3.0-flash-fin:free",
    "qwen/qwen3.8-27b:free",
    "google/gemma-4-26b-a4b-it:free",
]

def is_rate_limited(ip: str) -> bool:
    now = time.time()
    # Clean old requests
    request_log[ip] = [t for t in request_log[ip] if now - t < RATE_WINDOW]
    if len(request_log[ip]) >= RATE_LIMIT:
        return True
    request_log[ip].append(now)
    return False

@router.post("/generate")
async def generate(req: GenerateRequest, request: Request):
    client_ip = request.client.host
    start_time = time.time()

    if is_rate_limited(client_ip):
        logger.warning(f"RATE LIMIT | ip={client_ip}")
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a moment.")

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not set")

    last_error = None
    used_model = None

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
                duration = round(time.time() - start_time, 2)

                logger.info(
                    f"SUCCESS | ip={client_ip} | model={model} | "
                    f"prompt_len={len(req.prompt)} | duration={duration}s"
                )

                return {
                    "text": text,
                    "model_used": model
                }

            last_error = response.text
            used_model = model

        except Exception as e:
            last_error = str(e)
            continue

    duration = round(time.time() - start_time, 2)
    logger.error(
        f"FAILED | ip={client_ip} | last_model={used_model} | "
        f"prompt_len={len(req.prompt)} | duration={duration}s | error={last_error}"
    )

    raise HTTPException(
        status_code=503,
        detail="All free models are currently busy. Please try again in a moment."
    )
