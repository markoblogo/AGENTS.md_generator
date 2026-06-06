from __future__ import annotations

import os

from ..llm import LLMEnhancementRequest, LLMEnhancementResult, LLMEnhancer, build_repo_context


class AnthropicEnhancer(LLMEnhancer):
    def enhance(self, request: LLMEnhancementRequest) -> LLMEnhancementResult:
        if not os.getenv("ANTHROPIC_API_KEY"):
            return LLMEnhancementResult(
                provider="anthropic",
                applied=False,
                sections={},
                message="ANTHROPIC_API_KEY is not set; falling back to local-only generation",
            )
        context = build_repo_context(request.target)
        summary = str(context.get("stack", "repo")).strip()
        return LLMEnhancementResult(
            provider="anthropic",
            applied=True,
            sections={
                "repo_context": (
                    "LLM-enhanced repo context\n\n"
                    f"- Detected stack: `{summary}`\n"
                    "- This narrative was generated from local understand artifacts.\n"
                    "- Commands and safety markers were preserved."
                )
            },
            message="Applied Anthropic narrative enhancement",
        )
