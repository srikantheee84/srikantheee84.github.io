"""CloudWatch metrics publishing for pipeline quality monitoring."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

NAMESPACE = "CustomerFeedbackPipeline"


class QualityMonitor:
    """Publishes validation and processing metrics to CloudWatch."""

    def __init__(self, cloudwatch_client=None):
        self._cw = cloudwatch_client

    def publish_validation_metrics(self, pass_count: int, fail_count: int) -> None:
        """Publish batch validation pass/fail counts."""
        if not self._cw:
            logger.info(
                "CloudWatch not configured — validation metrics: pass=%d fail=%d",
                pass_count,
                fail_count,
            )
            return

        self._cw.put_metric_data(
            Namespace=NAMESPACE,
            MetricData=[
                {
                    "MetricName": "ValidationPassed",
                    "Value": pass_count,
                    "Unit": "Count",
                },
                {
                    "MetricName": "ValidationFailed",
                    "Value": fail_count,
                    "Unit": "Count",
                },
            ],
        )

    def publish_processing_metric(
        self, modality: str, latency_ms: float, success: bool
    ) -> None:
        """Publish per-modality processing latency and success/failure."""
        if not self._cw:
            logger.info(
                "CloudWatch not configured — %s processing: %.0fms success=%s",
                modality,
                latency_ms,
                success,
            )
            return

        self._cw.put_metric_data(
            Namespace=NAMESPACE,
            MetricData=[
                {
                    "MetricName": f"{modality.capitalize()}ProcessingLatency",
                    "Value": latency_ms,
                    "Unit": "Milliseconds",
                },
                {
                    "MetricName": f"{modality.capitalize()}ProcessingSuccess",
                    "Value": 1.0 if success else 0.0,
                    "Unit": "Count",
                },
            ],
        )

    def publish_analysis_metric(self, latency_ms: float, success: bool) -> None:
        """Publish Bedrock analysis latency and success/failure."""
        if not self._cw:
            logger.info(
                "CloudWatch not configured — analysis: %.0fms success=%s",
                latency_ms,
                success,
            )
            return

        self._cw.put_metric_data(
            Namespace=NAMESPACE,
            MetricData=[
                {
                    "MetricName": "AnalysisLatency",
                    "Value": latency_ms,
                    "Unit": "Milliseconds",
                },
                {
                    "MetricName": "AnalysisSuccess",
                    "Value": 1.0 if success else 0.0,
                    "Unit": "Count",
                },
            ],
        )
