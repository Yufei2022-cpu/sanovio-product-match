"""
LLM Provider interface and implementations.

The ComparisonProvider is a replaceable interface that abstracts
LLM-based comparison enhancement. Business logic does NOT depend
on any specific LLM API.

Implementations:
- MockComparisonProvider: Returns pre-cached results (demo mode)
- RuleBasedComparisonProvider: Pure deterministic, no LLM
- AnthropicComparisonProvider: Uses Claude API (requires API key)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMComparisonResult:
    """Enhanced comparison result from LLM."""
    enhanced_summary: Optional[str] = None
    enhanced_reasoning: Optional[str] = None
    additional_questions: list[dict] = None
    semantic_equivalence_notes: list[str] = None

    def __post_init__(self):
        if self.additional_questions is None:
            self.additional_questions = []
        if self.semantic_equivalence_notes is None:
            self.semantic_equivalence_notes = []


class ComparisonProvider(ABC):
    """
    Abstract interface for LLM-enhanced comparison.

    The LLM provider SUPPLEMENTS the deterministic comparison engine.
    It cannot override hard conflicts (e.g., sterile vs non-sterile).
    """

    @abstractmethod
    async def enhance_comparison(
        self,
        hospital_name: str,
        supplier_name: str,
        hospital_attrs: dict,
        supplier_attrs: dict,
        rule_based_evidence: list[dict],
        decision: str,
    ) -> LLMComparisonResult:
        """Enhance a comparison with LLM analysis."""
        pass

    @abstractmethod
    async def generate_questions(
        self,
        product_name: str,
        missing_attributes: list[str],
        context: dict,
    ) -> list[str]:
        """Generate targeted supplier questions."""
        pass


class MockComparisonProvider(ComparisonProvider):
    """
    Mock provider for demo mode — returns reasonable pre-built responses.
    No API calls required.
    """

    async def enhance_comparison(
        self,
        hospital_name: str,
        supplier_name: str,
        hospital_attrs: dict,
        supplier_attrs: dict,
        rule_based_evidence: list[dict],
        decision: str,
    ) -> LLMComparisonResult:
        # Return a reasonable mock enhancement
        if decision == "compatible":
            summary = (
                f"Based on the available product specifications, '{supplier_name}' "
                f"appears to be a suitable replacement for '{hospital_name}'. "
                f"All critical attributes align."
            )
        elif decision == "incompatible":
            summary = (
                f"'{supplier_name}' cannot serve as a replacement for '{hospital_name}'. "
                f"There are fundamental specification conflicts that cannot be resolved."
            )
        else:
            summary = (
                f"The comparison between '{supplier_name}' and '{hospital_name}' "
                f"is inconclusive due to missing critical specifications. "
                f"Supplier clarification is required before a decision can be made."
            )

        return LLMComparisonResult(
            enhanced_summary=summary,
            enhanced_reasoning="Analysis based on rule-based attribute comparison (mock mode).",
        )

    async def generate_questions(
        self,
        product_name: str,
        missing_attributes: list[str],
        context: dict,
    ) -> list[str]:
        return [
            f"Please provide the {attr} specification for {product_name}."
            for attr in missing_attributes
        ]


class RuleBasedComparisonProvider(ComparisonProvider):
    """
    Pure deterministic provider — no LLM calls at all.
    Uses template-based explanations.
    """

    async def enhance_comparison(
        self,
        hospital_name: str,
        supplier_name: str,
        hospital_attrs: dict,
        supplier_attrs: dict,
        rule_based_evidence: list[dict],
        decision: str,
    ) -> LLMComparisonResult:
        # Just pass through — no enhancement
        return LLMComparisonResult()

    async def generate_questions(
        self,
        product_name: str,
        missing_attributes: list[str],
        context: dict,
    ) -> list[str]:
        return []


def get_provider(provider_type: str = "mock") -> ComparisonProvider:
    """Factory function for comparison providers."""
    providers = {
        "mock": MockComparisonProvider,
        "rule_based": RuleBasedComparisonProvider,
    }

    # Lazy import for Anthropic to avoid requiring the SDK
    if provider_type == "anthropic":
        try:
            from backend.app.llm.anthropic_provider import AnthropicComparisonProvider
            return AnthropicComparisonProvider()
        except ImportError:
            print("Warning: anthropic package not installed. Falling back to mock.")
            return MockComparisonProvider()

    provider_class = providers.get(provider_type, MockComparisonProvider)
    return provider_class()
