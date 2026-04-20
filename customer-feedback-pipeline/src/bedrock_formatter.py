"""Formats processing results into Bedrock Converse API messages."""

from src.models import (
    AudioProcessingResult,
    ImageProcessingResult,
    SurveyProcessingResult,
    TextProcessingResult,
)


class BedrockFormatter:
    """Converts processor outputs into Converse API message format."""

    def format_text_result(self, result: TextProcessingResult) -> dict:
        """Format text processing result as a Converse API user message."""
        parts = [f"Customer feedback (text): \"{result.original_text}\""]

        if result.entities:
            entity_strs = [
                f"{e.entity_type}: {e.text} ({e.confidence:.0%})"
                for e in result.entities
            ]
            parts.append(f"Detected entities: {', '.join(entity_strs)}")

        if result.sentiment:
            s = result.sentiment
            parts.append(
                f"Sentiment: {s.sentiment} "
                f"(positive={s.positive:.0%}, negative={s.negative:.0%}, "
                f"neutral={s.neutral:.0%})"
            )

        return {"role": "user", "content": [{"text": "\n".join(parts)}]}

    def format_image_result(self, result: ImageProcessingResult) -> dict:
        """Format image processing result as a Converse API user message."""
        parts = [f"Customer feedback (image): record {result.record_id}"]

        if result.extracted_text:
            ocr_lines = [
                f"  {b.text} (confidence: {b.confidence:.1f}%)"
                for b in result.extracted_text
                if b.block_type == "LINE"
            ]
            parts.append("Extracted text (OCR):")
            parts.extend(ocr_lines)

        if result.labels:
            label_strs = [
                f"{l.name} ({l.confidence:.1f}%)" for l in result.labels
            ]
            parts.append(f"Detected labels: {', '.join(label_strs)}")

        return {"role": "user", "content": [{"text": "\n".join(parts)}]}

    def format_audio_result(self, result: AudioProcessingResult) -> dict:
        """Format audio processing result as a Converse API user message."""
        parts = [f"Customer feedback (audio): record {result.record_id}"]

        if result.segments:
            parts.append("Transcript with speaker labels:")
            for seg in result.segments:
                parts.append(
                    f"  [{seg.speaker_label}] ({seg.start_time:.1f}s-{seg.end_time:.1f}s): "
                    f"{seg.text}"
                )
        elif result.full_transcript:
            parts.append(f"Transcript: {result.full_transcript}")

        return {"role": "user", "content": [{"text": "\n".join(parts)}]}

    def format_survey_result(self, result: SurveyProcessingResult) -> dict:
        """Format survey processing result as a Converse API user message."""
        parts = [f"Customer feedback (survey): batch {result.batch_id}"]

        if result.question_summaries:
            parts.append("Survey results:")
            for qs in result.question_summaries:
                line = f"  {qs.question_text}: {qs.response_count} responses"
                if qs.mean_score is not None:
                    line += f", mean={qs.mean_score:.1f}"
                line += f", distribution={qs.response_distribution}"
                parts.append(line)

        if result.free_text_responses:
            parts.append("Free-text responses:")
            for ft in result.free_text_responses[:10]:  # Cap at 10
                parts.append(f"  - \"{ft}\"")

        return {"role": "user", "content": [{"text": "\n".join(parts)}]}

    def build_analysis_messages(
        self,
        text_results: list[TextProcessingResult],
        image_results: list[ImageProcessingResult],
        audio_results: list[AudioProcessingResult],
        survey_results: list[SurveyProcessingResult],
    ) -> list[dict]:
        """Build the full message list for Bedrock analysis."""
        messages = []

        for r in text_results:
            messages.append(self.format_text_result(r))
        for r in image_results:
            messages.append(self.format_image_result(r))
        for r in audio_results:
            messages.append(self.format_audio_result(r))
        for r in survey_results:
            messages.append(self.format_survey_result(r))

        # Add the analysis instruction as the final user message
        messages.append({
            "role": "user",
            "content": [{
                "text": (
                    "You are a customer feedback analyst. Based on all the feedback above "
                    "(text reviews, image analysis, audio transcripts, and survey results), "
                    "provide:\n"
                    "1. KEY THEMES: The top 3-5 recurring themes across all feedback types\n"
                    "2. SENTIMENT SUMMARY: An overall sentiment assessment in 2-3 sentences\n"
                    "3. RECOMMENDATIONS: 3-5 actionable recommendations based on the feedback\n\n"
                    "Format your response as:\n"
                    "THEMES:\n- theme 1\n- theme 2\n...\n\n"
                    "SENTIMENT SUMMARY:\n...\n\n"
                    "RECOMMENDATIONS:\n- recommendation 1\n- recommendation 2\n..."
                )
            }],
        })

        return messages
