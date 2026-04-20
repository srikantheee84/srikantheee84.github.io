"""Data validation using Glue Data Quality rules and Lambda quality scoring."""

import logging
from datetime import datetime, timedelta, timezone

from src.models import (
    DataType,
    FeedbackRecord,
    RecordStatus,
    ValidationResult,
)

logger = logging.getLogger(__name__)

# Required fields for completeness check
REQUIRED_FIELDS = ["record_id", "customer_id", "timestamp", "channel", "data_type"]

# Maximum age for freshness check
MAX_AGE_DAYS = 90


class DataValidator:
    """Validates feedback records using Glue Data Quality rules."""

    def __init__(self, quality_scorer=None, quality_monitor=None):
        self._seen_ids: set[str] = set()
        self._quality_scorer = quality_scorer
        self._quality_monitor = quality_monitor

    def validate(self, record: FeedbackRecord) -> ValidationResult:
        """Validate a single record against completeness, uniqueness, freshness rules."""
        violations: list[str] = []

        # Completeness: all required fields must be present and non-empty
        for field_name in REQUIRED_FIELDS:
            value = getattr(record, field_name, None)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                violations.append(f"missing_{field_name}")

        # Uniqueness: no duplicate record_id within the batch
        if record.record_id in self._seen_ids:
            violations.append("duplicate_id")
        else:
            self._seen_ids.add(record.record_id)

        # Freshness: timestamp within the last 90 days
        if record.timestamp:
            try:
                ts = datetime.fromisoformat(record.timestamp)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
                if ts < cutoff:
                    violations.append("stale_timestamp")
            except (ValueError, TypeError):
                violations.append("invalid_timestamp")

        is_valid = len(violations) == 0
        status = RecordStatus.VALID if is_valid else RecordStatus.INVALID
        record.status = status

        return ValidationResult(
            record_id=record.record_id,
            is_valid=is_valid,
            rule_violations=violations,
            status=status,
        )

    def validate_batch(self, records: list[FeedbackRecord]) -> list[ValidationResult]:
        """Validate a batch and publish CloudWatch metrics."""
        self._seen_ids.clear()
        results: list[ValidationResult] = []

        for record in records:
            result = self.validate(record)
            results.append(result)

        pass_count = sum(1 for r in results if r.is_valid)
        fail_count = len(results) - pass_count

        # Publish validation metrics via QualityMonitor
        if self._quality_monitor:
            try:
                self._quality_monitor.publish_validation_metrics(pass_count, fail_count)
            except Exception as e:
                logger.error("Failed to publish validation metrics: %s", e)

        # For text records that passed structural validation, invoke QualityScorer
        if self._quality_scorer:
            for record, result in zip(records, results):
                if result.is_valid and record.data_type == DataType.TEXT and record.text:
                    try:
                        quality_result = self._quality_scorer.score(record.text)
                        if quality_result.passed:
                            record.status = RecordStatus.QUALITY_PASSED
                        else:
                            record.status = RecordStatus.LOW_QUALITY
                    except Exception as e:
                        logger.error(
                            "Quality scorer failed for record %s: %s",
                            record.record_id,
                            e,
                        )
                        record.status = RecordStatus.VALIDATION_ERROR

        return results
