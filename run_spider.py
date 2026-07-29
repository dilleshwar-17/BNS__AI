#!/usr/bin/env python3
"""BNS AI Spider Web - Agentic RAG Pipeline CLI"""

import sys
import json
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from app.core.logging import setup_logging
from agents.master_agent import master_agent
from bus.message_bus import web


async def cmd_train():
    print("\n=== Training Spider Web ===")
    from pipeline.super_pipeline import SuperPipeline
    pipeline = SuperPipeline()
    results = await pipeline.train()
    print(json.dumps(results, indent=2))
    print("Training complete!\n")


async def cmd_cycle(query: str, user_id: str = "cli_user", rating: int = 0):
    print(f"\n{'='*60}")
    print(f"  SPIDER WEB - FULL CYCLE")
    print(f"{'='*60}")
    print(f"  Query: {query}")
    print(f"  User:  {user_id}")
    print(f"{'='*60}\n")

    if not master_agent.running:
        master_agent.start()

    result = await master_agent.run_full_cycle({
        "query": query,
        "user_id": user_id,
        "rating": rating,
    })

    print(f"\n  Classification: {result['classification'].get('primary_type', 'N/A')}")
    print(f"  Confidence:     {result['classification'].get('confidence', 0):.2f}")
    print(f"  Complexity:     {result['classification'].get('complexity', 'N/A')}")
    print(f"  Topics:         {', '.join(result['classification'].get('topics', [])) or 'None'}")
    print(f"  Sections:       {result['classification'].get('sections', [])}")
    print(f"  Strategies:     {', '.join(result['retrieval']['strategies'])}")
    print(f"  Retrieved:      {result['retrieval']['total_results']} results")
    print(f"  Template:       {result['prompt']['template']}")
    print(f"  Quality:        {result['response_quality'].get('quality_score', 0):.2f}")
    print(f"  Elapsed:        {result['elapsed_seconds']}s")
    print(f"\n  {'='*40}")
    print(f"  RESPONSE:")
    print(f"  {'='*40}")
    print(f"  {result['response'][:500]}")
    print(f"  {'='*40}\n")

    return result


async def cmd_status():
    if not master_agent.running:
        master_agent.start()
    status = master_agent.get_status()
    print("\n=== Spider Web Status ===")
    print(json.dumps(status, indent=2, default=str))
    print()


async def cmd_learn(query: str, rating: int = 3):
    if not master_agent.running:
        master_agent.start()
    from agents.learning_agent import learning_agent
    result = await learning_agent.learn({
        "query": query,
        "type": "manual",
        "rating": rating,
        "quality": rating / 5.0,
        "user_id": "cli_user",
    })
    print(f"Learned: {json.dumps(result, indent=2)}")


async def cmd_adapt():
    if not master_agent.running:
        master_agent.start()
    from agents.learning_agent import learning_agent
    result = await learning_agent.adapt({"detect_gaps": True})
    print(f"Adaptations: {json.dumps(result, indent=2)}")


async def cmd_web_stats():
    stats = web.get_stats()
    print("\n=== Spider Web Message Bus Stats ===")
    print(f"  Total messages: {stats['total_messages']}")
    print(f"  Patterns: {json.dumps(stats['patterns'], indent=2)}")
    print(f"  Subscribers: {json.dumps(stats['subscribers'], indent=2)}")


async def cmd_interactive():
    print("\n" + "=" * 60)
    print("  BNS AI SPIDER WEB - Interactive Mode")
    print("=" * 60)
    print("  Commands:")
    print("    train              - Train pipeline (ingest all data)")
    print("    cycle <query>      - Run full agentic cycle")
    print("    status             - Show spider web status")
    print("    learn <q> <r>      - Learn from query with rating (1-5)")
    print("    adapt              - Run adaptation")
    print("    web                - Show message bus stats")
    print("    exit               - Exit")
    print("=" * 60)

    master_agent.start()

    while True:
        try:
            line = input("\n🕷️  ").strip()
            if not line:
                continue
            if line == "exit":
                break
            elif line == "train":
                await cmd_train()
            elif line == "status":
                await cmd_status()
            elif line == "web":
                await cmd_web_stats()
            elif line == "adapt":
                await cmd_adapt()
            elif line.startswith("cycle "):
                await cmd_cycle(line[6:])
            elif line.startswith("learn "):
                parts = line[6:].rsplit(" ", 1)
                if len(parts) == 2:
                    await cmd_learn(parts[0], int(parts[1]))
                else:
                    await cmd_learn(line[6:])
            else:
                print(f"Unknown: {line}")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

    master_agent.stop()


async def main():
    setup_logging()

    if len(sys.argv) < 2:
        await cmd_interactive()
        return

    command = sys.argv[1]

    if command == "interactive":
        await cmd_interactive()
    elif command == "train":
        await cmd_train()
    elif command == "cycle":
        query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        if not query:
            print("Usage: python run_spider.py cycle <query>")
            return
        await cmd_cycle(query)
    elif command == "status":
        await cmd_status()
    elif command == "adapt":
        await cmd_adapt()
    elif command == "web":
        await cmd_web_stats()
    else:
        print(f"Unknown: {command}")
        print("Usage: python run_spider.py [interactive|train|cycle|status|adapt|web]")


if __name__ == "__main__":
    asyncio.run(main())
