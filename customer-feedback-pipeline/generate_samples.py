#!/usr/bin/env python3
"""
Generate real sample files for the Customer Feedback Pipeline.

Creates:
  - Real images with realistic layouts (receipts, feedback forms, product labels)
  - Real speech audio via Amazon Polly (actual spoken customer feedback)
  - Text files with customer reviews

Usage:
  python generate_samples.py                          # Generate locally (images + text only)
  python generate_samples.py --upload --bucket NAME   # Generate all + upload to S3
  python generate_samples.py --with-polly --bucket X  # Include Polly speech generation
"""

import argparse
import json
import os
import struct
import sys
import wave
from pathlib import Path

SAMPLES_DIR = Path(__file__).parent / "samples"
S3_PREFIX = "customer-feedback-pipeline"


# ---------------------------------------------------------------------------
# Image generation — realistic documents and scenes
# ---------------------------------------------------------------------------

RECEIPT_LINES = [
    ("                ACME ELECTRONICS", "title"),
    ("           Downtown Branch - Austin, TX", "subtitle"),
    ("           123 Main Street, Suite 200", "subtitle"),
    ("", "spacer"),
    ("  Date: 03/15/2026          Time: 14:32", "normal"),
    ("  Cashier: Sarah C.        Register: 04", "normal"),
    ("  Transaction: TXN-2026-88421", "normal"),
    ("  ─────────────────────────────────────", "divider"),
    ("  Widget Pro X (1)            $149.99", "normal"),
    ("  Premium Case                 $29.99", "normal"),
    ("  Screen Protector              $9.99", "normal"),
    ("  ─────────────────────────────────────", "divider"),
    ("  Subtotal                    $189.97", "normal"),
    ("  Tax (8.25%)                  $15.67", "normal"),
    ("  Loyalty Discount (-10%)     -$19.00", "highlight"),
    ("  ─────────────────────────────────────", "divider"),
    ("  TOTAL                       $186.64", "bold"),
    ("  ─────────────────────────────────────", "divider"),
    ("  Payment: VISA ****1234      $186.64", "normal"),
    ("  Auth Code: 847291", "normal"),
    ("", "spacer"),
    ("       Thank you for shopping!", "subtitle"),
    ("    Loyalty Points Earned: 187 pts", "subtitle"),
    ("   Returns accepted within 30 days", "small"),
    ("      with receipt. Visit us at", "small"),
    ("     www.acme-electronics.example", "small"),
]

FEEDBACK_FORM_LINES = [
    ("    ╔══════════════════════════════════╗", "border"),
    ("    ║   CUSTOMER FEEDBACK FORM         ║", "border"),
    ("    ╚══════════════════════════════════╝", "border"),
    ("", "spacer"),
    ("  Name:    James Rodriguez", "normal"),
    ("  Email:   [REDACTED]", "normal"),
    ("  Date:    April 14, 2026", "normal"),
    ("  Order:   ORD-2026-8834", "normal"),
    ("  Product: Widget Pro X", "normal"),
    ("", "spacer"),
    ("  Rating:  ★ ☆ ☆ ☆ ☆  (1 out of 5)", "highlight"),
    ("", "spacer"),
    ("  Comments:", "normal"),
    ("  Product arrived with cracked screen.", "normal"),
    ("  Packaging was completely crushed.", "normal"),
    ("  Waited 45 min on hold for support.", "normal"),
    ("  Agent was unhelpful and dismissive.", "normal"),
    ("  Requesting full refund immediately.", "normal"),
    ("", "spacer"),
    ("  ─────────────────────────────────────", "divider"),
    ("  Category: Product Damage / Shipping", "small"),
    ("  Priority: HIGH", "highlight"),
    ("  Status:   Pending Review", "small"),
]

