# Circle of Trust - AWS Deployment Architecture

## Executive Summary

This document outlines a **cost-efficient, scalable, and serverless** architecture for deploying the Circle of Trust multi-LLM advisory system on AWS. The solution leverages managed services and spot compute to minimize operational overhead while maintaining high availability.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            USER ACCESS LAYER                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                         ┌──────────▼──────────┐
                         │   S3 Static Website │
                         │   (React Frontend)  │
                         │   Static Hosting    │
                         └──────────┬──────────┘
                                    │ POST /chat (+ Auth token)
                                    │ GET /jobs/{id} (+ Auth token)
                                    │
                         ┌──────────▼──────────┐
                         │   PingID SSO        │
                         │  - Authentication   │
                         │  - MFA enforcement  │
                         └──────────┬──────────┘
                                    │
┌───────────────────────────────────┼───────────────────────────────────┐
│                              API LAYER                                 │
│                                   │                                    │
│                    ┌──────────────▼──────────────┐                    │
│                    │  API Gateway HTTP API       │                    │
│                    │  + WebSocket API Gateway    │                    │
│                    │  - PingID Token Validation  │                    │
│                    │  - Throttling               │                    │
│                    │  - VPC Link Integration     │                    │
│                    └──────────┬──────────────────┘                    │
│                               │                                        │
│                    ┌──────────▼──────────────────────────┐            │
│                    │ ECS Fargate (On-Demand)            │             │
│                    │     API Service                    │             │
│                    │  - Validate request                │             │
│                    │  - Create job_id                   │      ┌──────┼──────┐
│                    │  - Store metadata ─────────────────┼──────▶      │      │
│                    │  - Return job_id (fast)            │      │      │      │
│                    └──────────┬──────────────────────────┘      │  DynamoDB  │
└───────────────────────────────┼───────────────────────────────┐ │  Tables    │
                                │ Send job to queue             │ │ - Jobs     │
                    ┌───────────▼───────────┐                   │ │ - Results  │
                    │    Amazon SQS         │                   │ │ - State    │
                    │  (Job Queue)          │                   │ └────────────┘
                    │  - Buffer jobs        │                   │       ▲
                    │  - Decouple services  │                   │       │
                    │  - Enable retries     │                   │       │ Store
                    │  - DLQ for failures   │                   │       │ result
                    └───────────┬───────────┘                   │       │
                                │ Poll messages                 │       │
┌───────────────────────────────┼───────────────────────────────┼───────┼───┐
│                         COMPUTE LAYER (Workers)               │       │   │
│                                │                               │       │   │
│                    ┌───────────▼───────────┐                  │       │   │
│                    │   ECS Fargate SPOT    │                  │       │   │
│                    │   (Worker Tasks)      │                  │       │   │
│                    │  - Poll SQS           │                  │       │   │
│                    │  - Run agent logic    │                  │       │   │
│                    │  - Build prompts      ├──────┐           │       │   │
│                    │  - Ack SQS msg        ├──────┼───────────┼───────┘   │
│                    └───────────────────────┘      │           │           │
└───────────────────────────────────────────────────┼───────────┼───────────┘
                                                     │           │
                                          ┌──────────▼───────┐   │
                                          │ Amazon Bedrock   │   │
                                          │  - Claude 3.5    │   │
                                          │  - Mistral       │   │
                                          │  - Llama 3       │   │
                                          │  LLM Inference   │   │
                                          └──────────────────┘   │
                                                     │            │
                    ┌────────────────────────────────┘            │
                    │ Return responses                            │
                    └─────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                       DATA FLOW SUMMARY                                 │
│                                                                         │
│  User → S3 (Load UI)                                                    │
│  UI → PingID SSO (authenticate with MFA)                                │
│  PingID issues auth token to UI                                         │
│  UI → API Gateway (POST /chat + auth token)                             │
│  API Gateway → PingID (validate token)                                  │
│  API Gateway → ECS API (authorized request)                             │
│  ECS API → DynamoDB (store job metadata) → SQS (enqueue job)            │
│  ECS API → UI (return job_id, fast response)                             │
│  ECS Worker (Spot) ← SQS (poll job)                                     │
│  ECS Worker → Bedrock (run agent)                                        │
│  ECS Worker → DynamoDB (store result)                                   │
│  UI → API Gateway (GET /jobs/{id} + auth token)                         │
│  API Gateway → PingID (validate token) → ECS API → DynamoDB (read)      │
│  UI displays result                                                     │
└─────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                       OBSERVABILITY & MONITORING                        │
│                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐       │
│  │   CloudWatch    │  │   CloudWatch    │  │      X-Ray      │       │
│  │     Logs        │  │    Metrics      │  │   (Tracing)     │       │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘       │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         SECURITY & GOVERNANCE                           │
│                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐       │
│  │  PingID SSO     │  │      IAM        │  │      WAF        │       │
│  │  (Corporate)    │  │   (Roles)       │  │  (API Gateway)  │       │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘       │
│  ┌─────────────────┐  ┌─────────────────┐                            │
│  │   Secrets Mgr   │  │   CloudTrail    │                            │
│  │ (Bedrock Keys)  │  │  (Audit Logs)   │                            │
│  └─────────────────┘  └─────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────┘
```
