import asyncio
import httpx
import time
import json
import sys

URLS = [
    "https://example.com",
    "https://theneuralake.com",
    "https://stripe.com"
]
RUNS = 3

async def main():
    print("=" * 100)
    print(f"{'Website':<25} | {'Run':<3} | {'OpenAI Result':<15} | {'PageSpeed Result':<25} | {'Total Duration':<15}")
    print("-" * 100)
    
    timeout = httpx.Timeout(connect=10.0, read=90.0, write=10.0, pool=10.0)
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        for url in URLS:
            for run in range(1, RUNS + 1):
                start = time.monotonic()
                try:
                    resp = await client.post(
                        "http://127.0.0.1:8000/api/analyse",
                        json={"url": url}
                    )
                    elapsed = time.monotonic() - start
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        ai = data.get("ai_insights", {})
                        ps = data.get("pagespeed", {})
                        
                        ai_res = ai.get("status", "unknown")
                        if ai_res != "available":
                            ai_res = f"FAIL ({ai.get('reason', '')[:20]}...)"
                            
                        ps_res = ps.get("status", "unknown")
                        if ps_res == "available":
                            ps_res = f"OK (Score: {ps.get('performance_score')})"
                        else:
                            ps_res = f"FAIL ({ps.get('reason', '')[:20]}...)"
                            
                        print(f"{url:<25} | {run:<3} | {ai_res:<15} | {ps_res:<25} | {elapsed:.2f}s")
                    else:
                        print(f"{url:<25} | {run:<3} | HTTP {resp.status_code:<10} | {'-':<25} | {elapsed:.2f}s")
                except Exception as e:
                    elapsed = time.monotonic() - start
                    print(f"{url:<25} | {run:<3} | ERR {type(e).__name__:<11} | {'-':<25} | {elapsed:.2f}s")

if __name__ == "__main__":
    asyncio.run(main())