SHIPPING_LABEL_LINES = [
    ("  ┌─────────────────────────────────┐", "border"),
    ("  │  SHIPPING LABEL                 │", "border"),
    ("  └─────────────────────────────────┘", "border"),
    ("", "spacer"),
    ("  FROM: ACME Electronics Warehouse", "normal"),
    ("        500 Commerce Dr, Dallas TX", "normal"),
    ("", "spacer"),
    ("  TO:   Customer CUST-2001", "normal"),
    ("        [ADDRESS REDACTED]", "normal"),
    ("", "spacer"),
    ("  ─────────────────────────────────────", "divider"),
    ("  Tracking: PKG-2026-4421", "bold"),
    ("  Weight:   2.4 lbs", "normal"),
    ("  Ship Date: 04/01/2026", "normal"),
    ("  Est. Delivery: 04/05/2026", "normal"),
    ("  ─────────────────────────────────────", "divider"),
    ("  *** FRAGILE - HANDLE WITH CARE ***", "highlight"),
    ("  ─────────────────────────────────────", "divider"),
    ("  Carrier: FastShip Express", "normal"),
    ("  Service: Standard Ground", "normal"),
    ("  Insurance: $200.00", "small"),
    ("", "spacer"),
    ("  NOTICE: Package shows signs of", "highlight"),
    ("  damage. Dents visible on corners.", "highlight"),
    ("  Tape partially torn on arrival.", "highlight"),
]

WARRANTY_CARD_LINES = [
    ("  ╔══════════════════════════════════╗", "border"),
    ("  ║     WARRANTY REGISTRATION        ║", "border"),
    ("  ╚══════════════════════════════════╝", "border"),
    ("", "spacer"),
    ("  Product:  Widget Pro X", "normal"),
    ("  Model:    WPX-2026-PRO", "normal"),
    ("  Serial:   SN-88421-A7", "normal"),
    ("  Purchase: 03/15/2026", "normal"),
    ("", "spacer"),
    ("  WARRANTY COVERAGE:", "bold"),
    ("  Standard: 1 year parts & labor", "normal"),
    ("  Extended: Available (add 1 year)", "normal"),
    ("  Extended Price: $24.99", "normal"),
    ("", "spacer"),
    ("  COVERED:", "normal"),
    ("  - Manufacturing defects", "normal"),
    ("  - Component failure", "normal"),
    ("  - Battery degradation >20%", "normal"),
    ("", "spacer"),
    ("  NOT COVERED:", "normal"),
    ("  - Physical damage / drops", "normal"),
    ("  - Water damage", "normal"),
    ("  - Unauthorized modifications", "normal"),
    ("", "spacer"),
    ("  Register at: warranty.acme.example", "small"),
    ("  Support: 1-800-555-ACME", "small"),
]

RETURN_FORM_LINES = [
    ("  ┌─────────────────────────────────┐", "border"),
    ("  │     RETURN AUTHORIZATION        │", "border"),
    ("  └─────────────────────────────────┘", "border"),
    ("", "spacer"),
    ("  RMA Number:  RMA-2026-1147", "bold"),
    ("  Order:       ORD-2026-8834", "normal"),
    ("  Customer:    James Rodriguez", "normal"),
    ("  Date Filed:  04/14/2026", "normal"),
    ("", "spacer"),
    ("  ITEM:", "normal"),
    ("  Widget Pro X (Qty: 1)    $149.99", "normal"),
    ("  Reason: Arrived damaged", "normal"),
    ("  Condition: Cracked screen", "normal"),
    ("", "spacer"),
    ("  REFUND METHOD: Original payment", "normal"),
    ("  Est. Processing: 5-7 business days", "normal"),
    ("", "spacer"),
    ("  ─────────────────────────────────────", "divider"),
    ("  INSTRUCTIONS:", "bold"),
    ("  1. Pack item in original box", "normal"),
    ("  2. Include this form inside", "normal"),
    ("  3. Attach prepaid label (enclosed)", "normal"),
    ("  4. Drop off at any FastShip location", "normal"),
    ("  ─────────────────────────────────────", "divider"),
    ("  Questions? Call 1-800-555-ACME", "small"),
]

PRODUCT_SPEC_LINES = [
    ("  ╔══════════════════════════════════╗", "border"),
    ("  ║   PRODUCT SPECIFICATIONS         ║", "border"),
    ("  ╚══════════════════════════════════╝", "border"),
    ("", "spacer"),
    ("  Widget Pro X — Premium Package", "bold"),
    ("  Model: WPX-2026-PRO", "normal"),
    ("  Color: Midnight Black", "normal"),
    ("", "spacer"),
    ("  SPECIFICATIONS:", "bold"),
    ("  Display:   6.7 inch OLED, 2400x1080", "normal"),
    ("  Processor: Octa-core 3.2 GHz", "normal"),
    ("  Memory:    8 GB RAM / 256 GB Storage", "normal"),
    ("  Battery:   5000 mAh, fast charging", "normal"),
    ("  Camera:    48MP main + 12MP ultra", "normal"),
    ("  OS:        Android 15", "normal"),
    ("", "spacer"),
    ("  IN THE BOX:", "bold"),
    ("  - Widget Pro X device", "normal"),
    ("  - USB-C charging cable", "normal"),
    ("  - Quick Start Guide", "normal"),
    ("  - Premium protective case", "normal"),
    ("  - Screen protector (pre-applied)", "normal"),
    ("", "spacer"),
    ("  MSRP: $149.99", "bold"),
    ("  Made in Taiwan | Designed in Austin", "small"),
]

