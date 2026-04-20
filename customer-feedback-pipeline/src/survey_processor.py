"""Survey data processing — aggregation and statistics."""

import logging
from collections import Counter

from src.models import (
    FeedbackRecord,
    QuestionSummary,
    RecordStatus,
    SurveyProcessingResult,
)

logger = logging.getLogger(__name__)


class SurveyProcessor:
    """Processes survey feedback by computing response distributions and statistics."""

    def process(self, records: list[FeedbackRecord]) -> SurveyProcessingResult:
        """Aggregate survey responses across a batch of records."""
        batch_id = records[0].record_id if records else "unknown"

        try:
            all_responses: list[dict] = []
            free_text: list[str] = []

            for record in records:
                if not record.survey_responses:
                    continue
                for response in record.survey_responses:
                    all_responses.append(response)
                    # Collect free-text answers
                    if response.get("type") == "free_text" and response.get("answer"):
                        free_text.append(response["answer"])

            # Group by question_id and compute summaries
            question_groups: dict[str, list[dict]] = {}
            for resp in all_responses:
                qid = resp.get("question_id", "unknown")
                question_groups.setdefault(qid, []).append(resp)

            summaries = []
            for qid, responses in question_groups.items():
                summary = self._summarize_question(qid, responses)
                summaries.append(summary)

            for record in records:
                record.status = RecordStatus.PROCESSED

            return SurveyProcessingResult(
                batch_id=batch_id,
                question_summaries=summaries,
                individual_responses=all_responses,
                free_text_responses=free_text,
                status=RecordStatus.PROCESSED,
            )
        except Exception as e:
            logger.error("Survey processing failed: %s", e)
            return SurveyProcessingResult(
                batch_id=batch_id,
                status=RecordStatus.PROCESSING_FAILED,
                error=str(e),
            )

    def _summarize_question(
        self, question_id: str, responses: list[dict]
    ) -> QuestionSummary:
        """Compute distribution and mean for a single question."""
        question_text = responses[0].get("question_text", question_id)
        answers = [r.get("answer") for r in responses if r.get("answer") is not None]

        distribution = dict(Counter(str(a) for a in answers))

        # Compute mean for numeric answers
        numeric_values = []
        for a in answers:
            try:
                numeric_values.append(float(a))
            except (ValueError, TypeError):
                pass

        mean_score = None
        if numeric_values:
            mean_score = round(sum(numeric_values) / len(numeric_values), 2)

        return QuestionSummary(
            question_id=question_id,
            question_text=question_text,
            response_count=len(answers),
            response_distribution=distribution,
            mean_score=mean_score,
        )
