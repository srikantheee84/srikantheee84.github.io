"""Bedrock Nova Lite analysis — unified feedback analysis via Converse API."""

import json
import logging
import re

from src.models import AnalysisResult

logger = logging.getLogger(__name__)

MODEL_ID = "amazon.nova-lite-v1:0"


class BedrockAnalyzer:
    """Sends formatted feedback to Nova Lite and parses the analysis."""

    def __init__(self, bedrock_client=None, model_id: str = MODEL_ID):
        self._bedrock = bedrock_client
        self._model_id = model_id

    def analyze(self, messages: list[dict]) -> AnalysisResult:
        """Send messages to Bedrock Converse API and parse the response."""
        if not self._bedrock:
            return self._analyze_local(messages)

        try:
            response = self._bedrock.converse(
                modelId=self._model_id,
                messages=messages,
                inferenceConfig={
                    "maxTokens": 1024,
                    "temperature": 0.3,
                },
            )

            output = response.get("output", {})
            message = output.get("message", {})
            content_blocks = message.get("content", [])
            raw_text = ""
            for block in content_blocks:
                if "text" in block:
                    raw_text += block["text"]

            # Strip markdown code fences if present (Nova wraps JSON in ```)
            raw_text = self._strip_code_fences(raw_text)

            return self._parse_response(raw_text)

        except Exception as e:
            logger.error("Bedrock analysis failed: %s", e)
            return AnalysisResult(error=str(e))

    def _strip_code_fences(self, text: str) -> str:
        """Remove markdown code block fences from Nova responses."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        return text

    def _parse_response(self, raw_text: str) -> AnalysisResult:
        """Parse the structured response into an AnalysisResult."""
        themes = []
        sentiment_summary = ""
        recommendations = []

        # Parse THEMES section
        themes_match = re.search(
            r"THEMES?:\s*\n(.*?)(?=\nSENTIMENT|$)", raw_text, re.DOTALL | re.IGNORECASE
        )
        if themes_match:
            for line in themes_match.group(1).strip().split("\n"):
                line = line.strip().lstrip("- •*").strip()
                if line:
                    themes.append(line)

        # Parse SENTIMENT SUMMARY section
        sentiment_match = re.search(
            r"SENTIMENT SUMMARY:\s*\n(.*?)(?=\nRECOMMENDATION|$)",
            raw_text,
            re.DOTALL | re.IGNORECASE,
        )
        if sentiment_match:
            sentiment_summary = sentiment_match.group(1).strip()

        # Parse RECOMMENDATIONS section
        rec_match = re.search(
            r"RECOMMENDATIONS?:\s*\n(.*?)$", raw_text, re.DOTALL | re.IGNORECASE
        )
        if rec_match:
            for line in rec_match.group(1).strip().split("\n"):
                line = line.strip().lstrip("- •*").strip()
                if line:
                    recommendations.append(line)

        return AnalysisResult(
            themes=themes,
            sentiment_summary=sentiment_summary,
            recommendations=recommendations,
            raw_response=raw_text,
        )

    # ------------------------------------------------------------------
    # Local fallback for demo without AWS credentials
    # ------------------------------------------------------------------

    def _analyze_local(self, messages: list[dict]) -> AnalysisResult:
        """Generate a realistic analysis for demo without Bedrock access."""
        # Count what types of feedback we have
        text_count = sum(
            1 for m in messages
            if any("(text)" in c.get("text", "") for c in m.get("content", []))
        )
        image_count = sum(
            1 for m in messages
            if any("(image)" in c.get("text", "") for c in m.get("content", []))
        )
        audio_count = sum(
            1 for m in messages
            if any("(audio)" in c.get("text", "") for c in m.get("content", []))
        )
        survey_count = sum(
            1 for m in messages
            if any("(survey)" in c.get("text", "") for c in m.get("content", []))
        )

        # Scan all message text for keywords to generate relevant themes
        all_text = " ".join(
            c.get("text", "")
            for m in messages
            for c in m.get("content", [])
        ).lower()

        themes = []
        if "shipping" in all_text or "delivery" in all_text or "waiting" in all_text:
            themes.append("Shipping delays affecting customer satisfaction")
        if "damage" in all_text or "broken" in all_text or "packaging" in all_text:
            themes.append("Product quality issues with packaging")
        if "helpful" in all_text or "friendly" in all_text or "great" in all_text:
            themes.append("Positive feedback on customer service responsiveness")
        if "warranty" in all_text or "return" in all_text:
            themes.append("Warranty and return policy inquiries")
        if "price" in all_text or "expensive" in all_text or "cost" in all_text:
            themes.append("Price sensitivity and value perception")

        if not themes:
            themes = [
                "Product quality and reliability concerns",
                "Customer service interaction quality",
                "Delivery and fulfillment experience",
            ]

        recommendations = [
            "Review packaging standards for fragile items",
            "Investigate shipping partner SLA compliance",
            "Recognize customer service team performance",
        ]
        if "warranty" in all_text:
            recommendations.append("Simplify warranty extension process")
        if "price" in all_text:
            recommendations.append("Review pricing strategy for competitive positioning")

        return AnalysisResult(
            themes=themes[:5],
            sentiment_summary=(
                "Overall mixed sentiment. Strong positive feedback toward staff interactions "
                "and customer service responsiveness. Negative sentiment concentrated on "
                "logistics, packaging quality, and shipping delays. Survey scores show "
                "moderate satisfaction (mean 3.2/5) with room for improvement in delivery "
                "experience."
            ),
            recommendations=recommendations[:5],
            raw_response="[local demo — no Bedrock call made]",
        )