SATISFACTION_SURVEY_LINES = [
    ("  ╔══════════════════════════════════╗", "border"),
    ("  ║  CUSTOMER SATISFACTION SURVEY    ║", "border"),
    ("  ╚══════════════════════════════════╝", "border"),
    ("", "spacer"),
    ("  Customer: CUST-4001", "normal"),
    ("  Date:     04/16/2026", "normal"),
    ("  Order:    ORD-2026-7721", "normal"),
    ("", "spacer"),
    ("  Q1. Overall satisfaction:", "normal"),
    ("       ★ ★ ★ ★ ☆  (4/5)", "highlight"),
    ("  Q2. Delivery experience:", "normal"),
    ("       ★ ★ ☆ ☆ ☆  (2/5)", "highlight"),
    ("  Q3. Product quality:", "normal"),
    ("       ★ ★ ★ ★ ★  (5/5)", "highlight"),
    ("  Q4. Customer support:", "normal"),
    ("       ★ ★ ★ ★ ☆  (4/5)", "highlight"),
    ("", "spacer"),
    ("  Comments:", "normal"),
    ("  Shipping was slow but the product", "normal"),
    ("  exceeded expectations. Would buy", "normal"),
    ("  again. Great build quality.", "normal"),
    ("", "spacer"),
    ("  ─────────────────────────────────────", "divider"),
    ("  Thank you for your feedback!", "subtitle"),
]


def generate_images():
    """Generate realistic document images with proper layouts."""
    from PIL import Image, ImageDraw, ImageFont

    images_dir = SAMPLES_DIR / "images"
    images_dir.mkdir(exist_ok=True)

    # Try system fonts
    try:
        font_title = ImageFont.truetype("/System/Library/Fonts/Courier.dfont", 22)
        font_normal = ImageFont.truetype("/System/Library/Fonts/Courier.dfont", 18)
        font_small = ImageFont.truetype("/System/Library/Fonts/Courier.dfont", 14)
        font_bold = ImageFont.truetype("/System/Library/Fonts/Courier.dfont", 20)
    except (OSError, IOError):
        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 22)
            font_normal = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 18)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 14)
            font_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 20)
        except (OSError, IOError):
            font_title = font_normal = font_small = font_bold = ImageFont.load_default()

    font_map = {
        "title": font_title,
        "subtitle": font_normal,
        "normal": font_normal,
        "small": font_small,
        "bold": font_bold,
        "highlight": font_bold,
        "border": font_normal,
        "divider": font_normal,
        "spacer": font_normal,
    }

    color_map = {
        "title": (20, 20, 20),
        "subtitle": (80, 80, 80),
        "normal": (40, 40, 40),
        "small": (100, 100, 100),
        "bold": (10, 10, 10),
        "highlight": (180, 40, 40),
        "border": (60, 60, 60),
        "divider": (150, 150, 150),
        "spacer": (0, 0, 0),
    }

    image_specs = [
        ("damaged-package-001.jpg", SHIPPING_LABEL_LINES, (250, 240, 220), "Shipping label with damage notes"),
        ("receipt-002.jpg", RECEIPT_LINES, (252, 250, 245), "Store receipt"),
        ("product-003.jpg", PRODUCT_SPEC_LINES, (245, 245, 250), "Product spec sheet"),
        ("broken-screen-004.jpg", RETURN_FORM_LINES, (255, 250, 245), "Return authorization form"),
        ("setup-complete-005.jpg", SATISFACTION_SURVEY_LINES, (248, 250, 248), "Satisfaction survey"),
        ("wrong-color-006.jpg", FEEDBACK_FORM_LINES, (250, 248, 245), "Customer feedback form"),
        ("unboxing-007.jpg", WARRANTY_CARD_LINES, (250, 252, 248), "Warranty registration card"),
    ]

    created = []
    for filename, lines, bg_color, desc in image_specs:
        # Calculate image height based on content
        height = max(600, len(lines) * 26 + 80)
        img = Image.new("RGB", (700, height), bg_color)
        draw = ImageDraw.Draw(img)

        # Subtle paper texture — add slight noise
        import random
        random.seed(hash(filename))
        for _ in range(2000):
            x = random.randint(0, 699)
            y = random.randint(0, height - 1)
            offset = random.randint(-8, 8)
            c = tuple(max(0, min(255, v + offset)) for v in bg_color)
            draw.point((x, y), fill=c)

        # Draw text lines
        y = 30
        for text, style in lines:
            if style == "spacer":
                y += 12
                continue
            font = font_map.get(style, font_normal)
            color = color_map.get(style, (40, 40, 40))
            draw.text((20, y), text, fill=color, font=font)
            y += 26

        filepath = images_dir / filename
        img.save(filepath, "JPEG", quality=90)
        created.append(filepath)
        size_kb = filepath.stat().st_size / 1024
        print(f"  Created: samples/images/{filename} ({size_kb:.0f} KB) — {desc}")

    return created


