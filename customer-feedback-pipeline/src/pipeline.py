"""Pipeline orchestrator — wires validation, routing, processing, and analysis."""

import logging
import time
from dataclasses import dataclass, field

from src.audio_processor import AudioProcessor
from src.bedrock_analyzer import BedrockAnalyzer
from src.bedrock_formatter import BedrockFormatter
from src.data_validator import DataValidator
from src.image_processor import ImageProcessor
from src.models import (
    AnalysisResult,
    AudioProcessingResult,
    DataType,
    FeedbackRecord,
    ImageProcessingResult,
    RecordStatus,
    SurveyProcessingResult,
    TextProcessingResult,
    ValidationResult,
)
from src.quality_monitor import QualityMonitor
from src.quality_scorer import QualityScorer
from src.survey_processor import SurveyProcessor
from src.text_processor import TextProcessor

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Full pipeline output."""

    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    validation_results: list[ValidationResult] = field(default_factory=list)
    text_results: list[TextProcessingResult] = field(default_factory=list)
    image_results: list[ImageProcessingResult] = field(default_factory=list)
    audio_results: list[AudioProcessingResult] = field(default_factory=list)
    survey_results: list[SurveyProcessingResult] = field(default_factory=list)
    analysis: AnalysisResult | None = None
    processing_time_ms: float = 0.0


class Pipeline:
    """Orchestrates the full feedback processing pipeline."""

    def __init__(
        self,
        bedrock_client=None,
        comprehend_client=None,
        textract_client=None,
        rekognition_client=None,
        transcribe_client=None,
        cloudwatch_client=None,
    ):
        self._monitor = QualityMonitor(cloudwatch_client)
        self._scorer = QualityScorer()
        self._validator = DataValidator(
            quality_scorer=self._scorer, quality_monitor=self._monitor
        )
        self._text_processor = TextProcessor(comprehend_client)
        self._image_processor = ImageProcessor(textract_client, rekognition_client)
        self._audio_processor = AudioProcessor(transcribe_client)
        self._survey_processor = SurveyProcessor()
        self._formatter = BedrockFormatter()
        self._analyzer = BedrockAnalyzer(bedrock_client)

    def run(self, records: list[FeedbackRecord]) -> PipelineResult:
        """Run the full pipeline: validate → route → process → format → analyze."""
        start = time.time()
        result = PipelineResult(total_records=len(records))

        # Step 1: Validate
        validation_results = self._validator.validate_batch(records)
        result.validation_results = validation_results
        result.valid_records = sum(1 for v in validation_results if v.is_valid)
        result.invalid_records = result.total_records - result.valid_records

        # Step 2: Route valid records by type
        valid_records = [
            r
            for r, v in zip(records, validation_results)
            if v.is_valid and r.status != RecordStatus.LOW_QUALITY
        ]

        text_records = [r for r in valid_records if r.data_type == DataType.TEXT]
        image_records = [r for r in valid_records if r.data_type == DataType.IMAGE]
        audio_records = [r for r in valid_records if r.data_type == DataType.AUDIO]
        survey_records = [r for r in valid_records if r.data_type == DataType.SURVEY]

        # Step 3: Process each modality
        for record in text_records:
            tr = self._text_processor.process(record)
            result.text_results.append(tr)

        for record in image_records:
            ir = self._image_processor.process(record)
            result.image_results.append(ir)

        for record in audio_records:
            ar = self._audio_processor.process(record)
            result.audio_results.append(ar)

        if survey_records:
            sr = self._survey_processor.process(survey_records)
            result.survey_results.append(sr)

        # Step 4: Format for Bedrock
        messages = self._formatter.build_analysis_messages(
            result.text_results,
            result.image_results,
            result.audio_results,
            result.survey_results,
        )

        # Step 5: Analyze with Bedrock
        if messages and len(messages) > 1:  # More than just the instruction message
            result.analysis = self._analyzer.analyze(messages)

        result.processing_time_ms = (time.time() - start) * 1000
        return result
