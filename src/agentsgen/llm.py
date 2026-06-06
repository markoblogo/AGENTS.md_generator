from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .validators import (
    validate_llm_enhancement_result_payload,
    validate_llm_options_payload,
)


@dataclass(frozen=True)
class LLMOptions:
    enabled: bool = False
    provider: str = ""
    model: str = ""
    timeout_seconds: int = 30
    narrative_sections: tuple[str, ...] = field(default_factory=lambda: ("repo_context",))

    def normalized(self) -> "LLMOptions":
        provider = (self.provider or "").strip().lower()
        model = (self.model or "").strip()
        timeout_seconds = self.timeout_seconds if self.timeout_seconds > 0 else 30
        sections = tuple(
            sorted(
                {
                    str(section).strip()
                    for section in self.narrative_sections
                    if str(section).strip()
                }
            )
        ) or ("repo_context",)
        return LLMOptions(
            enabled=bool(self.enabled and provider),
            provider=provider,
            model=model,
            timeout_seconds=timeout_seconds,
            narrative_sections=sections,
        )

    def to_json(self) -> dict[str, object]:
        normalized = self.normalized()
        payload: dict[str, object] = {
            "enabled": normalized.enabled,
            "provider": normalized.provider,
            "model": normalized.model,
            "timeout_seconds": normalized.timeout_seconds,
            "narrative_sections": list(normalized.narrative_sections),
        }
        validate_llm_options_payload(payload)
        return payload

    @staticmethod
    def disabled() -> "LLMOptions":
        return LLMOptions()


@dataclass(frozen=True)
class LLMEnhancementRequest:
    target: Path
    provider: str
    model: str = ""
    timeout_seconds: int = 30
    narrative_sections: tuple[str, ...] = field(default_factory=lambda: ("repo_context",))


@dataclass(frozen=True)
class LLMEnhancementResult:
    provider: str
    applied: bool
    sections: dict[str, str]
    message: str = ""

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "provider": self.provider,
            "applied": self.applied,
            "sections": dict(self.sections),
            "message": self.message,
        }
        validate_llm_enhancement_result_payload(payload)
        return payload


class LLMEnhancer:
    def enhance(self, request: LLMEnhancementRequest) -> LLMEnhancementResult:
        raise NotImplementedError


def build_repo_context(target: Path) -> dict[str, object]:
    from .understand_context import build_understanding_payload

    return build_understanding_payload(target, output_dir=target / "docs" / "ai")


EnhancerFactory = Callable[[], LLMEnhancer]


def _openai_factory() -> LLMEnhancer:
    from .providers.openai import OpenAIEnhancer

    return OpenAIEnhancer()


def _anthropic_factory() -> LLMEnhancer:
    from .providers.anthropic import AnthropicEnhancer

    return AnthropicEnhancer()


PROVIDER_FACTORIES: dict[str, EnhancerFactory] = {
    "openai": _openai_factory,
    "anthropic": _anthropic_factory,
}


def resolve_enhancer(provider_name: str) -> LLMEnhancer | None:
    factory = PROVIDER_FACTORIES.get(provider_name)
    if factory is None:
        return None
    return factory()


def enhance_sections(request: LLMEnhancementRequest) -> LLMEnhancementResult:
    provider_name = (request.provider or "").strip().lower()
    if not provider_name:
        return LLMEnhancementResult(
            provider="none",
            applied=False,
            sections={},
            message="LLM enhancement disabled",
        )
    enhancer = resolve_enhancer(provider_name)
    if enhancer is None:
        return LLMEnhancementResult(
            provider=provider_name,
            applied=False,
            sections={},
            message=f"Unsupported LLM provider: {provider_name}",
        )
    try:
        return enhancer.enhance(request)
    except TimeoutError:
        return LLMEnhancementResult(
            provider=provider_name,
            applied=False,
            sections={},
            message=(
                f"{provider_name} enhancement timed out; "
                "falling back to local-only generation"
            ),
        )
    except Exception as exc:
        return LLMEnhancementResult(
            provider=provider_name,
            applied=False,
            sections={},
            message=(
                f"{provider_name} enhancement failed: {exc}; "
                "falling back to local-only generation"
            ),
        )
