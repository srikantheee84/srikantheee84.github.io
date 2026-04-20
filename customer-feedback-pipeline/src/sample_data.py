"""Sample feedback data for the demo.

Text reviews, survey responses, and invalid records are defined here.
Image and audio records are discovered from samples/images/ and samples/audio/.
When running with --use-aws, pass an S3 bucket so the image/audio records
point to real S3 keys. Without it, they use local placeholder paths.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.models import DataType, FeedbackRecord

SAMPLES_DIR = Path(__file__).parent.parent / "samples"
S3_PREFIX = "customer-feedback-pipeline"


def _recent_timestamp(days_ago: int = 5) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.isoformat()


def _discover_images(s3_bucket: str | None = None) -> list[FeedbackRecord]:
    """Build image FeedbackRecords from files in samples/images/."""
    images_dir = SAMPLES_DIR / "images"
    if not images_dir.exists():
        return []

    records = []
    for i, path in enumerate(sorted(images_dir.glob("*.jpg")), start=1):
        record_id = f"IMG-{i:03d}"
        if s3_bucket:
            key = f"s3://{s3_bucket}/{S3_PREFIX}/images/{path.name}"
        else:
            key = f"samples/images/{path.name}"

        records.append(FeedbackRecord(
            record_id=record_id,
            customer_id=f"CUST-{2000 + i}",
            timestamp=_recent_timestamp(i),
            channel="web",
            data_type=DataType.IMAGE,
            image_s3_key=key,
        ))
    return records


def _discover_audio(s3_bucket: str | None = None) -> list[FeedbackRecord]:
    """Build audio FeedbackRecords from files in samples/audio/."""
    audio_dir = SAMPLES_DIR / "audio"
    if not audio_dir.exists():
        return []

    records = []
    for i, path in enumerate(sorted(audio_dir.glob("*.wav")), start=1):
        record_id = f"AUD-{i:03d}"
        if s3_bucket:
            key = f"s3://{s3_bucket}/{S3_PREFIX}/audio/{path.name}"
        else:
            key = f"samples/audio/{path.name}"

        records.append(FeedbackRecord(
            record_id=record_id,
            customer_id=f"CUST-{3000 + i}",
            timestamp=_recent_timestamp(i),
            channel="phone",
            data_type=DataType.AUDIO,
            audio_s3_key=key,
        ))
    return records


# --- Text reviews ---
_TEXT_REVIEWS = [
    (4, "email", "Great experience with the customer service team. Sarah at the Austin store helped me resolve my issue in under 10 minutes. The product quality is excellent and I would definitely recommend it to friends."),
    (2, "web", "Disappointed with the shipping experience. My order took 14 days to arrive when the estimate was 3-5 business days. The product itself is fine but the packaging was damaged and the box was crushed. I expected better from a company of this size."),
    (5, "email", "Absolutely love the new Premium Package. The build quality is fantastic and the setup was straightforward. The included documentation made it easy to get started. Best purchase I have made this year."),
    (1, "web", "Terrible experience. Product arrived broken and customer support kept me waiting on hold for 45 minutes. When I finally got through, the agent was rude and unhelpful. I want a full refund. Never ordering from here again."),
    (3, "email", "The product is decent for the price point. Nothing exceptional but it gets the job done. Delivery was on time. Would be nice if the warranty was longer than one year. Competitors offer two years at a similar price."),
    (5, "web", "Outstanding quality and fast delivery. The packaging was secure and the product was exactly as described. Marcus from the support team followed up to make sure everything was working. That kind of attention to detail is rare these days."),
    (2, "email", "Ordered the Pro model based on the website description but what I received feels like the basic version. The materials are cheaper than expected and the finish has visible scratches. Contacted support and they said it is within spec. Very disappointing for the price I paid."),
    (4, "web", "Good product overall. Setup took about 20 minutes which was reasonable. The mobile app integration works well and the notifications are helpful. Only complaint is the instruction manual could be clearer. Had to watch a YouTube video to figure out the WiFi setup."),
    (1, "email", "This is the second defective unit I have received. First one had a cracked screen, replacement has a faulty power button. Quality control at the factory must be nonexistent. I have wasted hours dealing with returns and I am done. Requesting a full refund through my credit card company."),
    (3, "web", "Mixed feelings. The core functionality works great and battery life is impressive. However the accessory ecosystem is limited compared to competitors. Tried to find a compatible case and there are only two options available. For a product at this price point I expected more third-party support."),
    (5, "email", "Upgraded from the previous generation and the difference is night and day. Performance is noticeably faster, the display is sharper, and the new features actually add value instead of being gimmicks. Worth every penny of the upgrade price."),
    (2, "web", "Delivery driver left the package in the rain even though I have a covered porch. Box was soaked through and the product inside had water spots on it. Filed a complaint with the shipping company but they said it was delivered successfully. The product works but the experience left a bad taste."),
    (4, "email", "Solid product with good build quality. The customer loyalty discount was a nice touch. Jen from the Chicago support center helped me pick the right model for my needs. Appreciate the personalized service rather than just pushing the most expensive option."),
    (3, "web", "Returns process needs work. Took three weeks to get my refund after returning a defective item. Had to call twice to get status updates. The replacement product is fine but the hassle of the return almost made me switch to a competitor."),
    (4, "email", "Been using the product daily for two weeks now and it holds up well. Battery still lasts a full day with heavy use. The software updates have been frequent and actually fix issues rather than introducing new ones. Refreshing to see a company that supports their products post-purchase."),
]

# --- Survey responses ---
_SURVEYS = [
    {"q1": 4, "q2": 2, "q3": 5, "q4": 4, "comment": "Shipping was slow but the product exceeded expectations. Would buy again."},
    {"q1": 3, "q2": 3, "q3": 3, "q4": 3, "comment": "Average experience overall. Nothing stood out positively or negatively."},
    {"q1": 5, "q2": 5, "q3": 5, "q4": 5, "comment": "Everything was perfect from ordering to delivery. The product works flawlessly and the support team was proactive in following up."},
    {"q1": 1, "q2": 1, "q3": 2, "q4": 1, "comment": "Worst online shopping experience I have ever had. Package arrived two weeks late, product was damaged, and support was useless. Will never order again."},
    {"q1": 4, "q2": 4, "q3": 4, "q4": 3, "comment": "Good product and reasonable delivery time. Support was okay but took a while to respond to my email. Would appreciate faster response times."},
    {"q1": 2, "q2": 1, "q3": 3, "q4": 2, "comment": "Delivery was a disaster. Package left in the rain, no notification, and when I called support they blamed the carrier. Take responsibility for your shipping partners."},
    {"q1": 4, "q2": 3, "q3": 5, "q4": 4, "comment": "Product quality is top notch. Delivery could be faster but not a dealbreaker. The loyalty program discount was a nice surprise at checkout."},
    {"q1": 3, "q2": 4, "q3": 2, "q4": 3, "comment": "Delivery was fine but the product feels cheaper than the photos suggested. The materials do not match the premium branding. Considering a return."},
]


def _build_survey(index: int, data: dict) -> FeedbackRecord:
    return FeedbackRecord(
        record_id=f"SRV-{index:03d}",
        customer_id=f"CUST-{4000 + index}",
        timestamp=_recent_timestamp(index),
        channel="survey",
        data_type=DataType.SURVEY,
        survey_responses=[
            {"question_id": "Q1", "question_text": "Overall satisfaction (1-5)", "type": "numeric", "answer": data["q1"]},
            {"question_id": "Q2", "question_text": "Delivery experience (1-5)", "type": "numeric", "answer": data["q2"]},
            {"question_id": "Q3", "question_text": "Product quality (1-5)", "type": "numeric", "answer": data["q3"]},
            {"question_id": "Q4", "question_text": "Customer support experience (1-5)", "type": "numeric", "answer": data["q4"]},
            {"question_id": "Q5", "question_text": "Any additional comments?", "type": "free_text", "answer": data["comment"]},
        ],
    )


# --- Invalid records (for validation demo) ---
def _invalid_records() -> list[FeedbackRecord]:
    return [
        FeedbackRecord(record_id="BAD-001", customer_id="", timestamp=_recent_timestamp(1), channel="web", data_type=DataType.TEXT, text="This should fail validation — missing customer ID."),
        FeedbackRecord(record_id="BAD-002", customer_id="CUST-9998", timestamp="2025-01-01T00:00:00+00:00", channel="email", data_type=DataType.TEXT, text="This should fail validation — timestamp too old."),
        FeedbackRecord(record_id="TXT-001", customer_id="CUST-9999", timestamp=_recent_timestamp(1), channel="web", data_type=DataType.TEXT, text="This should fail validation — duplicate record ID."),
    ]


def load_sample_records(s3_bucket: str | None = None) -> list[FeedbackRecord]:
    """Load all sample records.

    Text, survey, and invalid records are defined inline.
    Image and audio records are discovered from samples/images/ and samples/audio/.
    Pass s3_bucket to point image/audio keys to real S3 paths.
    """
    records: list[FeedbackRecord] = []

    # Text reviews
    for i, (rating, channel, text) in enumerate(_TEXT_REVIEWS, start=1):
        records.append(FeedbackRecord(
            record_id=f"TXT-{i:03d}",
            customer_id=f"CUST-{1000 + i}",
            timestamp=_recent_timestamp(i % 7 + 1),
            channel=channel,
            data_type=DataType.TEXT,
            rating=rating,
            text=text,
        ))

    # Images — discovered from filesystem
    records.extend(_discover_images(s3_bucket))

    # Audio — discovered from filesystem
    records.extend(_discover_audio(s3_bucket))

    # Surveys
    for i, data in enumerate(_SURVEYS, start=1):
        records.append(_build_survey(i, data))

    # Invalid records
    records.extend(_invalid_records())

    return records
