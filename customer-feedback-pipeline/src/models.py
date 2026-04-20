"""Data models for the customer feedback pipeline."""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class DataType(Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    SURVEY = "survey"


class RecordStatus(Enum):
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    LOW_QUALITY = "low_quality"
    QUALITY_PASSED = "quality_passed"
    VALIDATION_ERROR = "validation_error"
    PROCESSING_FAILED = "processing_failed"
    PROCESSED = "processed"


@dataclass
class FeedbackRecord:
    """A single customer feedback record."""
    record_id: str
    customer_id: str
    timestamp: str
    channel: str          # e.g., "email", "phone", "web", "survey"
    data_type: DataType
    rating: Optional[int] = None       # 1-5
    text: Optional[str] = None
    image_s3_key: Optional[str] = None
    audio_s3_key: Optional[str] = None
    survey_responses: Optional[list[dict]] = None
    status: RecordStatus = RecordStatus.PENDING
    metadata: dict = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of Glue Data Quality validation."""
    record_id: str
    is_valid: bool
    rule_violations: list[str] = field(default_factory=list)
    status: RecordStatus = RecordStatus.PENDING


@dataclass
class QualityResult:
    """Result of Lambda text quality scoring."""
    score: float                    # 0.0-1.0
    passed: bool                    # score >= 0.5
    failure_reasons: list[str] = field(default_factory=list)


@dataclass
class Entity:
    """A detected entity from Comprehend."""
    text: str
    entity_type: str               # PERSON, ORGANIZATION, LOCATION, DATE, QUANTITY, etc.
    confidence: float              # 0.0-1.0


@dataclass
class SentimentResult:
    """Sentiment analysis result from Comprehend."""
    sentiment: str                 # POSITIVE, NEGATIVE, NEUTRAL, MIXED
    positive: float
    negative: float
    neutral: float
    mixed: float


@dataclass
class TextProcessingResult:
    """Output from TextProcessor."""
    record_id: str
    original_text: str
    entities: list[Entity] = field(default_factory=list)
    sentiment: Optional[SentimentResult] = None
    status: RecordStatus = RecordStatus.PROCESSED
    error: Optional[str] = None


@dataclass
class TextBlock:
    """A text block extracted by Textract."""
    text: str
    confidence: float
    block_type: str                # LINE, WORD


@dataclass
class ImageLabel:
    """A label detected by Rekognition."""
    name: str
    confidence: float


@dataclass
class ImageProcessingResult:
    """Output from ImageProcessor."""
    record_id: str
    extracted_text: list[TextBlock] = field(default_factory=list)
    labels: list[ImageLabel] = field(default_factory=list)
    status: RecordStatus = RecordStatus.PROCESSED
    error: Optional[str] = None


@dataclass
class SpeakerSegment:
    """A speaker-labeled transcript segment."""
    speaker_label: str
    start_time: float
    end_time: float
    text: str


@dataclass
class AudioProcessingResult:
    """Output from AudioProcessor."""
    record_id: str
    full_transcript: str = ""
    segments: list[SpeakerSegment] = field(default_factory=list)
    status: RecordStatus = RecordStatus.PROCESSED
    error: Optional[str] = None


@dataclass
class QuestionSummary:
    """Summary statistics for a single survey question."""
    question_id: str
    question_text: str
    response_count: int
    response_distribution: dict = field(default_factory=dict)  # value -> count
    mean_score: Optional[float] = None  # for numeric questions


@dataclass
class SurveyProcessingResult:
    """Output from SurveyProcessor."""
    batch_id: str
    question_summaries: list[QuestionSummary] = field(default_factory=list)
    individual_responses: list[dict] = field(default_factory=list)
    free_text_responses: list[str] = field(default_factory=list)
    status: RecordStatus = RecordStatus.PROCESSED
    error: Optional[str] = None


@dataclass
class AnalysisResult:
    """Output from Bedrock Nova Lite analysis."""
    themes: list[str] = field(default_factory=list)
    sentiment_summary: str = ""
    recommendations: list[str] = field(default_factory=list)
    raw_response: str = ""
    error: Optional[str] = None
