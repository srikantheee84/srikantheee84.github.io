"""Audio processing using Amazon Transcribe with speaker diarization."""

import logging
import time

from src.models import (
    AudioProcessingResult,
    FeedbackRecord,
    RecordStatus,
    SpeakerSegment,
)

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Processes audio feedback using Amazon Transcribe."""

    def __init__(self, transcribe_client=None):
        self._transcribe = transcribe_client

    def process(self, record: FeedbackRecord) -> AudioProcessingResult:
        """Transcribe audio with speaker labels."""
        if not record.audio_s3_key:
            return AudioProcessingResult(
                record_id=record.record_id,
                status=RecordStatus.PROCESSING_FAILED,
                error="No audio_s3_key in record",
            )

        try:
            if self._transcribe:
                segments = self._transcribe_audio(record.audio_s3_key, record.record_id)
            else:
                segments = self._transcribe_local(record.audio_s3_key)

            full_transcript = " ".join(seg.text for seg in segments)
            record.status = RecordStatus.PROCESSED
            return AudioProcessingResult(
                record_id=record.record_id,
                full_transcript=full_transcript,
                segments=segments,
                status=RecordStatus.PROCESSED,
            )
        except Exception as e:
            logger.error("Audio processing failed for %s: %s", record.record_id, e)
            record.status = RecordStatus.PROCESSING_FAILED
            return AudioProcessingResult(
                record_id=record.record_id,
                status=RecordStatus.PROCESSING_FAILED,
                error=str(e),
            )

    def _transcribe_audio(self, s3_key: str, record_id: str) -> list[SpeakerSegment]:
        """Start a Transcribe job and poll for results."""
        import json
        import urllib.request

        job_name = f"feedback-{record_id}-{int(time.time())}"
        media_uri = s3_key if s3_key.startswith("s3://") else f"s3://{s3_key}"

        self._transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={"MediaFileUri": media_uri},
            MediaFormat="wav",
            LanguageCode="en-US",
            Settings={
                "ShowSpeakerLabels": True,
                "MaxSpeakerLabels": 5,
            },
        )

        # Poll for completion
        while True:
            status = self._transcribe.get_transcription_job(
                TranscriptionJobName=job_name
            )
            job_status = status["TranscriptionJob"]["TranscriptionJobStatus"]
            if job_status in ("COMPLETED", "FAILED"):
                break
            time.sleep(3)

        if job_status == "FAILED":
            reason = status["TranscriptionJob"].get("FailureReason", "unknown")
            raise RuntimeError(f"Transcription job {job_name} failed: {reason}")

        # Fetch the transcript JSON from the URI
        transcript_uri = status["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
        with urllib.request.urlopen(transcript_uri) as resp:
            transcript_data = json.loads(resp.read().decode("utf-8"))

        return self._parse_transcript(transcript_data)

    def _parse_transcript(self, transcript_data: dict) -> list[SpeakerSegment]:
        """Parse Transcribe JSON output into SpeakerSegment objects.

        Transcribe returns speaker_labels.segments with item references (start_time/end_time)
        and a top-level items array with the actual words. We cross-reference them by time.
        """
        segments = []
        results = transcript_data.get("results", {})

        # Get the full transcript
        transcripts = results.get("transcripts", [])
        full_text = transcripts[0].get("transcript", "") if transcripts else ""

        # Build a lookup of words by start_time from the top-level items
        top_items = results.get("items", [])
        word_by_time: dict[str, str] = {}
        for item in top_items:
            if item.get("type") == "pronunciation" and item.get("start_time"):
                alts = item.get("alternatives", [])
                if alts:
                    word_by_time[item["start_time"]] = alts[0].get("content", "")

        # Parse speaker label segments
        speaker_labels = results.get("speaker_labels", {})
        raw_segments = speaker_labels.get("segments", [])

        if raw_segments:
            for seg in raw_segments:
                # Build text by looking up each item's start_time in the word lookup
                words = []
                for item in seg.get("items", []):
                    st = item.get("start_time", "")
                    word = word_by_time.get(st, "")
                    if word:
                        words.append(word)

                seg_text = " ".join(words).strip()
                if seg_text:
                    segments.append(
                        SpeakerSegment(
                            speaker_label=seg.get("speaker_label", "spk_0"),
                            start_time=float(seg.get("start_time", 0)),
                            end_time=float(seg.get("end_time", 0)),
                            text=seg_text,
                        )
                    )
        elif full_text:
            # No speaker labels — return full transcript as single segment
            segments.append(
                SpeakerSegment(
                    speaker_label="spk_0",
                    start_time=0.0,
                    end_time=0.0,
                    text=full_text,
                )
            )

        return segments

    # ------------------------------------------------------------------
    # Local fallback for demo without AWS credentials
    # ------------------------------------------------------------------

    def _transcribe_local(self, s3_key: str) -> list[SpeakerSegment]:
        """Simulated transcription for demo."""
        key_lower = s3_key.lower()
        if "complaint" in key_lower or "angry" in key_lower:
            return [
                SpeakerSegment(
                    speaker_label="spk_0",
                    start_time=0.0,
                    end_time=8.5,
                    text="I've been waiting for two weeks for my order and nobody has given me an update.",
                ),
                SpeakerSegment(
                    speaker_label="spk_1",
                    start_time=9.0,
                    end_time=15.2,
                    text="I'm sorry to hear that. Let me look into your order right away.",
                ),
                SpeakerSegment(
                    speaker_label="spk_0",
                    start_time=15.8,
                    end_time=22.0,
                    text="This is the third time I've called about this. The package was supposed to arrive last Monday.",
                ),
                SpeakerSegment(
                    speaker_label="spk_1",
                    start_time=22.5,
                    end_time=30.0,
                    text="I completely understand your frustration. I can see the shipment was delayed at the distribution center. Let me escalate this for priority delivery.",
                ),
            ]
        else:
            return [
                SpeakerSegment(
                    speaker_label="spk_0",
                    start_time=0.0,
                    end_time=6.0,
                    text="Hi, I'm calling about the product I received yesterday. It's working great but I had a question about the warranty.",
                ),
                SpeakerSegment(
                    speaker_label="spk_1",
                    start_time=6.5,
                    end_time=14.0,
                    text="Thank you for calling. I'd be happy to help with warranty information. Your product comes with a two-year standard warranty.",
                ),
                SpeakerSegment(
                    speaker_label="spk_0",
                    start_time=14.5,
                    end_time=20.0,
                    text="That's great to hear. And can I extend it? The product quality is excellent and I want to keep it protected.",
                ),
                SpeakerSegment(
                    speaker_label="spk_1",
                    start_time=20.5,
                    end_time=28.0,
                    text="Absolutely. We offer an extended warranty program for an additional year. I can set that up for you right now.",
                ),
            ]