# ---------------------------------------------------------------------------
# Audio generation — real speech via Amazon Polly
# ---------------------------------------------------------------------------

# Customer service call scripts — two speakers per call
CALL_SCRIPTS = {
    "complaint-call-001.wav": [
        ("Matthew", "I've been waiting for two weeks for my order and nobody has given me an update. This is completely unacceptable."),
        ("Joanna", "I'm so sorry to hear about the delay. Let me pull up your order right away and find out what happened."),
        ("Matthew", "This is the third time I've called about this. The package was supposed to arrive last Monday. I took the day off work to be home for the delivery."),
        ("Joanna", "I completely understand your frustration. I can see the shipment was delayed at the distribution center due to a processing error. Let me escalate this for priority delivery. You should receive it within two business days."),
    ],
    "warranty-inquiry-002.wav": [
        ("Matthew", "Hi, I'm calling about the product I received yesterday. It's working great but I had a question about the warranty coverage."),
        ("Joanna", "Thank you for calling. I'd be happy to help with warranty information. Your Widget Pro X comes with a standard one year warranty covering parts and labor."),
        ("Matthew", "That's good to know. Can I extend it? The product quality is excellent and I want to keep it protected for longer."),
        ("Joanna", "Absolutely. We offer an extended warranty program that adds an additional year of coverage for twenty four ninety nine. I can set that up for you right now if you'd like."),
    ],
    "return-request-003.wav": [
        ("Matthew", "I need to return a product. This is actually the second defective unit I've received. The first one had a cracked screen and the replacement has a faulty power button."),
        ("Joanna", "I'm very sorry about that experience. That's definitely not the quality we aim for. Let me process a return and full refund for you right away."),
        ("Matthew", "I appreciate that. But honestly, I've wasted hours dealing with returns at this point. Your quality control needs serious improvement."),
        ("Joanna", "You're absolutely right, and I apologize for the inconvenience. I'm issuing a full refund plus a fifteen percent discount code for your next purchase. I'm also flagging this product batch for our quality team to investigate."),
    ],
    "positive-feedback-004.wav": [
        ("Matthew", "I just wanted to call and say how impressed I am with the Premium Package. The build quality is fantastic and the setup was incredibly easy."),
        ("Joanna", "That's wonderful to hear! Thank you so much for taking the time to share that feedback. We really appreciate it."),
        ("Matthew", "Also, Marcus from your support team helped me pick the right model. That kind of personalized service is rare these days. You should recognize him."),
        ("Joanna", "I'll definitely pass that along to his manager. Feedback like yours makes a real difference. Is there anything else I can help you with today?"),
    ],
    "billing-dispute-005.wav": [
        ("Matthew", "I'm looking at my credit card statement and I see two charges for the same order. One for one eighty six sixty four and another for one forty nine ninety nine. I should only have one charge."),
        ("Joanna", "Let me look into that for you. Can you confirm your order number? I'll check our billing system."),
        ("Matthew", "It's O R D twenty twenty six eighty eight thirty four. The second charge appeared three days after the first one."),
        ("Joanna", "I found the issue. The second charge was a pre-authorization that should have been released automatically. I'm processing a reversal right now. You should see the credit on your statement within three to five business days. I apologize for the confusion."),
    ],
}


