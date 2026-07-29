import asyncio

import httpx


async def check():
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:8000/api/v1/health")
            data = resp.json()
            status = data.get("status", "unknown")
            print(f"Health Status: {status}")
            for service, info in data.get("services", {}).items():
                print(f"  {service}: {info.get('status', 'unknown')}")
    except Exception as e:
        print(f"Health check failed: {e}")


if __name__ == "__main__":
    asyncio.run(check())
