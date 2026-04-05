#!/usr/bin/env python3
"""Verify Ollama is running and the target model is available."""

import asyncio
import sys

import ollama


async def main():
    client = ollama.AsyncClient()

    print("=== Ollama Health Check ===\n")

    try:
        models = await client.list()
    except Exception as e:
        print(f"❌ Cannot connect to Ollama: {e}")
        print("\n  Start Ollama with: ollama serve")
        sys.exit(1)

    print("✅ Ollama is running")
    print("\nAvailable models:")
    for m in models.get("models", []):
        size_gb = m.get("size", 0) / (1024**3)
        print(f"  - {m['name']} ({size_gb:.1f} GB)")

    # Test generation
    target_model = "qwen2.5:14b"
    available = [m["name"] for m in models.get("models", [])]
    model_base = target_model.split(":")[0]

    if any(model_base in m for m in available):
        print(f"\n✅ Target model '{target_model}' is available")
        print("\nTest generation...")
        response = await client.chat(
            model=target_model,
            messages=[{"role": "user", "content": "こんにちは。一言で自己紹介してください。"}],
        )
        print(f"  Response: {response['message']['content']}")
    else:
        print(f"\n❌ Target model '{target_model}' not found")
        print(f"  Pull it with: ollama pull {target_model}")


if __name__ == "__main__":
    asyncio.run(main())