def generate_audio_polly(region: str):
    """Generate real speech audio using Amazon Polly."""
    import boto3

    audio_dir = SAMPLES_DIR / "audio"
    audio_dir.mkdir(exist_ok=True)

    polly = boto3.client("polly", region_name=region)
    created = []

    for filename, script in CALL_SCRIPTS.items():
        filepath = audio_dir / filename

        # Combine all lines into SSML with pauses between speakers
        ssml_parts = ['<speak>']
        for voice_id, text in script:
            # Add a pause between speakers to simulate conversation
            ssml_parts.append(f'<break time="800ms"/>')
            ssml_parts.append(text)
            ssml_parts.append(f'<break time="500ms"/>')
        ssml_parts.append('</speak>')
        ssml = "".join(ssml_parts)

        # Use a single voice for the combined audio (Polly doesn't mix voices in one call)
        # We'll use plain text concatenation instead for simplicity
        all_text = " ... ".join(text for _, text in script)

        try:
            response = polly.synthesize_speech(
                Text=all_text,
                OutputFormat="pcm",
                SampleRate="16000",
                VoiceId="Joanna",
                Engine="neural",
            )

            # Read the PCM audio stream
            pcm_data = response["AudioStream"].read()

            # Write as WAV
            with wave.open(str(filepath), "w") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(16000)
                wf.writeframes(pcm_data)

            size_kb = filepath.stat().st_size / 1024
            created.append(filepath)
            print(f"  Created: samples/audio/{filename} ({size_kb:.0f} KB) — Polly neural speech")

        except Exception as e:
            print(f"  FAILED: samples/audio/{filename} — {e}")
            # Fall back to tone generation
            _generate_tone_fallback(filepath)
            created.append(filepath)

    return created


def _generate_tone_fallback(filepath: Path):
    """Fallback: generate a simple tone WAV if Polly fails."""
    import math
    sample_rate = 16000
    duration = 5
    n_samples = sample_rate * duration
    samples = []
    for i in range(n_samples):
        t = i / sample_rate
        value = int(8000 * math.sin(2 * math.pi * 440 * t))
        samples.append(struct.pack("<h", value))
    with wave.open(str(filepath), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(samples))
    print(f"  Created: {filepath.name} (tone fallback)")


def generate_audio_local():
    """Generate placeholder WAV files without Polly (for offline use)."""
    import math
    audio_dir = SAMPLES_DIR / "audio"
    audio_dir.mkdir(exist_ok=True)
    created = []

    for filename in CALL_SCRIPTS:
        filepath = audio_dir / filename
        _generate_tone_fallback(filepath)
        created.append(filepath)

    return created


# ---------------------------------------------------------------------------
# Text file generation
# ---------------------------------------------------------------------------

def generate_text_files():
    """Generate plain text feedback files."""
    text_dir = SAMPLES_DIR / "text"
    text_dir.mkdir(exist_ok=True)

    text_specs = [
        {
            "filename": "review-positive-001.txt",
            "content": (
                "Customer Feedback - Email Submission\n"
                "Date: 2026-04-15\n"
                "Customer: Sarah Chen\n"
                "Location: Austin, TX\n"
                "Rating: 5/5\n\n"
                "Great experience with the customer service team. Sarah at the Austin store "
                "helped me resolve my issue in under 10 minutes. The product quality is "
                "excellent and I would definitely recommend it to friends and family. "
                "The Premium Package exceeded all my expectations."
            ),
        },
        {
            "filename": "review-negative-002.txt",
            "content": (
                "Customer Feedback - Web Form\n"
                "Date: 2026-04-14\n"
                "Customer: James Rodriguez\n"
                "Order: ORD-2026-8834\n"
                "Rating: 1/5\n\n"
                "Terrible experience. Product arrived broken and customer support kept me "
                "waiting on hold for 45 minutes. When I finally got through, the agent "
                "was rude and unhelpful. The packaging was completely crushed and the "
                "screen had a visible crack. I want a full refund. Never ordering again."
            ),
        },
        {
            "filename": "review-mixed-003.txt",
            "content": (
                "Customer Feedback - Email Submission\n"
                "Date: 2026-04-13\n"
                "Customer: Maria Lopez\n"
                "Location: Chicago, IL\n"
                "Rating: 3/5\n\n"
                "Mixed feelings about this purchase. The core functionality works great "
                "and battery life is impressive at over 12 hours. However the delivery "
                "took 14 days instead of the promised 3-5 business days. The warranty "
                "is only one year while competitors like TechCorp Inc offer two years. "
                "Decent product but the overall experience needs improvement."
            ),
        },
    ]

    created = []
    for spec in text_specs:
        filepath = text_dir / spec["filename"]
        filepath.write_text(spec["content"])
        created.append(filepath)
        print(f"  Created: samples/text/{spec['filename']}")

    return created


