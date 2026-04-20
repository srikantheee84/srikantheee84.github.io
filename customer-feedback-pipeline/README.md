# Customer Feedback Pipeline

A multimodal customer feedback data pipeline that ingests text reviews, images, audio recordings, and survey responses — validates with AWS Glue Data Quality rules — processes through purpose-built AWS AI services — and analyzes with Amazon Nova Lite via the Bedrock Converse API.

This is **Part 3** of a hands-on series on building AI applications with AWS.

## Hey, I'm Srikanth 👋

I'm a cloud engineer at AWS based in Austin, Texas. In Part 1, we built an insurance claim processor — text in, structured data out. In Part 2, we added benchmarking, circuit breakers, and cross-region resilience. Both projects processed one data type: text.

Real customer feedback doesn't come in one format. It arrives as written reviews, photos of damaged products, phone call recordings, and survey responses. This project builds a pipeline that handles all of them.

Part 1's `ContentValidator` checked for missing fields and redacted PII. That was fine for structured text. This project replaces it with Glue Data Quality rules for structural validation and a Lambda quality scorer for content-level checks — the enterprise version of the same idea.

By the time you finish this project, you'll know how to validate diverse data types, route records to the right AWS AI service, and bring everything together for unified analysis with Bedrock.

Let's build it.

