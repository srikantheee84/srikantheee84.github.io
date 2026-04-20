"""Lambda-style text quality scoring for customer feedback."""

import re

from src.models import QualityResult

# Thresholds
MIN_WORD_COUNT = 5
MIN_CHAR_LENGTH = 20
QUALITY_THRESHOLD = 0.5


class QualityScorer:
    """Scores text quality and filters low-quality feedback before model invocation."""

    def __init__(self, threshold: float = QUALITY_THRESHOLD):
        self._threshold = threshold

    def score(self, text: str) -> QualityResult:
        """Score text on length, word count, and content quality. Returns 0.0-1.0."""
        reasons: list[str] = []
        scores: list[float] = []

        # Length score
        char_len = len(text.strip())
        if char_len < MIN_CHAR_LENGTH:
            reasons.append(f"too_short ({char_len} chars, min {MIN_CHAR_LENGTH})")
            scores.append(0.0)
        else:
            scores.append(min(char_len / 200.0, 1.0))

        # Word count score
        words = text.strip().split()
        word_count = len(words)
        if word_count < MIN_WORD_COUNT:
            reasons.append(f"too_few_words ({word_count}, min {MIN_WORD_COUNT})")
            scores.append(0.0)
        else:
            scores.append(min(word_count / 50.0, 1.0))

        # Content quality — penalize repetitive or gibberish text
        unique_words = set(w.lower() for w in words)
        if word_count > 0:
            diversity = len(unique_words) / word_count
        else:
            diversity = 0.0
        if diversity < 0.3:
            reasons.append("low_word_diversity")
        scores.append(min(diversity / 0.7, 1.0))

        # Penalize text that is all caps or all punctuation
        alpha_chars = sum(1 for c in text if c.isalpha())
        if char_len > 0 and alpha_chars / char_len < 0.5:
            reasons.append("low_alpha_ratio")
            scores.append(0.2)
        else:
            scores.append(1.0)

        final_score = sum(scores) / len(scores) if scores else 0.0
        passed = final_score > self._threshold

        return QualityResult(
            score=round(final_score, 3),
            passed=passed,
            failure_reasons=reasons,
        )
