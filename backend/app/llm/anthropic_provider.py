"""
Anthropic (Claude) comparison provider.

Requires ANTHROPIC_API_KEY environment variable.
Uses Claude for enhanced explanations and question generation.
The LLM does NOT override deterministic hard-constraint decisions.
"""

import os
from dotenv import load_dotenv
from backend.app.llm import ComparisonProvider, LLMComparisonResult

load_dotenv()


class AnthropicComparisonProvider(ComparisonProvider):
    """
    Claude-based comparison enhancement.
    Requires: pip install anthropic + ANTHROPIC_API_KEY env var.
    """

    def __init__(self):
        import anthropic
        load_dotenv()
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-3-7-sonnet-20250219"

    async def enhance_comparison(
        self,
        hospital_name: str,
        supplier_name: str,
        hospital_attrs: dict,
        supplier_attrs: dict,
        rule_based_evidence: list[dict],
        decision: str,
    ) -> LLMComparisonResult:
        prompt = f"""You are a medical device procurement expert. Analyze this product comparison.

Hospital Article: {hospital_name}
Hospital Attributes: {hospital_attrs}

Supplier Product: {supplier_name}
Supplier Attributes: {supplier_attrs}

Rule-based comparison evidence: {rule_based_evidence}
Preliminary decision: {decision}

Provide:
1. A concise business-facing summary (2-3 sentences)
2. Key reasoning points based on observable attributes only
3. Any additional concerns not captured by attribute comparison

Do NOT override the preliminary decision if there are hard conflicts.
Do NOT guess missing information.
Respond in English."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text

            return LLMComparisonResult(
                enhanced_summary=text,
                enhanced_reasoning="Enhanced by Claude analysis",
            )
        except Exception as e:
            # Graceful fallback
            return LLMComparisonResult(
                enhanced_summary=None,
                enhanced_reasoning=f"LLM enhancement failed: {str(e)}",
            )

    async def generate_questions(
        self,
        product_name: str,
        missing_attributes: list[str],
        context: dict,
    ) -> list[str]:
        if not missing_attributes:
            return []

        prompt = f"""You are a medical device procurement expert.
Generate clear, professional questions to ask a supplier about missing product specifications.

Product: {product_name}
Missing attributes: {', '.join(missing_attributes)}
Context: {context}

Generate one clear question per missing attribute.
Questions should be specific, professional, and request documentation where relevant.
Respond with one question per line."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text
            return [q.strip() for q in text.strip().split("\n") if q.strip()]
        except Exception:
            return []