> Follow along on my blog: [blog.srikanthethiraj.com](https://blog.srikanthethiraj.com/)
> Connect with me: [LinkedIn](https://www.linkedin.com/in/srikanthethiraj/)

---

## Why This Matters — Before vs After

| | Basic Approach (Part 1) | With This System (Part 3) |
|---|---|---|
| **Data types** | Text only | Text, images, audio, surveys |
| **Validation** | `ContentValidator` — field checks + PII regex | Glue Data Quality rules + Lambda quality scorer |
| **AI services** | Bedrock only | Comprehend, Textract, Rekognition, Transcribe, SageMaker, Bedrock |
| **Processing** | Single pipeline for all documents | Processor-per-modality with routing |
| **Monitoring** | None | CloudWatch metrics, dashboards, alarms |
| **Data quality** | Pass/fail on required fields | Completeness + uniqueness + freshness + content scoring |

### The Pattern You're Learning

This project teaches a pattern for handling diverse data types in AI applications:

> **Ingest → Validate → Route → Process per modality → Format → Analyze**

Same approach works for medical intake (forms, X-rays, doctor notes), insurance claims (documents, photos, phone calls), or product reviews (text, images, video). The modalities change. The pattern doesn't.

## What You'll Learn

- How to validate data quality with Glue Data Quality rules (completeness, uniqueness, freshness)
- Lambda-based text quality scoring to filter low-quality feedback
- Amazon Comprehend for entity extraction and sentiment analysis
- Amazon Textract for image text extraction (OCR)
- Amazon Rekognition for image label detection
- Amazon Transcribe for audio-to-text with speaker diarization
- Survey data aggregation with response distributions and statistics
- Formatting multimodal results for the Bedrock Converse API
- Unified analysis with Amazon Nova Lite across all feedback types
- CloudWatch monitoring with dashboards and alarms

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Sample Feedback Data                        │
│         (text reviews, images, audio, surveys)                │
└──────────────────────────┬───────────────────────────────────┘
                           │
                    ┌──────▼──────────┐
                    │  Data Validator  │  Glue Data Quality rules:
                    │                  │  completeness, uniqueness,
                    │                  │  freshness
                    └──────┬──────────┘
                           │
                    ┌──────▼──────────┐
                    │ Quality Scorer  │  Lambda text quality check
                    │ (text only)     │  (length, diversity, content)
                    └──────┬──────────┘
                           │
              ┌────────────┼────────────┬────────────┐
              │            │            │            │
       ┌──────▼──────┐ ┌──▼────────┐ ┌▼──────────┐ ┌▼──────────┐
       │    Text      │ │  Image    │ │  Audio    │ │  Survey   │
       │  Processor   │ │ Processor │ │ Processor │ │ Processor │
       │ (Comprehend) │ │(Textract +│ │(Transcribe│ │(SageMaker │
       │              │ │Rekognition│ │           │ │Processing)│
       └──────┬───────┘ └─────┬─────┘ └─────┬────┘ └─────┬─────┘
              │               │              │            │
              └───────────────┼──────────────┼────────────┘
                              │              │
                       ┌──────▼──────────────▼───┐
                       │   Bedrock Formatter     │
                       │   (Converse API msgs)   │
                       └──────────┬──────────────┘
                                  │
                       ┌──────────▼──────────────┐
                       │   Bedrock Analyzer      │
                       │   (Nova Lite)           │
                       │                         │
                       │   → Themes              │
                       │   → Sentiment Summary   │
                       │   → Recommendations     │
                       └──────────┬──────────────┘
                                  │
                       ┌──────────▼──────────────┐
                       │   CloudWatch Monitor    │
                       │   (metrics, dashboard,  │
                       │    alarms)              │
                       └─────────────────────────┘
```

## How It Works — The Pipeline Flow

```
📋 Feedback Records
       │
       ▼
┌──────────────────┐
│ 1. INGEST        │  Load records with data_type tag (text/image/audio/survey)
└──────┬───────────┘
       ▼
┌──────────────────┐
│ 2. VALIDATE      │  Glue Data Quality: completeness, uniqueness, freshness
└──────┬───────────┘  Failed records flagged and skipped
       ▼
┌──────────────────┐
│ 3. SCORE         │  Lambda quality scorer for text records
└──────┬───────────┘  Short/gibberish text filtered out
       ▼
┌──────────────────┐
│ 4. ROUTE         │  Direct to processor by data_type
└──┬───┬───┬───┬───┘
   │   │   │   │
   ▼   ▼   ▼   ▼
  Text Image Audio Survey    ← Each gets its own processor
   │   │   │   │
   └───┴───┴───┘
       │
       ▼
┌──────────────────┐
│ 5. FORMAT        │  Convert all results to Converse API messages
└──────┬───────────┘
       ▼
┌──────────────────┐
│ 6. ANALYZE       │  Nova Lite: themes, sentiment, recommendations
└──────────────────┘
```

### The Four Processors

- **Text → Amazon Comprehend**: Extracts entities (PERSON, ORGANIZATION, LOCATION, DATE) and detects sentiment (POSITIVE, NEGATIVE, NEUTRAL, MIXED) with confidence scores
- **Images → Textract + Rekognition**: Textract runs OCR on photos (receipts, labels, handwritten notes). Rekognition detects objects and scenes (Box, Damage, Cardboard)
- **Audio → Amazon Transcribe**: Transcribes phone calls and voicemails with speaker diarization — who said what and when
- **Surveys → SageMaker Processing**: Computes response distributions, mean scores for numeric scales, and collects free-text responses

---

## Example Output — What You Get

```
Customer Feedback Pipeline — Demo
============================================================

Region:   us-east-1
AWS mode: live
Bucket:   your-bucket-name
------------------------------------------------------------

[1/6] Loading sample feedback records...
  Total records: 38
     audio: 5
     image: 7
    survey: 8
      text: 18

[2/6] Validating records (Glue Data Quality rules)...
  Passed: 35/38
  Failed: 3
  Violations:
    BAD-001: missing_customer_id
    BAD-002: stale_timestamp
    TXT-001: duplicate_id

[3/6] Processing text records (Amazon Comprehend)...

  Text Processing (15 records):
    Entities detected: 23
    Sentiment breakdown: mixed: 4, negative: 5, positive: 6

    Example — TXT-001:
      Text: "Great experience with the customer service team. Sarah at the Austin sto..."
      Entity: PERSON: Sarah (100%)
      Entity: LOCATION: Austin (97%)
      Entity: QUANTITY: under 10 minutes (99%)
      Sentiment: POSITIVE (pos=100%, neg=0%)

[4/6] Processing image records (Textract + Rekognition)...

  Image Processing (7 records):
    Text blocks extracted: 569
    Labels detected: 30

    Example — IMG-001:
      OCR: "RMA Number: RMA-2026-1147" (87.7%)
      OCR: "Order: ORD-2026-8834" (92.2%)
      Label: Page (100.0%)
      Label: Text (100.0%)

  Audio Processing (5 records):
    Transcripts: 5
    Speaker segments: 10

    Example — AUD-001:
      [spk_0] (0.0s-28.9s): I'm looking at my credit card statement and I see two
          charges for the same order...

  Survey Processing (1 batch):
    Questions summarized: 5
    Free-text responses: 8
      Overall satisfaction (1-5): 8 responses, mean=3.2
      Delivery experience (1-5): 8 responses, mean=2.9
      Product quality (1-5): 8 responses, mean=3.6

[5/6] Formatting results for Bedrock Converse API...
  Messages prepared: 28 data + 1 instruction

[6/6] Analyzing with Amazon Nova Lite...

  Themes:
    1. Product quality and perceived value
    2. Delivery and shipping issues
    3. Customer support responsiveness and effectiveness
    4. Warranty and return process clarity
    5. Overall satisfaction and likelihood to recommend

  Sentiment Summary:
    Overall mixed sentiment. Many customers appreciate the product quality
    and customer service, but significant frustration with delivery delays,
    damaged products, and poor communication from support teams.

  Recommendations:
    1. Improve quality control to reduce defective products reaching customers
    2. Enhance communication and transparency regarding shipping delays
    3. Train customer support staff to be more empathetic and proactive
    4. Clarify warranty terms and simplify the return process
    5. Gather and act on customer feedback to continuously improve
```

---

## Prerequisites

Before you start, you'll need:

1. **Python 3.10+** installed on your machine
2. **An AWS account** with access to Amazon Bedrock
3. **AWS CLI** installed and configured

If you completed Part 1 or Part 2, you already have all of this set up.

---

## Step-by-Step Setup Guide

### Step 1: Clone and Set Up the Project

```bash
git clone https://github.com/srikanthethiraj/customer-feedback-pipeline.git
cd customer-feedback-pipeline
```

Create a virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Enable Amazon Bedrock Model Access

1. Go to the [AWS Console](https://console.aws.amazon.com/)
2. Navigate to **Amazon Bedrock**
3. Make sure you're in the **us-east-1** region
4. In the left sidebar, click **Model access**
5. Click **Manage model access**
6. Enable **Amazon → Nova Lite**
7. Click **Save changes** and wait for "Access granted"

### Step 3: Run the Demo (Local Simulation)

```bash
python3 demo.py
```

This runs the full pipeline with simulated AWS service responses — no AWS credentials needed. You'll see validation, processing, and analysis for all four data types. The demo discovers sample images from `samples/images/` and audio from `samples/audio/` automatically.

### Step 4: Generate Real Sample Files and Run with AWS

Generate real sample images (document layouts for Textract) and real speech audio (via Amazon Polly for Transcribe), then upload to S3:

```bash
pip install Pillow
python3 generate_samples.py --with-polly --upload --bucket YOUR_BUCKET --region us-east-1
```

Run the pipeline with real AWS services:

```bash
python3 demo.py --use-aws --bucket YOUR_BUCKET --region us-east-1
```

This calls Comprehend, Textract, Rekognition, Transcribe, and Bedrock against real data. Textract reads actual text from the generated document images. Transcribe converts real Polly-generated speech back to text.

---

## Deploy to AWS

```bash
./deploy.sh your-s3-bucket-name
```

This will:
1. Package the Lambda functions into a zip file
2. Upload to your S3 bucket
3. Deploy the CloudFormation stack (Lambda functions, CloudWatch dashboard, alarms)
4. Print the stack outputs

Optional parameters:

```bash
./deploy.sh your-s3-bucket us-west-2 staging
#           ^bucket        ^region   ^environment
```

### Tear Down

```bash
aws cloudformation delete-stack --stack-name customer-feedback-pipeline-prod --region us-east-1
```

---

## Project Structure

```
customer-feedback-pipeline/
├── samples/
│   ├── images/                     # 7 real JPG files (receipts, shipping labels, forms)
│   └── audio/                      # 5 real WAV files (Polly-generated customer calls)
├── src/
│   ├── models.py                   # All data classes (FeedbackRecord, results, etc.)
│   ├── data_validator.py           # Glue Data Quality rules (completeness, uniqueness, freshness)
│   ├── quality_scorer.py           # Lambda text quality scoring
│   ├── quality_monitor.py          # CloudWatch metrics publishing
│   ├── text_processor.py           # Amazon Comprehend (entities + sentiment)
│   ├── image_processor.py          # Amazon Textract (OCR) + Rekognition (labels)
│   ├── audio_processor.py          # Amazon Transcribe (speech-to-text + speaker labels)
│   ├── survey_processor.py         # Survey aggregation (distributions, means, free-text)
│   ├── bedrock_formatter.py        # Converts results to Converse API messages
│   ├── bedrock_analyzer.py         # Nova Lite analysis (themes, sentiment, recommendations)
│   ├── pipeline.py                 # Pipeline orchestrator
│   ├── sample_data.py              # Sample records + auto-discovery of images/audio
│   └── infra/
│       └── template.yaml           # CloudFormation template
├── tests/
│   ├── unit/                       # Example-based tests
│   ├── property/                   # Hypothesis property-based tests
│   └── integration/                # End-to-end tests
├── demo.py                         # Demo script — run this first
├── generate_samples.py             # Generate real images (Pillow) + speech audio (Polly)
├── deploy.sh                       # One-command AWS deployment
├── requirements.txt                # Python dependencies
└── README.md
```

## Connection to Part 1

| Concept | Part 1 (Insurance Claim Processor) | Part 3 (This Project) |
|---|---|---|
| **Data types** | Text only | Text, images, audio, surveys |
| **Validation** | `ContentValidator` — field checks + PII regex | Glue Data Quality rules + Lambda quality scorer |
| **AI services** | Bedrock only | Comprehend, Textract, Rekognition, Transcribe, SageMaker, Bedrock |
| **Processing** | Single pipeline for all documents | Processor-per-modality with routing |
| **Monitoring** | None | CloudWatch metrics, dashboards, alarms |
| **Data quality** | Pass/fail on required fields | Completeness + uniqueness + freshness + content scoring |

---

## What's Next in the Series

| Part | Project | What You'll Build | Skills You'll Gain |
|---|---|---|---|
| **1** | **[Insurance Claim Processor](https://github.com/srikanthethiraj/insurance-claim-processor)** | AI-powered document extraction and summarization | Bedrock basics, prompt templates, simple RAG, model comparison |
| **2** | **[Financial Services AI Assistant](https://github.com/srikanthethiraj/financial-ai-assistant)** | Customer service assistant with dynamic model selection | Model benchmarking, Lambda abstraction, AppConfig, circuit breakers |
| **3** | **Customer Feedback Pipeline** (this project) | Multimodal data processing from text, images, audio, and surveys | Glue Data Quality, Comprehend, Textract, Transcribe, data formatting for FMs |
| **4** | **Knowledge Base RAG System** | Full RAG system with vector stores and embeddings | Bedrock Knowledge Bases, OpenSearch, DynamoDB, document chunking |
| **5** | **Advanced Search & Retrieval** | Optimized search with hybrid strategies and reranking | Chunking strategies, embedding comparison, hybrid search, query expansion |
| **6** | **AI Support Assistant with Governance** | Production AI assistant with safety controls | Bedrock Guardrails, Prompt Management, Prompt Flows, conversation workflows |

## License

MIT