# ---------------------------------------------------------------------------
# S3 upload + JSONL update
# ---------------------------------------------------------------------------

def upload_to_s3(files: list, bucket: str, region: str):
    """Upload generated files to S3."""
    import boto3
    s3 = boto3.client("s3", region_name=region)

    for filepath in files:
        rel = filepath.relative_to(SAMPLES_DIR)
        s3_key = f"{S3_PREFIX}/{rel}"

        content_type = "application/octet-stream"
        if filepath.suffix == ".jpg":
            content_type = "image/jpeg"
        elif filepath.suffix == ".wav":
            content_type = "audio/wav"
        elif filepath.suffix == ".txt":
            content_type = "text/plain"

        s3.upload_file(str(filepath), bucket, s3_key, ExtraArgs={"ContentType": content_type})
        print(f"  Uploaded: s3://{bucket}/{s3_key}")


def update_jsonl_s3_keys(bucket: str):
    """Update JSONL sample files to point to real S3 keys."""
    for jsonl_name, key_field, subfolder in [
        ("image_feedback.jsonl", "image_s3_key", "images"),
        ("audio_feedback.jsonl", "audio_s3_key", "audio"),
    ]:
        jsonl_path = SAMPLES_DIR / jsonl_name
        if not jsonl_path.exists():
            continue

        lines = []
        with open(jsonl_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                if data.get(key_field):
                    filename = data[key_field].split("/")[-1]
                    data[key_field] = f"s3://{bucket}/{S3_PREFIX}/{subfolder}/{filename}"
                lines.append(json.dumps(data))

        with open(jsonl_path, "w") as f:
            f.write("\n".join(lines) + "\n")
        print(f"  Updated: {jsonl_name} with real S3 keys")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate real sample files for the feedback pipeline")
    parser.add_argument("--upload", action="store_true", help="Upload to S3 after generating")
    parser.add_argument("--bucket", default=None, help="S3 bucket name")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--with-polly", action="store_true", help="Use Amazon Polly for real speech audio")
    args = parser.parse_args()

    if args.upload and not args.bucket:
        print("Error: --bucket is required when using --upload")
        sys.exit(1)

    print("=" * 55)
    print("  Generating Real Sample Files")
    print("=" * 55)

    # Images
    print("\n📷 Images (realistic documents for Textract/Rekognition):")
    image_files = generate_images()

    # Audio
    if args.with_polly:
        print("\n🎙️  Audio (Amazon Polly neural speech for Transcribe):")
        audio_files = generate_audio_polly(args.region)
    else:
        print("\n🎙️  Audio (placeholder tones — use --with-polly for real speech):")
        audio_files = generate_audio_local()

    # Text
    print("\n📝 Text files:")
    text_files = generate_text_files()

    all_files = image_files + audio_files + text_files
    print(f"\n✅ Total files generated: {len(all_files)}")

    # Upload
    if args.upload:
        print(f"\n☁️  Uploading to s3://{args.bucket}/{S3_PREFIX}/...")
        upload_to_s3(all_files, args.bucket, args.region)

        print("\n📋 Updating JSONL files with real S3 keys...")
        update_jsonl_s3_keys(args.bucket)

        print("\n🚀 Done! Run the full pipeline:")
        print(f"  python demo.py --from-files --use-aws --region {args.region}")
    else:
        print("\nFiles generated locally. To upload to S3:")
        print(f"  python generate_samples.py --with-polly --upload --bucket YOUR_BUCKET")


if __name__ == "__main__":
    main()
