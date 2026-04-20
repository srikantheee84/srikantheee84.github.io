"""Image processing using Amazon Textract and Rekognition."""

import logging

from src.models import (
    FeedbackRecord,
    ImageLabel,
    ImageProcessingResult,
    RecordStatus,
    TextBlock,
)

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Processes image feedback using Textract (OCR) and Rekognition (labels)."""

    def __init__(self, textract_client=None, rekognition_client=None):
        self._textract = textract_client
        self._rekognition = rekognition_client

    def process(self, record: FeedbackRecord) -> ImageProcessingResult:
        """Extract text and detect labels from an image feedback record."""
        if not record.image_s3_key:
            return ImageProcessingResult(
                record_id=record.record_id,
                status=RecordStatus.PROCESSING_FAILED,
                error="No image_s3_key in record",
            )

        try:
            if self._textract and self._rekognition:
                text_blocks = self._extract_text(record.image_s3_key)
                labels = self._detect_labels(record.image_s3_key)
            else:
                text_blocks = self._extract_text_local(record.image_s3_key)
                labels = self._detect_labels_local(record.image_s3_key)

            record.status = RecordStatus.PROCESSED
            return ImageProcessingResult(
                record_id=record.record_id,
                extracted_text=text_blocks,
                labels=labels,
                status=RecordStatus.PROCESSED,
            )
        except Exception as e:
            logger.error("Image processing failed for %s: %s", record.record_id, e)
            record.status = RecordStatus.PROCESSING_FAILED
            return ImageProcessingResult(
                record_id=record.record_id,
                status=RecordStatus.PROCESSING_FAILED,
                error=str(e),
            )

    def _extract_text(self, s3_key: str) -> list[TextBlock]:
        """Call Textract DetectDocumentText."""
        bucket, key = self._parse_s3_key(s3_key)
        response = self._textract.detect_document_text(
            Document={"S3Object": {"Bucket": bucket, "Name": key}}
        )
        blocks = []
        for block in response.get("Blocks", []):
            if block["BlockType"] in ("LINE", "WORD"):
                blocks.append(
                    TextBlock(
                        text=block.get("Text", ""),
                        confidence=round(block.get("Confidence", 0.0), 1),
                        block_type=block["BlockType"],
                    )
                )
        return blocks

    def _detect_labels(self, s3_key: str) -> list[ImageLabel]:
        """Call Rekognition DetectLabels."""
        bucket, key = self._parse_s3_key(s3_key)
        response = self._rekognition.detect_labels(
            Image={"S3Object": {"Bucket": bucket, "Name": key}},
            MaxLabels=20,
        )
        return [
            ImageLabel(
                name=label["Name"],
                confidence=round(label["Confidence"], 1),
            )
            for label in response.get("Labels", [])
        ]

    @staticmethod
    def _parse_s3_key(s3_key: str) -> tuple[str, str]:
        """Parse 's3://bucket/key' or 'bucket/key' into (bucket, key)."""
        if s3_key.startswith("s3://"):
            s3_key = s3_key[5:]
        parts = s3_key.split("/", 1)
        return parts[0], parts[1] if len(parts) > 1 else ""

    # ------------------------------------------------------------------
    # Local fallback for demo without AWS credentials
    # ------------------------------------------------------------------

    def _extract_text_local(self, s3_key: str) -> list[TextBlock]:
        """Simulated OCR results for demo."""
        # Generate realistic OCR output based on the key name
        key_lower = s3_key.lower()
        if "receipt" in key_lower:
            return [
                TextBlock(text="RECEIPT", confidence=99.5, block_type="LINE"),
                TextBlock(text="Store: Downtown Branch", confidence=98.2, block_type="LINE"),
                TextBlock(text="Date: 2026-03-15", confidence=97.8, block_type="LINE"),
                TextBlock(text="Item: Widget Pro X", confidence=96.5, block_type="LINE"),
                TextBlock(text="Total: $49.99", confidence=99.1, block_type="LINE"),
            ]
        elif "damage" in key_lower or "broken" in key_lower:
            return [
                TextBlock(text="FRAGILE", confidence=95.3, block_type="LINE"),
                TextBlock(text="Handle With Care", confidence=92.1, block_type="LINE"),
                TextBlock(text="Shipping Label: PKG-2026-4421", confidence=88.7, block_type="LINE"),
            ]
        else:
            return [
                TextBlock(text="Customer Feedback Form", confidence=97.0, block_type="LINE"),
                TextBlock(text="Product: Premium Package", confidence=94.5, block_type="LINE"),
                TextBlock(text="Rating: 3/5", confidence=96.2, block_type="LINE"),
            ]

    def _detect_labels_local(self, s3_key: str) -> list[ImageLabel]:
        """Simulated label detection for demo."""
        key_lower = s3_key.lower()
        if "damage" in key_lower or "broken" in key_lower:
            return [
                ImageLabel(name="Box", confidence=98.7),
                ImageLabel(name="Cardboard", confidence=97.2),
                ImageLabel(name="Package", confidence=95.8),
                ImageLabel(name="Damage", confidence=89.3),
                ImageLabel(name="Tape", confidence=85.1),
            ]
        elif "receipt" in key_lower:
            return [
                ImageLabel(name="Document", confidence=99.1),
                ImageLabel(name="Text", confidence=98.5),
                ImageLabel(name="Paper", confidence=97.3),
                ImageLabel(name="Receipt", confidence=94.2),
            ]
        else:
            return [
                ImageLabel(name="Product", confidence=96.5),
                ImageLabel(name="Electronics", confidence=91.2),
                ImageLabel(name="Package", confidence=88.7),
                ImageLabel(name="Label", confidence=85.4),
            ]
