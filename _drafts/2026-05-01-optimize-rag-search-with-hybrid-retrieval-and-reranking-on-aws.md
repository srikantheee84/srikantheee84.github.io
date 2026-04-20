---
layout: post
title: "Optimize RAG Search with Hybrid Retrieval and Reranking on AWS"
tags: [AI, AWS, Python, Bedrock, OpenSearch, RAG, Embeddings, Search]
featured_image_thumbnail:
featured_image: assets/images/posts/2026/article-5-hero.jpeg
featured: false
hidden: false
---

In Part 4, we built a RAG knowledge base with vector stores, embeddings, and document processing. It works — ask a question, get an answer grounded in your documents. But "works" and "works well" are different things.

This project makes the search smarter. Hybrid retrieval that combines vectors with keywords. Reranking that puts the best results first. Query expansion that finds what you meant, not just what you typed. And evaluation metrics that tell you exactly how good your search is.

<!--more-->

## The Problem

Pure vector search has a blind spot. It's great at semantic similarity — "cold starts" matches "execution environment initialization." But it misses exact terms. Search for "t3.small.search" and vector search might return results about instance types in general, not the specific one you asked about.

Keyword search has the opposite problem. It finds exact matches but misses meaning. "How do I reduce startup latency?" returns nothing if your documents say "cold start" instead of "startup latency."

You need both. And you need a way to measure which approach actually works better.

## The Pattern

**Expand → Embed → Search (vector + keyword) → Rerank → Generate → Evaluate**

Article 4 was: embed → search → generate. This project adds query intelligence on the front end, hybrid search and reranking in the middle, and quality measurement on the back end.

## Architecture

The system has two flows: the search pipeline that processes queries, and the evaluation framework that measures quality.

**Search Pipeline** — queries flow through expansion, embedding, hybrid search, reranking, and generation.

![Search Pipeline](/assets/images/posts/2026/article-5-search.png)

The evaluation framework runs test queries with known relevant documents through the pipeline and scores results with MRR, NDCG, Precision@K, and Recall@K.

## How It Works

Six phases. Each one adds a layer of intelligence to the basic vector search from Article 4.

**Phase 1: Chunking Comparison.** Three strategies side by side — fixed-size (512 chars with overlap), hierarchical (split by headings then paragraphs), and semantic (respect natural boundaries). The same corpus produces very different chunk distributions:

```
Strategy               Chunks   Avg Size    Min    Max
fixed-512                  69        162      1    512
hierarchical               26        345    192    614
semantic                   14        643    240    796
```

Fixed-size produces 69 tiny fragments. Hierarchical splits by section titles and keeps each title with its content — 26 mid-sized chunks. Semantic respects natural paragraph boundaries — 14 coherent sections. More chunks isn't better — it means more noise in retrieval.

**Phase 2: Embedding Benchmark.** Amazon Titan Embed V2 converts text to 1024-dimensional vectors. We measure latency (244ms average) and check that semantically related texts produce similar vectors while unrelated texts don't.

The similarity matrix confirms the model understands meaning — Lambda and S3 content score 0.04 (unrelated), while S3 and Bedrock content score 0.16 (both AWS storage/retrieval topics).

**Phase 3: Hybrid Search.** This is the core upgrade from Article 4. Instead of pure vector search, we combine 75% vector similarity with 25% keyword matching. The keyword component catches exact terms that vector search might miss.

```
Query: "How do Lambda cold starts work?"
Weights: vector=0.75, keyword=0.25

[1] (0.6942) When Lambda runs your function, it creates an execution environment...
[2] (0.2908) Lambda automatically scales your function by running additional...
[3] (0.2851) AWS Lambda is a serverless compute service...
```

The top result scores 0.69 — a strong match. The gap between #1 and #2 is large, which means the system is confident about what's most relevant.

**Phase 4: Reranking.** Hybrid search gets the right documents into the top-K. Reranking puts them in the right order. We use Nova Micro to score each result's relevance to the query on a 0-10 scale.

```
Reranked results:
[1] (0.80) When Lambda runs your function, it creates an execution environment...
[2] (0.30) Lambda automatically scales your function...
[3] (0.30) AWS Lambda is a serverless compute service...
[4] (0.10) S3 lifecycle policies automate transitioning...
[5] (0.00) Amazon S3: Trigger functions when objects are created...
```

After reranking, the cold starts passage scores 0.80 while unrelated S3 content drops to 0.00. The model understands relevance better than cosine similarity alone.

**Phase 5: Query Processing.** Simple queries get expanded into related searches. Complex queries get decomposed into sub-questions.

