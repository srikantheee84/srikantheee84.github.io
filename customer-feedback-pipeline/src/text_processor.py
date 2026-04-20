"""Text processing using Amazon Comprehend for entity extraction and sentiment analysis."""

import logging

from src.models import (
    Entity,
    FeedbackRecord,
    RecordStatus,
    SentimentResult,
    TextProcessingResult,
)

logger = logging.getLogger(__name__)


class TextProcessor:
    """Processes text feedback using Amazon Comprehend."""

    def __init__(self, comprehend_client=None):
        self._comprehend = comprehend_client

    def process(self, record: FeedbackRecord) -> TextProcessingResult:
        """Extract entities and detect sentiment from a text feedback record."""
        if not record.text:
            return TextProcessingResult(
                record_id=record.record_id,
                original_text="",
                status=RecordStatus.PROCESSING_FAILED,
                error="No text content in record",
            )

        text = record.text
        entities: list[Entity] = []
        sentiment: SentimentResult | None = None

        try:
            if self._comprehend:
                entities = self._detect_entities(text)
                sentiment = self._detect_sentiment(text)
            else:
                entities = self._detect_entities_local(text)
                sentiment = self._detect_sentiment_local(text)

            record.status = RecordStatus.PROCESSED
            return TextProcessingResult(
                record_id=record.record_id,
                original_text=text,
                entities=entities,
                sentiment=sentiment,
                status=RecordStatus.PROCESSED,
            )
        except Exception as e:
            logger.error("Text processing failed for %s: %s", record.record_id, e)
            record.status = RecordStatus.PROCESSING_FAILED
            return TextProcessingResult(
                record_id=record.record_id,
                original_text=text,
                status=RecordStatus.PROCESSING_FAILED,
                error=str(e),
            )

    def _detect_entities(self, text: str) -> list[Entity]:
        """Call Comprehend DetectEntities."""
        response = self._comprehend.detect_entities(Text=text, LanguageCode="en")
        return [
            Entity(
                text=e["Text"],
                entity_type=e["Type"],
                confidence=round(e["Score"], 3),
            )
            for e in response.get("Entities", [])
        ]

    def _detect_sentiment(self, text: str) -> SentimentResult:
        """Call Comprehend DetectSentiment."""
        response = self._comprehend.detect_sentiment(Text=text, LanguageCode="en")
        scores = response.get("SentimentScore", {})
        return SentimentResult(
            sentiment=response.get("Sentiment", "NEUTRAL"),
            positive=round(scores.get("Positive", 0.0), 3),
            negative=round(scores.get("Negative", 0.0), 3),
            neutral=round(scores.get("Neutral", 0.0), 3),
            mixed=round(scores.get("Mixed", 0.0), 3),
        )

    # ------------------------------------------------------------------
    # Local fallback for demo without AWS credentials
    # ------------------------------------------------------------------

    def _detect_entities_local(self, text: str) -> list[Entity]:
        """Simple keyword-based entity detection for local demo."""
        entities = []
        # Look for capitalized multi-word names as PERSON candidates
        import re

        # Simple patterns for demo purposes
        name_pattern = re.compile(r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b")
        for match in name_pattern.finditer(text):
            entities.append(
                Entity(text=match.group(1), entity_type="PERSON", confidence=0.85)
            )

        # Location keywords
        location_words = ["store", "location", "branch", "office", "center"]
        for word in location_words:
            idx = text.lower().find(word)
            if idx > 0:
                # Grab preceding word as location name
                before = text[:idx].strip().split()
                if before:
                    loc = before[-1]
                    if loc[0].isupper():
                        entities.append(
                            Entity(text=loc, entity_type="LOCATION", confidence=0.75)
                        )

        # Organization patterns
        org_suffixes = ["Inc", "Corp", "LLC", "Ltd", "Co"]
        for suffix in org_suffixes:
            if suffix in text:
                idx = text.find(suffix)
                before = text[:idx].strip().split()
                if before:
                    org_name = before[-1] + " " + suffix
                    entities.append(
                        Entity(text=org_name, entity_type="ORGANIZATION", confidence=0.80)
                    )

        return entities

    def _detect_sentiment_local(self, text: str) -> SentimentResult:
        """Simple keyword-based sentiment detection for local demo."""
        text_lower = text.lower()
        positive_words = [
            "great", "excellent", "good", "love", "amazing", "wonderful",
            "fantastic", "happy", "pleased", "satisfied", "helpful", "friendly",
        ]
        negative_words = [
            "bad", "terrible", "awful", "hate", "horrible", "worst",
            "disappointed", "frustrated", "angry", "broken", "damaged", "poor",
            "slow", "rude", "waiting", "never", "complaint",
        ]

        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)
        total = pos_count + neg_count or 1

        pos_score = pos_count / total
        neg_score = neg_count / total
        neutral_score = max(0.0, 1.0 - pos_score - neg_score)

        if pos_score > neg_score and pos_score > 0.4:
            sentiment = "POSITIVE"
        elif neg_score > pos_score and neg_score > 0.4:
            sentiment = "NEGATIVE"
        elif pos_count > 0 and neg_count > 0:
            sentiment = "MIXED"
        else:
            sentiment = "NEUTRAL"

        return SentimentResult(
            sentiment=sentiment,
            positive=round(pos_score, 3),
            negative=round(neg_score, 3),
            neutral=round(neutral_score, 3),
            mixed=round(0.1 if sentiment == "MIXED" else 0.0, 3),
        )
