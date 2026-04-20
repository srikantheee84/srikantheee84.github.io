#!/usr/bin/env python3
"""
Demo script for the Customer Feedback Pipeline.

Demonstrates the full flow: load sample data → validate → route by type →
process with purpose-built AI services → format for Bedrock → analyze with
Nova Lite.

This is Part 3 of the series. In Part 1 we processed text documents. In
Part 2 we added benchmarking and resilience. Here we handle four data types
— text, images, audio, and surveys — each routed to the right AWS AI service.

Prerequisites:
  1. AWS credentials configured (aws configure or env vars)
  2. Bedrock model access enabled for Nova Lite
     (AWS Console → Bedrock → Model access → Request access)

Usage:
  python demo.py                                          # local simulation
  python demo.py --use-aws --bucket YOUR_BUCKET           # real AWS services
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from src.models import DataType, RecordStatus
from src.pipeline import Pipeline, PipelineResult
from src.sample_data import load_sample_records


def print_header(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def print_step(step: str, total: str, description: str) -> None:
    print(f"[{step}/{total}] {description}")


def demo_load_data(s3_bucket: str | None = None) -> list:
    """Step 1: Load sample records."""
    print_step("1", "6", "Loading sample feedback records...")
    records = load_sample_records(s3_bucket=s3_bucket)

    type_counts = {}
    for r in records:
        type_counts[r.data_type.value] = type_counts.get(r.data_type.value, 0) + 1

    print(f"  Total records: {len(records)}")
    for dtype, count in sorted(type_counts.items()):
        print(f"    {dtype:>8}: {count}")
    return records


def demo_validate(result: PipelineResult) -> None:
    print_step("2", "6", "Validating records (Glue Data Quality rules)...")
    print(f"  Passed: {result.valid_records}/{result.total_records}")
    print(f"  Failed: {result.invalid_records}")

    failed = [v for v in result.validation_results if not v.is_valid]
    if failed:
        print("  Violations:")
        for v in failed:
            print(f"    {v.record_id}: {', '.join(v.rule_violations)}")


def demo_text_results(result: PipelineResult) -> None:
    if not result.text_results:
        return
    print(f"\n  Text Processing ({len(result.text_results)} records):")
    total_entities = sum(len(r.entities) for r in result.text_results)
    sentiments = {}
    for r in result.text_results:
        if r.sentiment:
            s = r.sentiment.sentiment
            sentiments[s] = sentiments.get(s, 0) + 1
    print(f"    Entities detected: {total_entities}")
    if sentiments:
        sentiment_str = ", ".join(f"{k.lower()}: {v}" for k, v in sorted(sentiments.items()))
        print(f"    Sentiment breakdown: {sentiment_str}")

    first = result.text_results[0]
    print(f"\n    Example — {first.record_id}:")
    print(f"      Text: \"{first.original_text[:80]}...\"")
    if first.entities:
        for e in first.entities[:3]:
            print(f"      Entity: {e.entity_type}: {e.text} ({e.confidence:.0%})")
    if first.sentiment:
        s = first.sentiment
        print(f"      Sentiment: {s.sentiment} (pos={s.positive:.0%}, neg={s.negative:.0%})")


def demo_image_results(result: PipelineResult) -> None:
    if not result.image_results:
        return
    total_text = sum(len(r.extracted_text) for r in result.image_results)
    total_labels = sum(len(r.labels) for r in result.image_results)
    print(f"\n  Image Processing ({len(result.image_results)} records):")
    print(f"    Text blocks extracted: {total_text}")
    print(f"    Labels detected: {total_labels}")

    first = result.image_results[0]
    print(f"\n    Example — {first.record_id}:")
    for tb in first.extracted_text[:3]:
        print(f"      OCR: \"{tb.text}\" ({tb.confidence:.1f}%)")
    for lb in first.labels[:3]:
        print(f"      Label: {lb.name} ({lb.confidence:.1f}%)")


def demo_audio_results(result: PipelineResult) -> None:
    if not result.audio_results:
        return
    total_segments = sum(len(r.segments) for r in result.audio_results)
    print(f"\n  Audio Processing ({len(result.audio_results)} records):")
    print(f"    Transcripts: {len(result.audio_results)}")
    print(f"    Speaker segments: {total_segments}")

    first = result.audio_results[0]
    print(f"\n    Example — {first.record_id}:")
    for seg in first.segments[:2]:
        text_preview = seg.text[:70] + "..." if len(seg.text) > 70 else seg.text
        print(
            f"      [{seg.speaker_label}] ({seg.start_time:.1f}s-{seg.end_time:.1f}s): "
            f"{text_preview}"
        )


def demo_survey_results(result: PipelineResult) -> None:
    if not result.survey_results:
        return
    sr = result.survey_results[0]
    print(f"\n  Survey Processing ({len(result.survey_results)} batch):")
    print(f"    Questions summarized: {len(sr.question_summaries)}")
    print(f"    Free-text responses: {len(sr.free_text_responses)}")

    for qs in sr.question_summaries[:3]:
        line = f"      {qs.question_text}: {qs.response_count} responses"
        if qs.mean_score is not None:
            line += f", mean={qs.mean_score:.1f}"
        print(line)


def demo_analysis(result: PipelineResult) -> None:
    print_step("6", "6", "Analyzing with Amazon Nova Lite...")
    if not result.analysis:
        print("  No analysis produced (insufficient data)")
        return

    a = result.analysis
    if a.error:
        print(f"  Error: {a.error}")
        return

    if a.themes:
        print("\n  Themes:")
        for i, theme in enumerate(a.themes, 1):
            print(f"    {i}. {theme}")

    if a.sentiment_summary:
        print(f"\n  Sentiment Summary:")
        words = a.sentiment_summary.split()
        line = "    "
        for word in words:
            if len(line) + len(word) + 1 > 74:
                print(line)
                line = "    " + word
            else:
                line += " " + word if line.strip() else "    " + word
        if line.strip():
            print(line)

    if a.recommendations:
        print(f"\n  Recommendations:")
        for i, rec in enumerate(a.recommendations, 1):
            print(f"    {i}. {rec}")


def main():
    parser = argparse.ArgumentParser(
        description="Demo: Customer Feedback Pipeline (Part 3)"
    )
    parser.add_argument("--region", default="us-east-1", help="AWS region (default: us-east-1)")
    parser.add_argument("--use-aws", action="store_true", help="Use real AWS services")
    parser.add_argument("--bucket", default=None, help="S3 bucket with sample images/audio (required for --use-aws image/audio processing)")
    args = parser.parse_args()

    print_header("Customer Feedback Pipeline — Demo")
    print(f"Region:   {args.region}")
    print(f"AWS mode: {'live' if args.use_aws else 'local simulation'}")
    if args.bucket:
        print(f"Bucket:   {args.bucket}")
    print("-" * 60)

    # Build AWS clients if requested
    bedrock = comprehend = textract = rekognition = transcribe = cw = None
    if args.use_aws:
        import boto3
        bedrock = boto3.client("bedrock-runtime", region_name=args.region)
        comprehend = boto3.client("comprehend", region_name=args.region)
        textract = boto3.client("textract", region_name=args.region)
        rekognition = boto3.client("rekognition", region_name=args.region)
        transcribe = boto3.client("transcribe", region_name=args.region)
        cw = boto3.client("cloudwatch", region_name=args.region)

    # Step 1: Load data (pass bucket so image/audio keys point to S3)
    records = demo_load_data(s3_bucket=args.bucket)

    # Step 2-6: Run pipeline
    print()
    pipeline = Pipeline(
        bedrock_client=bedrock,
        comprehend_client=comprehend,
        textract_client=textract,
        rekognition_client=rekognition,
        transcribe_client=transcribe,
        cloudwatch_client=cw,
    )
    result = pipeline.run(records)

    print()
    demo_validate(result)

    print()
    print_step("3", "6", "Processing text records (Amazon Comprehend)...")
    demo_text_results(result)

    print()
    print_step("4", "6", "Processing image records (Textract + Rekognition)...")
    demo_image_results(result)
    demo_audio_results(result)
    demo_survey_results(result)

    print()
    print_step("5", "6", "Formatting results for Bedrock Converse API...")
    msg_count = len(result.text_results) + len(result.image_results) + len(result.audio_results) + len(result.survey_results)
    print(f"  Messages prepared: {msg_count} data + 1 instruction")

    print()
    demo_analysis(result)

    # Summary
    print_header("Demo Complete")
    print(f"Pipeline processed {result.total_records} records in {result.processing_time_ms:.0f}ms")
    print()
    if not args.use_aws:
        print("This ran with local simulations. To use real AWS services:")
        print("  python demo.py --use-aws --bucket YOUR_BUCKET --region us-east-1")
    print()
    print("Next steps:")
    print("  - Generate sample files:  python generate_samples.py --with-polly --upload --bucket YOUR_BUCKET")
    print("  - Deploy to AWS:          ./deploy.sh your-s3-bucket-name")
    print("  - Part 4 replaces in-memory RAG with real vector stores")


if __name__ == "__main__":
    main()
