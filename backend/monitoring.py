"""Monitoring logic for Ollama and Council performance."""

import time
import httpx
from typing import Dict, List, Any
from .config import OLLAMA_API_URL

# In-memory stats storage
STATS = {
    "requests_total": 0,
    "requests_failed": 0,
    "total_latency_ms": 0,
    "models_usage": {}
}

async def get_ollama_status() -> Dict[str, Any]:
    """Check Ollama service status and running models."""
    # OLLAMA_API_URL is usually http://localhost:11434/api/chat
    # We want the base URL
    base_url = OLLAMA_API_URL.replace("/api/chat", "")
    
    status = {
        "service": "unknown",
        "version": "unknown",
        "running_models": []
    }
    
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            # Check version
            try:
                resp = await client.get(f"{base_url}/api/version")
                if resp.status_code == 200:
                    status["service"] = "online"
                    status["version"] = resp.json().get("version")
                else:
                    status["service"] = "error"
            except httpx.ConnectError:
                status["service"] = "offline"
                return status
            
            # Check running models (ps)
            # Note: /api/ps was added in recent Ollama versions. 
            # If it fails (404), we just return empty list.
            try:
                resp_ps = await client.get(f"{base_url}/api/ps")
                if resp_ps.status_code == 200:
                    status["running_models"] = resp_ps.json().get("models", [])
            except Exception:
                pass
                
    except Exception as e:
        status["service"] = "offline"
        status["error"] = str(e)
        
    return status

def record_request(model: str, latency_ms: float, success: bool):
    """Record request metrics."""
    STATS["requests_total"] += 1
    if not success:
        STATS["requests_failed"] += 1
    else:
        STATS["total_latency_ms"] += latency_ms
        
    if model not in STATS["models_usage"]:
        STATS["models_usage"][model] = {"count": 0, "total_latency": 0, "errors": 0}
    
    STATS["models_usage"][model]["count"] += 1
    if success:
        STATS["models_usage"][model]["total_latency"] += latency_ms
    else:
        STATS["models_usage"][model]["errors"] += 1

def get_stats() -> Dict[str, Any]:
    """Get current stats."""
    avg_latency = 0
    success_count = STATS["requests_total"] - STATS["requests_failed"]
    if success_count > 0:
        avg_latency = STATS["total_latency_ms"] / success_count
        
    # Calculate per-model averages
    model_stats = {}
    for model, data in STATS["models_usage"].items():
        m_success = data["count"] - data["errors"]
        m_avg = 0
        if m_success > 0:
            m_avg = data["total_latency"] / m_success
            
        model_stats[model] = {
            "count": data["count"],
            "errors": data["errors"],
            "average_latency_ms": round(m_avg, 2)
        }
        
    return {
        "global": {
            "total_requests": STATS["requests_total"],
            "failed_requests": STATS["requests_failed"],
            "average_latency_ms": round(avg_latency, 2)
        },
        "models": model_stats
    }
