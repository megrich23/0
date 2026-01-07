#!/usr/bin/env python3
"""Example script demonstrating the brainstorming tool."""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    """Run a brainstorming session."""

    # Import after path setup
    from backend.tools import BrainstormingTool

    # Option 1: Basic usage (no external deps - will show diagnostic info)
    print("=" * 60)
    print("BRAINSTORMING TOOL - Basic Test (no providers)")
    print("=" * 60)

    tool = BrainstormingTool()
    result = await tool(
        topic="The relationship between consciousness and free will",
        mode="explore",
        depth=2,
    )

    print(f"\nSuccess: {result.success}")
    print(f"Ideas generated: {result.metadata.get('idea_count', 0)}")

    if result.data.get("phases_skipped"):
        print("\nPhases skipped (need providers):")
        for phase in result.data["phases_skipped"]:
            print(f"  - {phase['phase']}: {phase['reason']}")

    if result.metadata.get("warning"):
        print(f"\nWarning: {result.metadata['warning']}")

    # Option 2: With LLM provider (if API key available)
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        print("\n" + "=" * 60)
        print("BRAINSTORMING TOOL - With LLM Provider")
        print("=" * 60)

        from backend.core.providers import OpenAIProvider, ProviderConfig

        provider = OpenAIProvider(ProviderConfig(
            name="openai",
            provider_type="openai",
            api_key=api_key,
            model="gpt-4-turbo-preview",
            temperature=0.8,
        ))

        tool_with_llm = BrainstormingTool(llm_provider=provider)
        result = await tool_with_llm(
            topic="The relationship between consciousness and free will",
            mode="explore",
            depth=2,
        )

        print(f"\nSuccess: {result.success}")
        print(f"Ideas generated: {result.metadata.get('idea_count', 0)}")

        if result.data.get("ideas"):
            print("\nGenerated ideas:")
            for i, idea in enumerate(result.data["ideas"], 1):
                content = idea["content"][:200] + "..." if len(idea["content"]) > 200 else idea["content"]
                print(f"\n{i}. [{idea['source_type']}] {content}")
    else:
        print("\n" + "-" * 60)
        print("TIP: Set OPENAI_API_KEY environment variable to test with LLM synthesis")
        print("  export OPENAI_API_KEY=sk-...")


if __name__ == "__main__":
    asyncio.run(main())