```
Simple: "Lambda cold starts"
→ "Lambda cold starts"
→ "How to reduce Lambda function cold start latency"
→ "Strategies for minimizing AWS Lambda initialization delays"
→ "Techniques to mitigate AWS Lambda function startup time"

Complex: "Compare Lambda cold starts with ECS task startup times"
→ "How are Lambda cold starts defined and what factors influence them?"
→ "What are ECS task startup times and what factors influence them?"
→ "How do Lambda cold starts compare to ECS task startup times?"
```

Expansion catches different phrasings. Decomposition breaks multi-part questions into answerable pieces.

**Phase 6: Evaluation.** This is how you know your search actually works. Five test queries with known relevant passages, scored on four metrics:

```
Query                                            MRR   NDCG    P@5    R@5
How do Lambda cold starts work?                1.000  1.000  0.600  1.000
What vector stores does Bedrock KB support?    1.000  0.956  0.800  1.000
How does S3 versioning protect data?           1.000  1.000  0.200  1.000
What embedding models are available?           1.000  0.920  0.400  1.000
How do I set up Lambda event triggers?         1.000  0.854  0.800  0.500
AVERAGE                                        1.000  0.946  0.560  0.900
```

MRR of 1.0 means the most relevant result is always ranked first. NDCG of 0.946 means the overall ranking quality is excellent. Recall of 0.90 means we're finding 90% of all relevant passages in the top 5.

## Evaluation Metrics — What They Mean

**MRR (Mean Reciprocal Rank)** — How high is the first relevant result? MRR of 1.0 means it's always #1. MRR of 0.5 means it's usually #2.

**NDCG (Normalized Discounted Cumulative Gain)** — Are all the relevant results ranked near the top? Rewards systems that put multiple relevant results high, not just the first one.

**Precision@K** — What fraction of the top-K results are relevant? P@5 of 0.60 means 3 out of 5 results are relevant.

**Recall@K** — What fraction of all relevant documents appear in the top-K? R@5 of 0.90 means we're finding 90% of everything relevant.

## What Changed from Article 4

| Concept | Article 4 (Knowledge Base) | Article 5 (This Project) |
|---|---|---|
| **Search** | Pure vector (cosine similarity) | Hybrid (75% vector + 25% keyword) |
| **Ranking** | Single-pass similarity score | Two-pass: similarity then reranking |
| **Query handling** | Direct embedding | Expansion for simple, decomposition for complex |
| **Chunking** | Semantic only | Three strategies compared with metrics |
| **Evaluation** | None — "it looks right" | MRR, NDCG, Precision@K, Recall@K |
| **Reranking** | None | Nova Micro relevance scoring |

## Getting Started

Prerequisites: Python 3.10+, AWS CLI configured, Bedrock model access for Titan Embed V2, Nova Lite, and Nova Micro.

```bash
git clone https://github.com/srikanthethiraj/advanced-search-retrieval.git
cd advanced-search-retrieval
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Run the demo:

```bash
python demo.py --region us-east-1
```

You'll see all six phases — chunking comparison, embedding benchmark, hybrid search, reranking, query processing, and evaluation metrics.

## Tear Down

No infrastructure to tear down — this project runs entirely against Bedrock APIs with in-memory search. No OpenSearch domain, no DynamoDB table, no CloudFormation stack.

## What's Next

This is Part 5 of an ongoing series:

- **Part 1** — [Insurance Claim Processor](https://blog.srikanthethiraj.com/build-an-ai-powered-insurance-claim-processor-with-amazon-bedrock): Bedrock basics, prompt templates, simple RAG
- **Part 2** — [Financial Services AI Assistant](https://blog.srikanthethiraj.com/build-a-financial-services-ai-assistant-with-amazon-bedrock): benchmarking, circuit breakers, cross-region resilience
- **Part 3** — [Customer Feedback Pipeline](https://blog.srikanthethiraj.com/build-a-customer-feedback-pipeline-with-amazon-bedrock): multimodal data processing
- **Part 4** — [RAG Knowledge Base](https://blog.srikanthethiraj.com/build-a-rag-knowledge-base-with-amazon-bedrock-and-opensearch): vector stores, embeddings, document chunking
- **Part 5** — Advanced Search & Retrieval (this post): hybrid search, reranking, query expansion, evaluation
- **Part 6** — AI Support Assistant with Governance: guardrails, prompt management, conversation flows
- **Part 7+** — Agentic AI, enterprise integration, AI safety, optimization, testing & evaluation

In Part 6, we build a production AI assistant with Amazon Bedrock Guardrails, prompt management with versioning, conversation flows, and edge case testing.

Repository: [github.com/srikanthethiraj/advanced-search-retrieval](https://github.com/srikanthethiraj/advanced-search-retrieval)

---

*I'm Srikanth — a cloud engineer at AWS based in Austin, Texas. I learn by building, and I write about what I build. Follow along on this blog or connect with me on [LinkedIn](https://www.linkedin.com/in/srikanthethiraj/).*
