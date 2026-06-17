"""
AI Stack Doctor v4 — REWIRED Edition

AI Stack Doctor v4
==================
Phase 5: Industry Intelligence · AI Org Health · Maturity Calibration

New in v4 (REWIRED-inspired additions):
  - INDUSTRY_VALUE_MAP: 9 sector profiles with highest-value AI domains per industry
  - Industry-weighted recommendations: top domains surfaced first per sector
  - AI Org Health section: CAIO/VP AI signals, platform team, production depth
  - Maturity ladder refinement: Scaling Purgatory flag, sharper calibration signals
  - Sector benchmark hints injected into peer comparison searches

Built on v3 (retained):
  - Mode selector: Analyze YOUR company | Analyze a competitor | Generic audit
  - Historical tracking: every report saved to SQLite with trend comparison
  - Top-tier company intelligence layer (Meta, Nvidia, OpenAI, Microsoft,
    Anthropic, Apple, Amazon, Netflix, Salesforce, Google, Mistral, Intel, etc.)
  - Company-specific search query routing (engineering blogs, research pages, etc.)
  - API server mode: expose the agent as a REST endpoint (--api flag)
  - Trend delta: shows score changes vs last audit for same company

Usage:
    python3 ai_stack_health_agent_v3.py              # Interactive CLI
    python3 ai_stack_health_agent_v3.py --api        # REST API mode (port 8080)
    python3 ai_stack_health_agent_v3.py --history    # View past reports

Requirements:
    pip3 install anthropic ddgs rich flask
"""

import anthropic
import json
import sys
import os
import re
import sqlite3
import argparse
from datetime import datetime
from pathlib import Path

# ── Optional deps ─────────────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table as RichTable
    from rich.prompt import Prompt, IntPrompt
    from rich.rule import Rule
    from rich import print as rprint
    RICH = True
    console = Console()
except ImportError:
    RICH = False
    console = None

client = anthropic.Anthropic()
DB_PATH = Path("ai_stack_history.db")

# ── Top-Tier Company Intelligence Layer ──────────────────────────────────────
# Pre-loaded known signals for well-documented companies.
# Used to enrich search queries AND give Claude a baseline to cross-reference.
COMPANY_INTEL = {
    "meta": {
        "industry": "social media / AI research",
        "blogs": ["engineering.fb.com", "ai.meta.com/blog", "research.facebook.com"],
        "known_stack": ["PyTorch", "Llama", "FAISS", "Presto", "Spark", "Hive",
                        "Flink", "Airflow", "Triton Inference Server", "FBLearner",
                        "Horizon (RL platform)", "Ax (AutoML)", "WhatsApp Business AI",
                        "Meta AI Assistant", "Ray", "Tupperware (cluster mgmt)"],
        "known_strengths": ["GenAI/LLMs (Llama 3.x)", "ML Infrastructure", "Data Engineering"],
        "search_hints": ["Meta AI LLM infrastructure", "PyTorch Meta engineering blog",
                         "FBLearner Flow ML platform", "Meta Llama deployment scale"],
    },
    "nvidia": {
        "industry": "semiconductors / AI infrastructure",
        "blogs": ["developer.nvidia.com/blog", "blogs.nvidia.com", "research.nvidia.com"],
        "known_stack": ["CUDA", "TensorRT", "Triton Inference Server", "NeMo",
                        "RAPIDS", "cuML", "Merlin (RecSys)", "NVIDIA AI Enterprise",
                        "DGX Cloud", "Omniverse", "NEMO Guardrails", "Hopper GPU"],
        "known_strengths": ["AI Platforms", "MLOps/LLMOps", "Cloud AI Services"],
        "search_hints": ["NVIDIA NeMo LLM platform", "NVIDIA Triton inference",
                         "NVIDIA DGX Cloud AI infrastructure", "NVIDIA AI Enterprise stack"],
    },
    "openai": {
        "industry": "AI research / LLM products",
        "blogs": ["openai.com/research", "openai.com/blog"],
        "known_stack": ["GPT-4o", "GPT-4 Turbo", "o1/o3 reasoning models", "DALL-E 3",
                        "Whisper", "Sora", "Codex", "Triton (custom GPU kernels)",
                        "Azure OpenAI Service", "RLHF pipeline", "InstructGPT",
                        "Evals framework", "Kubernetes (custom)", "Ray"],
        "known_strengths": ["GenAI/LLMs", "Agentic AI", "MLOps/LLMOps"],
        "search_hints": ["OpenAI infrastructure engineering blog", "OpenAI training cluster",
                         "OpenAI RLHF pipeline", "OpenAI deployment architecture scale"],
    },
    "anthropic": {
        "industry": "AI safety / LLM research",
        "blogs": ["anthropic.com/research", "anthropic.com/news"],
        "known_stack": ["Claude (Haiku/Sonnet/Opus)", "Constitutional AI", "RLHF",
                        "Sleeper agents research", "Interpretability tools",
                        "Amazon Bedrock (distribution)", "Google Cloud (infra)",
                        "AWS (training compute)", "Model Card framework"],
        "known_strengths": ["GenAI/LLMs", "AI Governance", "Agentic AI"],
        "search_hints": ["Anthropic Claude infrastructure", "Anthropic Constitutional AI pipeline",
                         "Anthropic model training compute", "Anthropic safety evaluation systems"],
    },
    "microsoft": {
        "industry": "enterprise software / cloud / AI",
        "blogs": ["azure.microsoft.com/blog", "research.microsoft.com", "techcommunity.microsoft.com"],
        "known_stack": ["Azure OpenAI Service", "Copilot (M365)", "Azure ML", "Fabric",
                        "Bing AI", "Phi models", "ONNX Runtime", "DeepSpeed",
                        "Semantic Kernel", "Promptflow", "Azure AI Studio",
                        "GitHub Copilot", "Power Platform AI", "Azure AI Search"],
        "known_strengths": ["Cloud AI Services", "AI Platforms", "Agentic AI"],
        "search_hints": ["Microsoft Azure AI infrastructure blog", "Microsoft DeepSpeed training",
                         "Microsoft Copilot architecture", "Azure ML platform engineering"],
    },
    "google": {
        "industry": "search / cloud / AI research",
        "blogs": ["ai.googleblog.com", "cloud.google.com/blog", "deepmind.google"],
        "known_stack": ["Gemini Ultra/Pro/Flash", "TPUs (v4/v5)", "Vertex AI",
                        "TensorFlow", "JAX", "Keras", "Bard/Gemini app",
                        "BigQuery ML", "Dataflow", "Pub/Sub", "Spanner",
                        "DeepMind Gato/Gemma", "AlphaCode 2", "NotebookLM",
                        "Google AI Studio", "Duet AI"],
        "known_strengths": ["Cloud AI Services", "ML Infrastructure", "GenAI/LLMs"],
        "search_hints": ["Google TPU infrastructure Gemini", "Google Vertex AI engineering",
                         "DeepMind research infrastructure", "Google ML platform TensorFlow JAX"],
    },
    "amazon": {
        "industry": "e-commerce / cloud / AI",
        "blogs": ["aws.amazon.com/blogs/machine-learning", "amazon.science"],
        "known_stack": ["SageMaker", "Bedrock", "Trainium/Inferentia chips",
                        "Alexa AI", "Rufus (shopping AI)", "CodeWhisperer",
                        "Rekognition", "Comprehend", "Forecast", "Personalize",
                        "Q (enterprise AI assistant)", "EMR", "Glue", "Kinesis",
                        "Amazon Nova models", "Titan models"],
        "known_strengths": ["Cloud AI Services", "Data Engineering", "AI Platforms"],
        "search_hints": ["AWS SageMaker engineering blog", "Amazon Bedrock foundation models",
                         "Amazon Trainium chip ML training", "Amazon Alexa AI infrastructure"],
    },
    "apple": {
        "industry": "consumer electronics / software / AI",
        "blogs": ["machinelearning.apple.com", "apple.com/newsroom"],
        "known_stack": ["Apple Intelligence", "Core ML", "Create ML", "Neural Engine",
                        "Private Cloud Compute", "Siri AI", "Vision framework",
                        "Natural Language framework", "Swift for TensorFlow (legacy)",
                        "On-device LLMs (Apple Silicon)", "MLX framework"],
        "known_strengths": ["On-device AI", "AI Governance/Privacy", "ML Infrastructure"],
        "search_hints": ["Apple MLX framework engineering", "Apple Private Cloud Compute AI",
                         "Apple Intelligence on-device ML", "Apple Core ML infrastructure"],
    },
    "netflix": {
        "industry": "streaming / entertainment",
        "blogs": ["netflixtechblog.com"],
        "known_stack": ["Metaflow", "Maestro (workflow)", "Hollow (data distribution)",
                        "Flink", "Spark", "Ray", "TensorFlow", "PyTorch",
                        "Merlin (RecSys)", "A/B testing platform (Experimentation)",
                        "Keystone (streaming pipeline)", "Mantis", "Zuul"],
        "known_strengths": ["ML Infrastructure", "Data Engineering", "MLOps/LLMOps"],
        "search_hints": ["Netflix Metaflow ML platform", "Netflix recommendation system architecture",
                         "Netflix Tech Blog machine learning", "Netflix LLM generative AI strategy"],
    },
    "salesforce": {
        "industry": "enterprise CRM / cloud software",
        "blogs": ["engineering.salesforce.com", "blog.salesforce.com/ai"],
        "known_stack": ["Einstein AI", "Einstein GPT", "Agentforce", "BLIP-2",
                        "CodeGen", "Slack AI", "Data Cloud (CDP)", "Tableau AI",
                        "MuleSoft AI", "xLAM agentic models", "OpenAI partnership",
                        "Heroku AI"],
        "known_strengths": ["Agentic AI", "GenAI/LLMs", "AI Platforms"],
        "search_hints": ["Salesforce Einstein AI engineering", "Salesforce Agentforce architecture",
                         "Salesforce xLAM agentic model", "Salesforce AI Cloud platform"],
    },
    "mistral": {
        "industry": "AI research / LLM products",
        "blogs": ["mistral.ai/news", "mistral.ai/research"],
        "known_stack": ["Mistral 7B/8x7B/Large/Nemo", "Mixtral MoE architecture",
                        "Le Chat (consumer product)", "La Plateforme (API)",
                        "Codestral", "Mistral Embed", "vLLM (serving)",
                        "Azure AI / Google Cloud (distribution)"],
        "known_strengths": ["GenAI/LLMs", "Agentic AI", "MLOps/LLMOps"],
        "search_hints": ["Mistral AI model architecture engineering", "Mistral MoE deployment",
                         "Mistral Le Chat infrastructure", "Mistral API platform scale"],
    },
    "intel": {
        "industry": "semiconductors / AI hardware",
        "blogs": ["community.intel.com/ai", "intel.com/content/www/us/en/newsroom"],
        "known_stack": ["Gaudi AI accelerators", "OpenVINO", "Intel Extension for PyTorch",
                        "BigDL", "oneAPI", "Nervana (legacy)", "Habana Labs",
                        "Intel Developer Cloud", "IPEX-LLM", "Tiber AI Cloud"],
        "known_strengths": ["AI Platforms", "Cloud AI Services", "ML Infrastructure"],
        "search_hints": ["Intel Gaudi AI accelerator benchmark", "Intel OpenVINO LLM inference",
                         "Intel oneAPI AI development", "Intel Habana Labs training infrastructure"],
    },
    "adobe": {
        "industry": "creative software / digital experience / AI",
        "blogs": ["blog.adobe.com", "adobe.com/sensei", "research.adobe.com"],
        "known_stack": ["Adobe Firefly (GenAI images/video)", "Adobe Sensei AI",
                        "Adobe Experience Platform (AEP)", "Real-Time CDP",
                        "Journey Optimizer AI", "Marketo Engage AI",
                        "Adobe Express AI", "Content Authenticity Initiative (CAI)",
                        "Photoshop Generative Fill", "Frame.io AI",
                        "Adobe GenStudio", "Acrobat AI Assistant",
                        "Azure OpenAI (partnership)", "Python/PyTorch (research)"],
        "known_strengths": ["GenAI/LLMs", "AI Platforms", "Data Engineering"],
        "search_hints": ["Adobe Firefly generative AI infrastructure",
                         "Adobe Sensei ML platform engineering",
                         "Adobe Experience Platform AI architecture",
                         "Adobe GenStudio AI content pipeline"],
    },
    "tesla": {
        "industry": "electric vehicles / autonomous driving / AI",
        "blogs": ["tesla.com/AI", "tesla.com/blog", "arxiv.org tesla"],
        "known_stack": ["Autopilot / FSD Neural Networks", "Dojo supercomputer",
                        "Tesla Vision (camera-only perception)", "Occupancy Networks",
                        "End-to-end neural driving model", "PyTorch (training)",
                        "Custom D1 AI chip", "Optimus robot AI",
                        "Fleet learning pipeline", "Shadow mode data collection",
                        "Tesla Energy AI (grid optimization)", "Grok integration (xAI)"],
        "known_strengths": ["ML Infrastructure", "Data Engineering", "AI Platforms"],
        "search_hints": ["Tesla Dojo supercomputer AI training",
                         "Tesla FSD neural network architecture",
                         "Tesla Autopilot machine learning pipeline",
                         "Tesla fleet learning data engineering scale"],
    },
    "broadcom": {
        "industry": "semiconductors / enterprise software / networking",
        "blogs": ["broadcom.com/blog", "vmware.com/topics/ai"],
        "known_stack": ["VMware Private AI Foundation", "VMware vSphere AI",
                        "Broadcom AI ASIC (custom accelerators)", "VCF (VMware Cloud Foundation)",
                        "Tanzu AI (Kubernetes for ML)", "Aria AI (operations)",
                        "NSX AI networking", "Brocade AI networking",
                        "CA AI (enterprise software)", "Symantec AI (security)"],
        "known_strengths": ["AI Platforms", "Cloud AI Services", "ML Infrastructure"],
        "search_hints": ["Broadcom VMware Private AI Foundation architecture",
                         "VMware Tanzu AI ML workloads",
                         "Broadcom AI ASIC chip inference",
                         "VMware vSphere AI infrastructure enterprise"],
    },
    "oracle": {
        "industry": "enterprise software / cloud / database",
        "blogs": ["blogs.oracle.com/ai-and-datascience", "developer.oracle.com"],
        "known_stack": ["Oracle Cloud Infrastructure (OCI) AI", "OCI Generative AI Service",
                        "Oracle AI Vector Search", "Oracle Database 23ai",
                        "Oracle Analytics Cloud AI", "Autonomous Database",
                        "Cohere partnership (LLMs)", "Meta Llama on OCI",
                        "OCI Data Science", "Oracle Digital Assistant",
                        "Oracle Fusion AI (ERP/HCM)", "APEX AI"],
        "known_strengths": ["Cloud AI Services", "Data Engineering", "AI Platforms"],
        "search_hints": ["Oracle OCI Generative AI infrastructure",
                         "Oracle Database 23ai vector search AI",
                         "Oracle Cohere LLM partnership deployment",
                         "Oracle Cloud AI data science platform"],
    },
    "amd": {
        "industry": "semiconductors / AI hardware / GPU",
        "blogs": ["community.amd.com/ai", "developer.amd.com", "rocm.docs.amd.com"],
        "known_stack": ["Instinct MI300X/MI325X AI accelerators", "ROCm (open GPU platform)",
                        "HIP (CUDA-compatible runtime)", "MIOpen (deep learning library)",
                        "Ryzen AI (on-device NPU)", "AMD EPYC AI server CPUs",
                        "Radeon AI (consumer GPU ML)", "vLLM on ROCm",
                        "PyTorch ROCm backend", "TensorFlow ROCm",
                        "AMD AI Developer Cloud", "Pensando AI networking"],
        "known_strengths": ["AI Platforms", "ML Infrastructure", "Cloud AI Services"],
        "search_hints": ["AMD Instinct MI300X AI training benchmark",
                         "AMD ROCm LLM inference engineering",
                         "AMD Ryzen AI on-device machine learning",
                         "AMD HIP GPU compute AI workloads"],
    },
    "stability ai": {
        "industry": "generative AI / image & media synthesis",
        "blogs": ["stability.ai/news", "stability.ai/research"],
        "known_stack": ["Stable Diffusion (SD 1.x/2.x/3.x/XL)", "SDXL Turbo",
                        "Stable Video Diffusion", "Stable Audio",
                        "Stable LM (language models)", "Stable Code",
                        "DreamStudio (consumer platform)", "Stability AI API",
                        "DeepFloyd IF", "Clipdrop (acquired)",
                        "AWS partnership (compute)", "PyTorch (training)"],
        "known_strengths": ["GenAI / LLMs", "Agentic AI", "MLOps / LLMOps"],
        "search_hints": ["Stability AI Stable Diffusion infrastructure training",
                         "Stability AI SDXL architecture deployment",
                         "Stability AI API platform engineering",
                         "Stable Diffusion 3 model architecture research"],
    },
    "deepl": {
        "industry": "AI translation / natural language processing",
        "blogs": ["deepl.com/blog", "developers.deepl.com"],
        "known_stack": ["DeepL Translator (neural MT)", "DeepL Write (AI writing)",
                        "DeepL API (Pro/Free tiers)", "DeepL for Business",
                        "Glossary API", "Document translation pipeline",
                        "Custom neural MT models", "DeepL Voice (real-time translation)",
                        "Proprietary transformer architecture",
                        "Internal data infrastructure (Cologne HQ)",
                        "CAT tool integrations (memoQ, SDL Trados)"],
        "known_strengths": ["GenAI / LLMs", "Data Engineering", "AI Platforms"],
        "search_hints": ["DeepL neural machine translation architecture",
                         "DeepL API infrastructure engineering",
                         "DeepL transformer model training pipeline",
                         "DeepL Write AI grammar correction model"],
    },
    "synthesia": {
        "industry": "generative AI / synthetic video / avatars",
        "blogs": ["synthesia.io/blog", "synthesia.io/research"],
        "known_stack": ["Synthesia Studio (video generation platform)",
                        "AI Avatars (100+ photo-realistic)",
                        "AI Voices (120+ languages)", "IRIS avatar model",
                        "Video translation pipeline", "Synthesia API",
                        "Enterprise SSO / SCIM", "Screen Recorder AI",
                        "GAN + diffusion hybrid pipeline",
                        "Azure (cloud infrastructure)", "Custom TTS models"],
        "known_strengths": ["GenAI / LLMs", "AI Platforms", "MLOps / LLMOps"],
        "search_hints": ["Synthesia AI avatar video generation pipeline",
                         "Synthesia IRIS model architecture",
                         "Synthesia enterprise video AI platform",
                         "Synthesia API synthetic media infrastructure"],
    },
    "aleph alpha": {
        "industry": "AI research / European sovereign LLMs",
        "blogs": ["aleph-alpha.com/blog", "aleph-alpha.com/research"],
        "known_stack": ["Luminous (foundation model family: Base/Extended/Supreme)",
                        "Pharia-1 (next-gen model)", "Aleph Alpha API",
                        "Explain (interpretability feature)", "Attention Manipulation",
                        "Intelligence Layer (enterprise SDK)",
                        "Aleph Alpha PharIA (EU pharma AI)",
                        "On-premises deployment option",
                        "EU sovereign cloud infrastructure",
                        "GDPR-native architecture", "Multimodal (text + image)"],
        "known_strengths": ["GenAI / LLMs", "AI Governance", "Data Engineering"],
        "search_hints": ["Aleph Alpha Luminous model architecture",
                         "Aleph Alpha sovereign AI Europe infrastructure",
                         "Aleph Alpha Pharia model training",
                         "Aleph Alpha Intelligence Layer enterprise SDK"],
    },
    "elevenlabs": {
        "industry": "generative AI / voice synthesis / audio",
        "blogs": ["elevenlabs.io/blog", "elevenlabs.io/research"],
        "known_stack": ["ElevenLabs TTS (text-to-speech API)",
                        "Voice Cloning (instant + professional)",
                        "Multilingual v2 model (29 languages)",
                        "Projects (long-form audio production)",
                        "Dubbing Studio (AI video translation)",
                        "Sound Effects generation",
                        "ElevenLabs Reader app",
                        "Voice Library (community voices)",
                        "Streaming API (low-latency TTS)",
                        "Speech-to-Speech conversion",
                        "Custom voice model fine-tuning"],
        "known_strengths": ["GenAI / LLMs", "AI Platforms", "MLOps / LLMOps"],
        "search_hints": ["ElevenLabs text-to-speech model architecture",
                         "ElevenLabs voice cloning pipeline infrastructure",
                         "ElevenLabs multilingual TTS model training",
                         "ElevenLabs API streaming latency engineering"],
    },
    # ── ASIA — TECH ───────────────────────────────────────────────────────────
    "baidu": {
        "industry": "GenAI / Search AI / Cloud",
        "blogs": ["research.baidu.com", "developer.baidu.com/en", "ir.baidu.com"],
        "known_stack": ["Ernie 4.5 / X1 (LLMs)", "Ernie Bot (consumer AI)",
                        "Qianfan AI Platform", "Kunlun AI chips (custom silicon)",
                        "Paddle (open-source DL framework)", "Apollo (autonomous driving AI)",
                        "Baidu Cloud AI services", "Wenxin ERNIE (multimodal)",
                        "Baidu Search AI integration", "DuerOS (voice AI)"],
        "known_strengths": ["GenAI / LLMs", "AI Platforms", "Cloud AI Services"],
        "search_hints": ["Baidu ERNIE LLM model architecture 2025",
                         "Baidu AI cloud platform engineering",
                         "Baidu Kunlun AI chip infrastructure",
                         "Baidu Paddle deep learning framework"],
    },
    "bytedance": {
        "industry": "Social Media / GenAI / Content AI",
        "blogs": ["bytedance.com/en/news", "research.bytedance.com"],
        "known_stack": ["Doubao LLM (China's #1 AI chatbot)", "Seedance (video AI)",
                        "TikTok recommendation engine (custom ML)",
                        "Bytedance AI Lab (research)", "Volcano Engine (AI cloud)",
                        "Coze (AI agent platform)", "MiniMax partnership",
                        "Custom TPU-equivalent AI chips", "PyTorch (training)"],
        "known_strengths": ["GenAI / LLMs", "Agentic AI", "Machine Learning"],
        "search_hints": ["ByteDance Doubao LLM infrastructure architecture",
                         "ByteDance TikTok recommendation AI engineering",
                         "ByteDance Volcano Engine AI cloud platform",
                         "ByteDance AI research lab model training"],
    },
    "alibaba": {
        "industry": "Cloud / AI Platform / E-commerce AI",
        "blogs": ["alibabacloud.com/blog", "damo.alibaba.com", "ir.alibabagroup.com"],
        "known_stack": ["Qwen model family (open-source LLMs)", "Tongyi Qianwen (AI assistant)",
                        "Alibaba Cloud AI (100+ pre-trained models)",
                        "DAMO Academy (AI research)", "Accio (B2B AI sourcing)",
                        "DingTalk AI (enterprise AI)", "PAI (ML platform)",
                        "MaxCompute (big data)", "Lindorm (real-time data)"],
        "known_strengths": ["GenAI / LLMs", "Cloud AI Services", "AI Platforms"],
        "search_hints": ["Alibaba Qwen model architecture open source",
                         "Alibaba Cloud AI platform infrastructure 2025",
                         "DAMO Academy AI research publications",
                         "Alibaba PAI machine learning platform engineering"],
    },
    "samsung": {
        "industry": "Consumer Tech / AI Hardware / Semiconductors",
        "blogs": ["research.samsung.com", "semiconductor.samsung.com/us/consumer-storage/internal-ssd/"],
        "known_stack": ["Samsung Gauss (on-device LLM)", "Exynos AI NPU chips",
                        "Galaxy AI features (on-device)", "Samsung AI Research Centers",
                        "HBM memory for AI (SK Hynix competitor)",
                        "Bixby (voice AI)", "SmartThings AI (IoT)",
                        "Tizen AI platform", "One UI AI features"],
        "known_strengths": ["GenAI / LLMs", "AI Platforms", "Machine Learning"],
        "search_hints": ["Samsung Gauss LLM on-device AI architecture",
                         "Samsung Exynos NPU AI chip engineering",
                         "Samsung Galaxy AI feature stack",
                         "Samsung AI research center publications"],
    },
    "deepseek": {
        "industry": "GenAI / LLMs / Open Source AI",
        "blogs": ["deepseek.com", "github.com/deepseek-ai"],
        "known_stack": ["DeepSeek-R1 (reasoning model)", "DeepSeek-V3 (foundation model)",
                        "DeepSeek Coder (code AI)", "DeepSeek API",
                        "Mixture of Experts (MoE) architecture",
                        "Custom CUDA optimization", "Reinforcement Learning from feedback",
                        "Open-source model weights (MIT license)"],
        "known_strengths": ["GenAI / LLMs", "Machine Learning", "AI Platforms"],
        "search_hints": ["DeepSeek R1 model architecture training efficiency",
                         "DeepSeek V3 MoE infrastructure engineering",
                         "DeepSeek open source LLM training cost",
                         "DeepSeek API platform deployment"],
    },
    "infosys": {
        "industry": "AI Services / IT Consulting / Enterprise AI",
        "blogs": ["infosys.com/newsroom", "infosys.com/iki"],
        "known_stack": ["Infosys Topaz (AI platform)", "Infosys Cobalt (cloud AI)",
                        "AI-first application development", "GenAI COE (Center of Excellence)",
                        "Azure / AWS / GCP partnerships", "Infosys Applied AI",
                        "Data & Analytics platform", "Responsible AI framework",
                        "AI training academy (100K+ employees)"],
        "known_strengths": ["AI Platforms", "Cloud AI Services", "AI Governance"],
        "search_hints": ["Infosys Topaz AI platform capabilities 2025",
                         "Infosys generative AI enterprise deployment",
                         "Infosys AI governance responsible AI framework",
                         "Infosys Cobalt cloud AI engineering"],
    },

    # ── ASIA — FINTECH ────────────────────────────────────────────────────────
    "ant group": {
        "industry": "Fintech / Payments AI / Financial Inclusion",
        "blogs": ["antgroup.com/en/news", "global.alipay.com"],
        "known_stack": ["Alipay+ (cross-border AI payments)", "Antom Copilot (AI CFO)",
                        "AQ (AI healthcare app)", "AI risk scoring engine",
                        "Sesame Credit (AI credit scoring)", "AlphaFin (financial AI)",
                        "Distributed financial AI infrastructure",
                        "Real-time fraud detection ML", "ZOLOZ (AI identity)"],
        "known_strengths": ["GenAI / LLMs", "Machine Learning", "AI Governance"],
        "search_hints": ["Ant Group AI financial risk scoring architecture",
                         "Alipay AI fraud detection machine learning",
                         "Ant Group Antom AI platform engineering",
                         "Ant Group responsible AI financial inclusion"],
    },
    "paytm": {
        "industry": "Fintech / Payments AI / India",
        "blogs": ["paytm.com/about", "investors.paytm.com"],
        "known_stack": ["Paytm AI (fraud & credit scoring)", "Paytm Soundbox (edge AI)",
                        "UPI payment AI routing", "Paytm ML platform",
                        "Credit underwriting AI", "KYC AI (computer vision)",
                        "Merchant AI analytics", "AWS India infrastructure"],
        "known_strengths": ["Machine Learning", "AI Platforms", "Cloud AI Services"],
        "search_hints": ["Paytm AI fraud detection credit scoring India",
                         "Paytm machine learning payment routing architecture",
                         "Paytm UPI AI infrastructure engineering",
                         "Paytm ML platform credit underwriting"],
    },
    "kakao": {
        "industry": "Social / Fintech AI / South Korea",
        "blogs": ["kakao.com/en", "kakaoenterprise.com"],
        "known_stack": ["KakaoBrain (AI research lab)", "KoGPT (Korean LLM)",
                        "Kakao Pay AI (fraud, credit)", "Kakao Bank ML",
                        "Mindslab (voice AI)", "Kakao Enterprise AI platform",
                        "Kakao i (AI assistant)", "Karlo (text-to-image AI)"],
        "known_strengths": ["GenAI / LLMs", "Machine Learning", "AI Platforms"],
        "search_hints": ["KakaoBrain AI research KoGPT architecture Korea",
                         "Kakao Pay AI fraud detection financial ML",
                         "Kakao Enterprise AI platform engineering",
                         "Kakao i conversational AI infrastructure"],
    },

    # ── LATIN AMERICA — TECH ──────────────────────────────────────────────────
    "nubank": {
        "industry": "Fintech / Neobank AI / Latin America",
        "blogs": ["building.nubank.com.br", "ir.nubank.com.br"],
        "known_stack": ["Nu ML Platform (internal)", "Credit scoring AI (Clojure/Python)",
                        "Fraud detection ensemble models", "Flink (real-time data)",
                        "Datomic (data architecture)", "AWS (primary cloud)",
                        "Spark (data processing)", "Causal ML (credit decisions)",
                        "A/B experimentation platform", "NuX (customer AI)"],
        "known_strengths": ["Machine Learning", "Data Engineering", "MLOps / LLMOps"],
        "search_hints": ["Nubank ML platform credit scoring architecture Brazil",
                         "Nubank fraud detection machine learning engineering",
                         "Nubank data engineering Flink Datomic stack",
                         "Nubank AI credit underwriting causal inference"],
    },
    "mercado libre": {
        "industry": "E-commerce / Fintech AI / Latin America",
        "blogs": ["medium.com/mercadolibre-tech", "ir.mercadolibre.com"],
        "known_stack": ["Mercado Pago AI (fraud, credit)", "Recommendation engine (custom ML)",
                        "Meli AI (internal platform)", "PyTorch (training)",
                        "AWS + GCP (multi-cloud)", "Kafka (event streaming)",
                        "Spark (data processing)", "Credit underwriting ML",
                        "Computer vision (product catalog)", "NLP (search AI)"],
        "known_strengths": ["Machine Learning", "Data Engineering", "AI Platforms"],
        "search_hints": ["Mercado Libre ML platform recommendation engine architecture",
                         "Mercado Pago fraud detection AI engineering",
                         "Mercado Libre data engineering Kafka Spark stack",
                         "Meli AI platform machine learning infrastructure"],
    },
    "rappi": {
        "industry": "Super-app / Delivery AI / Latin America",
        "blogs": ["rappi.com/blog", "medium.com/rappi"],
        "known_stack": ["Route optimization ML", "Demand forecasting AI",
                        "Dynamic pricing models", "Rappi Turbo (supply chain AI)",
                        "RappiCard AI (credit scoring)", "Computer vision (order verification)",
                        "GCP (primary cloud)", "TensorFlow (training)",
                        "Real-time data pipeline", "Recommendation AI"],
        "known_strengths": ["Machine Learning", "Data Engineering", "Cloud AI Services"],
        "search_hints": ["Rappi route optimization machine learning Colombia",
                         "Rappi demand forecasting AI engineering platform",
                         "Rappi super-app ML infrastructure GCP",
                         "Rappi dynamic pricing recommendation AI"],
    },

    # ── LATIN AMERICA — FINTECH ───────────────────────────────────────────────
    "clip": {
        "industry": "Fintech / Payments AI / Mexico",
        "blogs": ["clip.mx/blog", "engineering.clip.mx"],
        "known_stack": ["Fraud detection ML (payments)", "Credit scoring AI (SMB)",
                        "POS terminal edge AI", "AWS Mexico (cloud)",
                        "Real-time transaction scoring", "KYC AI (computer vision)",
                        "Merchant analytics AI", "Open banking integrations"],
        "known_strengths": ["Machine Learning", "Cloud AI Services", "AI Platforms"],
        "search_hints": ["Clip Mexico payment fraud detection ML architecture",
                         "Clip fintech AI credit scoring SMB Mexico",
                         "Clip POS payment AI infrastructure engineering",
                         "Clip Mexico open banking AI platform"],
    },
    "uala": {
        "industry": "Fintech / Neobank AI / Argentina",
        "blogs": ["uala.com.ar/blog", "uala.com.ar/inversiones"],
        "known_stack": ["Credit scoring AI (thin-file)", "Fraud detection ML",
                        "UalaDis (investment AI)", "AWS (cloud)",
                        "Real-time payment processing", "KYC biometric AI",
                        "Behavioral analytics ML", "Open banking API platform"],
        "known_strengths": ["Machine Learning", "Cloud AI Services", "Data Engineering"],
        "search_hints": ["Uala Argentina neobank AI credit scoring architecture",
                         "Uala fraud detection machine learning fintech",
                         "Uala AI platform financial inclusion Argentina",
                         "Uala investment AI platform engineering"],
    },

    # ── AFRICA ────────────────────────────────────────────────────────────────
    "flutterwave": {
        "industry": "Fintech / Payments AI / Africa",
        "blogs": ["flutterwave.com/blog", "flutterwave.com/pst/developers"],
        "known_stack": ["Fraud detection ML (payments)", "Real-time risk scoring",
                        "Multi-currency AI routing", "AWS Africa (cloud)",
                        "Payment intelligence platform", "KYC AI verification",
                        "Merchant analytics dashboard", "API-first architecture"],
        "known_strengths": ["Machine Learning", "Cloud AI Services", "Data Engineering"],
        "search_hints": ["Flutterwave fraud detection AI payment Africa engineering",
                         "Flutterwave ML risk scoring payment routing",
                         "Flutterwave AI platform Africa infrastructure",
                         "Flutterwave payment intelligence machine learning"],
    },
    "safaricom": {
        "industry": "Telecom / Fintech AI / Africa",
        "blogs": ["safaricom.co.ke/newsroom", "safaricom.co.ke/personal/m-pesa"],
        "known_stack": ["M-Pesa AI (fraud, ML scoring)", "Safaricom AI platform",
                        "Network optimization ML", "Customer churn prediction AI",
                        "M-Pesa Daraja API (fintech)", "Azure Africa (cloud)",
                        "Predictive maintenance ML", "NLP (customer service AI)",
                        "30M+ user transaction ML", "Financial inclusion AI"],
        "known_strengths": ["Machine Learning", "Cloud AI Services", "Data Engineering"],
        "search_hints": ["M-Pesa Safaricom AI fraud detection machine learning Kenya",
                         "Safaricom AI platform network optimization engineering",
                         "M-Pesa transaction ML financial inclusion Africa",
                         "Safaricom Azure AI cloud infrastructure Kenya"],
    },
    "moniepoint": {
        "industry": "Fintech / SMB Banking AI / Africa",
        "blogs": ["moniepoint.com/blog", "moniepoint.com/business"],
        "known_stack": ["Credit scoring AI (SMB, informal sector)",
                        "Fraud detection ML (real-time)", "POS terminal network AI",
                        "AWS (cloud infrastructure)", "Financial data ML pipeline",
                        "Agent banking AI", "KYC AI (document + biometrics)",
                        "Merchant analytics platform"],
        "known_strengths": ["Machine Learning", "Cloud AI Services", "Data Engineering"],
        "search_hints": ["Moniepoint AI credit scoring SMB Africa Nigeria engineering",
                         "Moniepoint fraud detection machine learning fintech",
                         "Moniepoint AI banking platform Nigeria infrastructure",
                         "Moniepoint ML financial inclusion agent banking"],
    },

    # ── UK / EUROPE — TECH ────────────────────────────────────────────────────
    "deepmind": {
        "industry": "AI Research / Safety / UK",
        "blogs": ["deepmind.com/blog", "deepmind.com/research"],
        "known_stack": ["Gemini (co-developed with Google)", "AlphaFold (protein AI)",
                        "AlphaStar / AlphaGo (RL)", "Gato (generalist agent)",
                        "TPU training infrastructure (Google)", "JAX (primary ML framework)",
                        "Reinforcement learning platform", "AI safety research tooling",
                        "Lyria (music generation AI)", "GraphCast (weather AI)"],
        "known_strengths": ["GenAI / LLMs", "Machine Learning", "AI Governance"],
        "search_hints": ["DeepMind Gemini model architecture research",
                         "DeepMind AlphaFold protein AI infrastructure",
                         "DeepMind JAX reinforcement learning platform",
                         "DeepMind AI safety research engineering"],
    },

    # ── EUROPE — FINTECH ──────────────────────────────────────────────────────
    "revolut": {
        "industry": "Fintech / Neobank AI / Europe",
        "blogs": ["blog.revolut.com", "engineering.revolut.com"],
        "known_stack": ["Revolut AI (financial assistant)", "Fraud detection ML (real-time)",
                        "Credit scoring AI (dynamic)", "AWS + GCP (multi-cloud)",
                        "Kafka (event streaming)", "Spark (data processing)",
                        "Python + Kotlin ML stack", "Agentic finance features",
                        "Robo-advisor AI", "FX rate prediction ML"],
        "known_strengths": ["Machine Learning", "Data Engineering", "MLOps / LLMOps"],
        "search_hints": ["Revolut fraud detection machine learning architecture",
                         "Revolut AI financial assistant engineering 2025",
                         "Revolut ML platform credit scoring infrastructure",
                         "Revolut data engineering Kafka Spark stack"],
    },
    "adyen": {
        "industry": "Fintech / Payments AI / Europe",
        "blogs": ["adyen.com/blog", "adyen.com/knowledge-hub"],
        "known_stack": ["RevenueAccelerate (AI revenue optimization)",
                        "DataConnect (merchant intelligence)", "Fraud detection ML (Signifyd)",
                        "Network Token ML", "Adyen for Platforms AI",
                        "Custom payment routing ML", "AWS + on-premise hybrid",
                        "Real-time authorization AI", "Merchant data AI"],
        "known_strengths": ["Machine Learning", "Data Engineering", "Cloud AI Services"],
        "search_hints": ["Adyen fraud detection AI payment machine learning",
                         "Adyen RevenueAccelerate ML optimization architecture",
                         "Adyen payment routing AI engineering infrastructure",
                         "Adyen DataConnect merchant intelligence platform"],
    },
    "klarna": {
        "industry": "Fintech / BNPL AI / Europe",
        "blogs": ["klarna.com/international/press", "engineering.klarna.com"],
        "known_stack": ["Klarna AI (OpenAI partnership — GPT-4o)",
                        "Credit risk AI (dynamic underwriting)", "Fraud detection ML",
                        "Kustomer (AI customer service — acquired)", "Snowflake (data warehouse)",
                        "AWS (primary cloud)", "Real-time credit decisioning",
                        "Agentic shopping assistant", "85 AI agents (replacing 700 staff)"],
        "known_strengths": ["GenAI / LLMs", "Machine Learning", "Agentic AI"],
        "search_hints": ["Klarna AI OpenAI GPT integration architecture 2025",
                         "Klarna credit risk ML dynamic underwriting engineering",
                         "Klarna fraud detection machine learning platform",
                         "Klarna AI agents customer service automation"],
    },
    "wise": {
        "industry": "Fintech / FX AI / Cross-border Payments",
        "blogs": ["wise.com/gb/blog", "transferwise.com/us/engineering"],
        "known_stack": ["FX rate prediction ML", "Fraud detection AI (real-time)",
                        "Compliance automation ML (KYC/AML)", "AWS (primary cloud)",
                        "Kafka (event streaming)", "Wise Platform API AI",
                        "Dynamic pricing ML", "Document verification AI (computer vision)",
                        "Multi-currency routing optimization"],
        "known_strengths": ["Machine Learning", "Data Engineering", "Cloud AI Services"],
        "search_hints": ["Wise Transferwise FX prediction machine learning architecture",
                         "Wise fraud detection AI compliance engineering",
                         "Wise ML platform payment routing infrastructure",
                         "Wise KYC AML AI automation engineering"],
    },
}

def get_company_intel(company: str) -> dict:
    """Return pre-loaded intel for known top-tier companies, or empty dict."""
    key = company.lower().strip()
    # Direct match
    if key in COMPANY_INTEL:
        return COMPANY_INTEL[key]
    # Partial match
    for k, v in COMPANY_INTEL.items():
        if k in key or key in k:
            return v
    return {}

def enrich_queries(base_queries: list, intel: dict) -> list:
    """Add company-specific targeted queries if intel is available."""
    if not intel:
        return base_queries
    enriched = list(base_queries)
    for hint in intel.get("search_hints", [])[:3]:
        enriched.append(hint)
    for blog in intel.get("blogs", [])[:2]:
        enriched.append(f"site:{blog} AI infrastructure machine learning")
    return enriched


# ── Global AI Compliance Framework ───────────────────────────────────────────
# Key regulatory frameworks the governance audit step must assess.
# Organized by jurisdiction and relevance tier (CRITICAL / HIGH / MEDIUM).
GLOBAL_COMPLIANCE = {

    # ── EUROPEAN UNION ─────────────────────────────────────────────────────────
    "EU AI Act (2024)": {
        "jurisdiction": "European Union",
        "tier": "CRITICAL",
        "effective": "Aug 2024 (phased to 2027)",
        "scope": "All AI systems deployed in the EU, regardless of where developed",
        "key_requirements": [
            "Prohibited AI practices banned from Feb 2025 (social scoring, real-time biometric surveillance in public)",
            "High-risk AI systems require conformity assessment, registration, human oversight",
            "General Purpose AI (GPAI) models >10^25 FLOPs face systemic risk obligations",
            "Foundation model providers must document training data, energy use, capabilities",
            "Transparency obligations for AI-generated content (deepfakes, chatbots)",
            "Right to explanation for high-risk AI decisions",
        ],
        "penalties": "Up to €35M or 7% global annual turnover",
        "url": "https://artificialintelligenceact.eu",
    },
    "GDPR (2018) + AI Implications": {
        "jurisdiction": "European Union",
        "tier": "CRITICAL",
        "effective": "May 2018 (ongoing enforcement)",
        "scope": "Any processing of EU residents' personal data",
        "key_requirements": [
            "Lawful basis required for training AI on personal data",
            "Data minimisation — only collect what AI genuinely needs",
            "Right to erasure ('right to be forgotten') — must be honoured in AI systems",
            "Automated decision-making rights (Art. 22) — right to human review",
            "Data Protection Impact Assessment (DPIA) mandatory for high-risk AI processing",
            "Privacy by design and by default in AI system architecture",
            "Cross-border data transfers require adequacy decision or SCCs",
        ],
        "penalties": "Up to €20M or 4% global annual turnover",
        "url": "https://gdpr.eu",
    },
    "EU Data Act (2024)": {
        "jurisdiction": "European Union",
        "tier": "HIGH",
        "effective": "Sep 2025",
        "scope": "Data generated by IoT devices, cloud services, and data spaces in EU",
        "key_requirements": [
            "Data sharing obligations between businesses and consumers",
            "Cloud switching rights — must support data portability",
            "B2G data sharing in public emergencies",
            "Contractual protections for data holders in B2B relationships",
        ],
        "penalties": "Up to €20M or 4% global turnover",
        "url": "https://digital-strategy.ec.europa.eu/en/policies/data-act",
    },
    "EU Digital Services Act / DSA (2022)": {
        "jurisdiction": "European Union",
        "tier": "HIGH",
        "effective": "Feb 2024 (VLOPs/VLOSEs from Aug 2023)",
        "scope": "Online platforms and search engines serving EU users",
        "key_requirements": [
            "Algorithmic transparency and explainability for recommender systems",
            "Annual risk assessments for Very Large Online Platforms (VLOPs)",
            "Ad targeting restrictions (profiling minors prohibited)",
            "Access to data for researchers",
            "Crisis response protocols for AI-powered disinformation",
        ],
        "penalties": "Up to 6% global annual turnover; repeat offenders can be banned",
        "url": "https://digital-strategy.ec.europa.eu/en/policies/digital-services-act-package",
    },

    # ── UNITED STATES ──────────────────────────────────────────────────────────
    "US Executive Order on AI (Oct 2023)": {
        "jurisdiction": "United States",
        "tier": "CRITICAL",
        "effective": "Oct 2023 (ongoing agency rulemaking)",
        "scope": "Federal agencies and companies doing business with US government; dual-use AI",
        "key_requirements": [
            "AI safety testing for foundation models before deployment (NIST AI RMF alignment)",
            "Mandatory reporting for AI models trained above compute thresholds",
            "Watermarking/authentication of AI-generated content",
            "Equity and civil rights protections in AI systems",
            "Critical infrastructure AI risk management",
        ],
        "penalties": "Contractual and procurement consequences for federal contractors",
        "url": "https://www.whitehouse.gov/briefing-room/presidential-actions/2023/10/30/executive-order-on-the-safe-secure-and-trustworthy-development-and-use-of-artificial-intelligence/",
    },
    "CCPA / CPRA (2020/2023)": {
        "jurisdiction": "United States — California",
        "tier": "CRITICAL",
        "effective": "Jan 2020 / Jan 2023",
        "scope": "Businesses collecting personal data of California residents",
        "key_requirements": [
            "Right to know what personal data is collected and used in AI training",
            "Right to opt-out of sale or sharing of personal data",
            "Right to correct inaccurate personal data",
            "Sensitive personal information restrictions (biometrics, health, race)",
            "Automated decision-making: right to opt-out and obtain explanation",
        ],
        "penalties": "Up to $7,500 per intentional violation",
        "url": "https://cppa.ca.gov",
    },
    "NIST AI Risk Management Framework (2023)": {
        "jurisdiction": "United States (voluntary, widely adopted globally)",
        "tier": "HIGH",
        "effective": "Jan 2023",
        "scope": "Voluntary framework for managing AI risks across any organisation",
        "key_requirements": [
            "GOVERN: Establish AI risk culture, policies, and accountability structures",
            "MAP: Identify and categorise AI risks in context",
            "MEASURE: Analyse and assess AI risks with metrics",
            "MANAGE: Prioritise and treat AI risks with defined controls",
        ],
        "penalties": "Voluntary — but referenced in US federal procurement and sector regulation",
        "url": "https://www.nist.gov/artificial-intelligence",
    },
    "US State AI Laws (2024-25 wave)": {
        "jurisdiction": "United States — Multiple States",
        "tier": "HIGH",
        "effective": "Varies by state (2024-2026)",
        "scope": "Colorado, Texas, Illinois, Connecticut, Virginia AI regulation wave",
        "key_requirements": [
            "Colorado SB 205: High-risk AI developer and deployer obligations (2026)",
            "Illinois BIPA: Biometric data collection and AI facial recognition consent",
            "Texas AI in Employment: Restrictions on AI use in hiring decisions",
            "Virginia VCDPA: Automated profiling opt-out rights",
        ],
        "penalties": "Varies by state — up to $50K per violation (Colorado)",
        "url": "https://www.ncsl.org/technology-and-communication/artificial-intelligence-2024-legislation",
    },

    # ── UNITED KINGDOM ─────────────────────────────────────────────────────────
    "UK AI Regulation (Pro-Innovation Approach)": {
        "jurisdiction": "United Kingdom",
        "tier": "HIGH",
        "effective": "2024 onwards (existing law + sector guidance)",
        "scope": "AI systems deployed or developed in the UK",
        "key_requirements": [
            "Principles-based approach: safety, transparency, fairness, accountability, contestability",
            "Sector-specific regulators enforce AI rules (FCA, ICO, CMA, MHRA)",
            "ICO Guidance on AI and data protection (GDPR UK equivalent)",
            "AI Safety Institute: frontier model evaluations (AISI)",
            "Mandatory AI incident reporting under discussion",
        ],
        "penalties": "Sector-specific — ICO up to £17.5M or 4% global turnover",
        "url": "https://www.gov.uk/government/publications/ai-regulation-a-pro-innovation-approach",
    },

    # ── CHINA ──────────────────────────────────────────────────────────────────
    "China Generative AI Regulations (2023)": {
        "jurisdiction": "China",
        "tier": "CRITICAL",
        "effective": "Aug 2023",
        "scope": "Generative AI services provided to users in China",
        "key_requirements": [
            "Content must adhere to socialist core values; no content subverting state power",
            "Training data must have clear IP licensing",
            "Mandatory labelling of AI-generated content",
            "Security assessment required before public deployment",
            "User data localisation within China",
            "Algorithmic recommendation regulations (Mar 2022) for AI-driven feeds",
        ],
        "penalties": "Service suspension, fines, criminal liability for severe cases",
        "url": "https://www.cac.gov.cn",
    },

    # ── GLOBAL / SECTOR-SPECIFIC ───────────────────────────────────────────────
    "ISO/IEC 42001 — AI Management System (2023)": {
        "jurisdiction": "Global (ISO standard)",
        "tier": "HIGH",
        "effective": "Dec 2023",
        "scope": "Any organisation developing, providing, or using AI systems",
        "key_requirements": [
            "Establish an AI Management System (AIMS) with documented policies",
            "AI risk assessment and impact assessment procedures",
            "Roles and responsibilities for AI governance",
            "Continuous monitoring and improvement of AI systems",
            "Aligns with ISO 27001 (InfoSec) and ISO 9001 (Quality)",
        ],
        "penalties": "Voluntary — but increasingly required by enterprise procurement",
        "url": "https://www.iso.org/standard/81230.html",
    },
    "HIPAA + AI (US Healthcare)": {
        "jurisdiction": "United States — Healthcare",
        "tier": "CRITICAL",
        "effective": "Ongoing; HHS AI guidance 2024",
        "scope": "AI systems processing Protected Health Information (PHI)",
        "key_requirements": [
            "PHI cannot be used to train AI models without explicit authorisation or de-identification",
            "Business Associate Agreements (BAA) required with AI vendors",
            "AI clinical decision support tools may require FDA clearance",
            "Audit trails for AI-assisted clinical decisions",
            "HHS guidance: AI must not introduce bias in covered entity decisions",
        ],
        "penalties": "Up to $1.9M per violation category per year",
        "url": "https://www.hhs.gov/hipaa/index.html",
    },
    "PCI-DSS v4.0 + AI (Payment)": {
        "jurisdiction": "Global — Payment Industry",
        "tier": "HIGH",
        "effective": "Mar 2024 (v4.0)",
        "scope": "Any AI systems handling cardholder data or payment processes",
        "key_requirements": [
            "AI fraud detection systems must not store raw PAN data beyond need",
            "Penetration testing must include AI/ML components",
            "Automated security testing of AI pipelines handling card data",
            "Targeted risk analysis for AI system customised controls",
        ],
        "penalties": "Fines from card brands; loss of ability to process payments",
        "url": "https://www.pcisecuritystandards.org",
    },
    "SOC 2 Type II + AI Controls": {
        "jurisdiction": "Global (AICPA standard, widely required)",
        "tier": "HIGH",
        "effective": "Ongoing — annual audits",
        "scope": "SaaS and cloud AI service providers",
        "key_requirements": [
            "AI model access controls and logical security",
            "Change management for model updates and retraining",
            "Availability SLAs for AI inference services",
            "Confidentiality of training data and model weights",
            "Processing integrity — AI outputs are complete and accurate",
        ],
        "penalties": "Loss of enterprise customers; failed procurement requirements",
        "url": "https://www.aicpa.org/resources/article/soc-2-reporting-on-an-examination-of-controls",
    },
}

def get_compliance_context(company: str, industry: str = "") -> str:
    """
    Return a concise compliance context string for the governance audit step.
    Selects the most relevant frameworks based on company geography and industry.
    """
    intel  = get_company_intel(company)
    ind    = (intel.get("industry","") or industry or "").lower()
    is_eu  = any(k in company.lower() for k in
                 ["aleph alpha","deepl","stability","synthesia"]) or "europe" in ind
    is_health   = any(x in ind for x in ["health","pharma","medical","biotech"])
    is_payment  = any(x in ind for x in ["payment","fintech","banking","finance"])
    is_china    = "china" in ind
    is_consumer = any(x in ind for x in ["consumer","social","media","entertainment","streaming"])

    lines = ["KEY COMPLIANCE FRAMEWORKS TO ASSESS IN GOVERNANCE AUDIT:\n"]
    for name, fw in GLOBAL_COMPLIANCE.items():
        tier = fw["tier"]
        jur  = fw["jurisdiction"]
        # Always include CRITICAL global/EU frameworks
        if tier == "CRITICAL":
            lines.append(f"▸ [{tier}] {name} ({jur})")
            lines.append(f"  Effective: {fw['effective']}")
            lines.append(f"  Scope: {fw['scope']}")
            top_reqs = fw["key_requirements"][:2]
            for r in top_reqs:
                lines.append(f"  • {r}")
            lines.append("")
        # Conditionally include HIGH frameworks
        elif tier == "HIGH":
            include = False
            if "ISO" in name: include = True
            if is_eu   and "EU" in jur:       include = True
            if is_eu   and "United Kingdom" in jur: include = True
            if is_health and "HIPAA" in name: include = True
            if is_payment and "PCI" in name:  include = True
            if is_china and "China" in jur:   include = True
            if is_consumer and "DSA" in name: include = True
            if "SOC 2" in name:               include = True
            if "NIST" in name:                include = True
            if include:
                lines.append(f"▸ [{tier}] {name} ({jur})")
                lines.append(f"  Effective: {fw['effective']}")
                lines.append(f"  Key: {fw['key_requirements'][0]}")
                lines.append("")

    lines.append("Score governance category with these frameworks in mind.")
    lines.append("Flag any critical gaps, missing policies, or likely non-compliance signals.")
    return "\n".join(lines)


# ── ROI Calculation Framework ─────────────────────────────────────────────────
# Evidence-based cost and ROI estimates per AI infrastructure gap category.
# Sources: Gartner, McKinsey, Forrester, DORA reports, industry benchmarks.
# All figures are ranges — agent selects appropriate point based on company size.

ROI_FRAMEWORK = {
    "GenAI / LLMs": {
        "gap_cost_range": "$150K–$2M/year",
        "gap_cost_drivers": [
            "Engineer hours spent on manual content/code tasks that GenAI would automate",
            "Lost competitive differentiation vs AI-native competitors",
            "Delayed product shipping due to lack of AI-assisted development",
        ],
        "fix_cost_range": "$20K–$150K",
        "fix_cost_drivers": "API costs + integration engineering + prompt engineering",
        "roi_range": "200–500%",
        "payback_months": "2–6 months",
        "roi_basis": "McKinsey: GenAI adoption saves 20-40% of knowledge worker time",
    },
    "Agentic AI": {
        "gap_cost_range": "$200K–$3M/year",
        "gap_cost_drivers": [
            "Manual orchestration of multi-step workflows that agents would automate",
            "Human review bottlenecks in repetitive decision pipelines",
            "Competitive gap vs companies shipping agentic products",
        ],
        "fix_cost_range": "$50K–$300K",
        "fix_cost_drivers": "Framework licensing + agent development + orchestration infrastructure",
        "roi_range": "300–800%",
        "payback_months": "3–9 months",
        "roi_basis": "Forrester: Agentic AI reduces process cycle times by 60-80%",
    },
    "Machine Learning": {
        "gap_cost_range": "$300K–$5M/year",
        "gap_cost_drivers": [
            "Revenue lost to poor personalization, pricing, or fraud detection",
            "Engineering rework from ad-hoc ML without proper infrastructure",
            "Model incidents caused by lack of monitoring",
        ],
        "fix_cost_range": "$100K–$500K",
        "fix_cost_drivers": "Platform licensing + ML engineering + compute infrastructure",
        "roi_range": "400–1200%",
        "payback_months": "4–12 months",
        "roi_basis": "MIT: ML-mature companies achieve 2x revenue growth vs peers",
    },
    "Data Engineering": {
        "gap_cost_range": "$250K–$4M/year",
        "gap_cost_drivers": [
            "Data team hours spent on unreliable pipeline maintenance",
            "Business decisions delayed by poor data availability",
            "AI initiatives blocked by data quality issues",
        ],
        "fix_cost_range": "$80K–$400K",
        "fix_cost_drivers": "Modern data stack tooling + data engineering + migration",
        "roi_range": "250–600%",
        "payback_months": "6–12 months",
        "roi_basis": "DAMA: Poor data quality costs organizations 15-25% of revenue",
    },
    "AI Platforms": {
        "gap_cost_range": "$200K–$3M/year",
        "gap_cost_drivers": [
            "Duplicated tooling across teams without shared platform",
            "Slow model deployment cycles (weeks vs hours)",
            "Inability to scale AI experiments to production",
        ],
        "fix_cost_range": "$100K–$600K",
        "fix_cost_drivers": "Platform build/buy + DevOps + model serving infrastructure",
        "roi_range": "200–500%",
        "payback_months": "6–18 months",
        "roi_basis": "DORA: High-performing ML teams deploy 10x faster with proper platforms",
    },
    "MLOps / LLMOps": {
        "gap_cost_range": "$150K–$2M/year",
        "gap_cost_drivers": [
            "Model incidents and regressions caught late costing engineering time",
            "LLM output quality degradation undetected in production",
            "Compliance exposure from unmonitored AI decisions",
            "Time spent on manual model retraining and deployment",
        ],
        "fix_cost_range": "$40K–$250K",
        "fix_cost_drivers": "LLMOps tooling (LangSmith/Arize/etc.) + observability + CI/CD for models",
        "roi_range": "300–700%",
        "payback_months": "2–6 months",
        "roi_basis": "Gartner: 85% of AI projects fail — MLOps halves failure rate",
    },
    "Cloud AI Services": {
        "gap_cost_range": "$100K–$1.5M/year",
        "gap_cost_drivers": [
            "Building custom infrastructure that managed cloud AI services provide",
            "Over-provisioned compute from lack of managed scaling",
            "Missing cloud-native AI capabilities requiring rebuild",
        ],
        "fix_cost_range": "$20K–$150K",
        "fix_cost_drivers": "Cloud AI service migration + architecture + training",
        "roi_range": "150–400%",
        "payback_months": "3–9 months",
        "roi_basis": "AWS/GCP/Azure: Managed AI services reduce infrastructure cost by 30-60%",
    },
    "Governance / Compliance": {
        "gap_cost_range": "$500K–$50M+ (regulatory fine exposure)",
        "gap_cost_drivers": [
            "GDPR/CCPA violation fines (up to 4% global revenue)",
            "EU AI Act penalties (up to 7% global revenue)",
            "Regulatory audit costs and remediation",
            "Reputational damage from AI incidents",
        ],
        "fix_cost_range": "$30K–$300K",
        "fix_cost_drivers": "Legal review + governance framework + tooling + training",
        "roi_range": "500–10000% (risk-adjusted)",
        "payback_months": "Immediate — risk mitigation",
        "roi_basis": "IBM: Average cost of AI compliance failure = $4.45M",
    },
    "Redundancy Elimination": {
        "gap_cost_range": "$50K–$2M/year",
        "gap_cost_drivers": [
            "Duplicate SaaS subscriptions for overlapping AI capabilities",
            "Engineering time maintaining redundant integrations",
            "Inconsistent outputs from competing AI systems",
        ],
        "fix_cost_range": "$10K–$50K",
        "fix_cost_drivers": "Audit + consolidation + migration + training",
        "roi_range": "200–800%",
        "payback_months": "1–3 months",
        "roi_basis": "Gartner: Average enterprise has 30-40% redundant SaaS spend",
    },
}

def get_roi_context(company_size: str = "", industry: str = "") -> str:
    """Build ROI framework context for the agent to use in recommendations."""
    size_multipliers = {
        "startup": "Use the lower end of all cost ranges.",
        "growth":  "Use the lower-to-mid range of cost estimates.",
        "mid-market": "Use mid-range cost estimates.",
        "enterprise": "Use upper-mid to high end of cost ranges.",
        "large enterprise": "Use the high end of all cost ranges.",
    }
    size_key = "mid-market"
    for k in size_multipliers:
        if k in company_size.lower():
            size_key = k
            break

    lines = [
        "ROI CALCULATION FRAMEWORK — Use these benchmarks to quantify every recommendation:",
        f"Company size guidance: {size_multipliers.get(size_key, 'Use mid-range estimates.')}",
        "",
    ]
    for domain, data in ROI_FRAMEWORK.items():
        lines.append(f"[{domain}]")
        lines.append(f"  Gap Cost:    {data['gap_cost_range']}/year")
        lines.append(f"  Fix Cost:    {data['fix_cost_range']}")
        lines.append(f"  ROI:         {data['roi_range']} in 12 months")
        lines.append(f"  Payback:     {data['payback_months']}")
        lines.append(f"  Basis:       {data['roi_basis']}")
        lines.append("")

    lines.append("FORMAT for each recommendation:")
    lines.append("  Action | Business justification | Gap Cost: $X/year | Fix Cost: ~$X")
    lines.append("  Projected ROI: X% | Payback: X months | Impact: H/M/L | Owner: role")
    return "\n".join(lines)


# ── Prescription Priority Framework ──────────────────────────────────────────
# Used by the agent to score and prioritize recommendations consistently.
# Priority Score = (Impact × Urgency) ÷ Complexity
# Impact:    1–5 (revenue/risk effect)
# Urgency:   1–5 (time sensitivity)
# Complexity: 1–5 (implementation effort)

PRESCRIPTION_PRIORITY = {
    "CRITICAL": {
        "criteria": [
            "Compliance violation risk (regulatory fine exposure)",
            "Security vulnerability in AI systems",
            "Score gap > 5 points in any domain",
            "Gap cost > $500K/year",
            "Competitive threat — competitor has capability, you don't",
        ],
        "sla": "Address within 30 days",
        "color": "🔴",
    },
    "HIGH": {
        "criteria": [
            "Significant revenue or cost impact ($100K–$500K/year)",
            "Score gap 3–5 points in any domain",
            "Blocking other improvements (dependency chain)",
            "Customer-facing AI quality issues",
        ],
        "sla": "Address within 90 days",
        "color": "🟠",
    },
    "MEDIUM": {
        "criteria": [
            "Moderate improvement opportunity ($50K–$100K/year)",
            "Score gap 1–3 points",
            "Best practice gap without immediate risk",
            "Technical debt accumulation",
        ],
        "sla": "Address within 6 months",
        "color": "🟡",
    },
    "LOW": {
        "criteria": [
            "Optimization opportunity (< $50K/year impact)",
            "Minor gap vs industry best practice",
            "Nice-to-have capability",
            "Future-proofing",
        ],
        "sla": "Address within 12 months",
        "color": "🟢",
    },
}

# ── Industry Value Map (REWIRED: highest-value AI domains per sector) ─────────
# Source: McKinsey REWIRED — prioritize investments by domain value for the sector.
# Used to rerank prescriptions so the highest-ROI domains surface first.

INDUSTRY_VALUE_MAP = {
    "fintech": {
        "top_domains": ["Machine Learning", "Data Engineering", "MLOps / LLMOps"],
        "why": "Fraud detection, credit scoring, and real-time decisioning are table-stakes competitive advantages",
        "benchmark_hints": ["fintech AI fraud detection ML benchmark", "neobank credit scoring AI stack"],
        "gap_signals": ["real-time inference <50ms", "causal ML for credit", "AML model monitoring"],
    },
    "healthcare": {
        "top_domains": ["AI Platforms", "Governance / Compliance", "Machine Learning"],
        "why": "FDA clearance requirements and PHI constraints make governance the unlock for everything else",
        "benchmark_hints": ["healthcare AI platform HIPAA compliance benchmark", "clinical ML FDA clearance"],
        "gap_signals": ["HIPAA-compliant model training", "clinical decision support audit trails", "bias monitoring"],
    },
    "ecommerce": {
        "top_domains": ["GenAI / LLMs", "Machine Learning", "Data Engineering"],
        "why": "Personalization and recommendation engines directly compound revenue per visit",
        "benchmark_hints": ["ecommerce recommendation AI stack benchmark", "retail personalization ML platform"],
        "gap_signals": ["real-time recommendation latency", "A/B testing infrastructure", "demand forecasting"],
    },
    "media": {
        "top_domains": ["GenAI / LLMs", "Agentic AI", "MLOps / LLMOps"],
        "why": "Content generation velocity and recommendation quality are the core competitive levers",
        "benchmark_hints": ["media company GenAI content production stack", "streaming recommendation ML benchmark"],
        "gap_signals": ["content moderation AI", "personalization at scale", "synthetic media governance"],
    },
    "enterprise_software": {
        "top_domains": ["Agentic AI", "GenAI / LLMs", "Cloud AI Services"],
        "why": "AI-native product features and copilots are now table-stakes for enterprise SaaS retention",
        "benchmark_hints": ["enterprise SaaS AI copilot feature benchmark", "B2B software GenAI adoption"],
        "gap_signals": ["in-product AI assistant", "workflow automation agents", "customer-facing LLM features"],
    },
    "semiconductors": {
        "top_domains": ["AI Platforms", "Machine Learning", "Cloud AI Services"],
        "why": "Yield optimization and predictive maintenance ML directly reduce CapEx at scale",
        "benchmark_hints": ["semiconductor AI yield optimization ML benchmark", "chip design AI platform"],
        "gap_signals": ["process yield ML", "chip design automation", "supply chain AI"],
    },
    "logistics": {
        "top_domains": ["Machine Learning", "Data Engineering", "Agentic AI"],
        "why": "Route optimization and demand forecasting are the highest-ROI AI investments in this sector",
        "benchmark_hints": ["logistics AI route optimization benchmark", "supply chain ML platform"],
        "gap_signals": ["dynamic routing ML", "demand forecasting accuracy", "autonomous agent dispatch"],
    },
    "telecom": {
        "top_domains": ["Data Engineering", "Machine Learning", "Cloud AI Services"],
        "why": "Network optimization and churn prediction ML directly impact margins at scale",
        "benchmark_hints": ["telecom AI network optimization benchmark", "telco churn prediction ML"],
        "gap_signals": ["network anomaly detection", "predictive maintenance", "customer churn ML"],
    },
    "social_media": {
        "top_domains": ["Machine Learning", "Data Engineering", "MLOps / LLMOps"],
        "why": "Recommendation quality and content moderation reliability define product retention",
        "benchmark_hints": ["social media recommendation ML benchmark", "content moderation AI scale"],
        "gap_signals": ["recommendation freshness", "moderation latency", "A/B experimentation velocity"],
    },
    "default": {
        "top_domains": ["GenAI / LLMs", "MLOps / LLMOps", "Data Engineering"],
        "why": "These three domains deliver the highest cross-industry ROI for most companies",
        "benchmark_hints": [],
        "gap_signals": [],
    },
}

def detect_industry_slug(company: str, intel: dict, industry_hint: str = "") -> str:
    """Map company/industry string to an INDUSTRY_VALUE_MAP key."""
    combined = (intel.get("industry", "") + " " + industry_hint).lower()
    mapping = {
        "fintech":            ["fintech", "payment", "banking", "neobank", "credit", "insurance"],
        "healthcare":         ["health", "pharma", "medical", "biotech", "clinical"],
        "ecommerce":          ["ecommerce", "e-commerce", "retail", "marketplace", "shopping"],
        "media":              ["media", "streaming", "entertainment", "content", "music", "video"],
        "enterprise_software":["enterprise software", "saas", "b2b software", "crm", "erp"],
        "semiconductors":     ["semiconductor", "chip", "hardware", "silicon", "gpu"],
        "logistics":          ["logistics", "supply chain", "shipping", "freight", "delivery"],
        "telecom":            ["telecom", "telco", "wireless", "carrier", "network operator"],
        "social_media":       ["social media", "social network", "platform"],
    }
    for slug, keywords in mapping.items():
        if any(kw in combined for kw in keywords):
            return slug
    return "default"

def get_industry_context(company: str, intel: dict, industry_hint: str = "") -> str:
    """Return industry-weighted priority context for the agent."""
    slug = detect_industry_slug(company, intel, industry_hint)
    data = INDUSTRY_VALUE_MAP.get(slug, INDUSTRY_VALUE_MAP["default"])
    lines = [
        f"INDUSTRY-WEIGHTED PRIORITIES ({slug.replace('_', ' ').title()}):",
        f"Top value domains for this sector: {', '.join(data['top_domains'])}",
        f"Why: {data['why']}",
        f"Key gap signals to look for: {', '.join(data['gap_signals']) or 'standard gaps apply'}",
        "",
        "INSTRUCTION: When ranking prescriptions, surface gaps in the top_domains listed above",
        "first, unless a CRITICAL compliance or security issue overrides the order.",
    ]
    return "\n".join(lines)


# ── Maturity Ladder Signals (REWIRED: death by pilots calibration) ────────────
# Sharpens the 5-level maturity ladder with concrete observable signals.
# Adds "Scaling Purgatory" — the most common stuck state per McKinsey research.

MATURITY_SIGNALS = {
    "Experimenting": [
        "Running AI pilots with no production deployments",
        "No dedicated ML engineering team",
        "AI tools chosen by individual engineers, not centrally governed",
    ],
    "Building": [
        "1-2 production AI systems live",
        "Small ML team (1-5 engineers) hired",
        "Basic MLOps: model versioning or experiment tracking in place",
    ],
    "Scaling": [
        "Multiple production AI systems across 2+ business units",
        "Dedicated ML platform team or internal AI platform forming",
        "Structured MLOps with CI/CD for models",
        "⚠ SCALING PURGATORY: many pilots, inconsistent production rollout — flag this explicitly",
    ],
    "Optimizing": [
        "AI embedded in core product and operational workflows",
        "LLMOps / model monitoring in place with alerting",
        "Formal AI governance policy and model inventory",
        "Cross-functional AI product teams (not siloed ML team)",
    ],
    "Leading": [
        "AI is a core competitive moat, not a cost center",
        "Published research, open-source contributions, or industry-first AI features",
        "CAIO or equivalent C-suite AI leadership",
        "AI talent density: 10%+ of engineering in AI/ML roles",
    ],
}

QUICK_WIN_EXAMPLES = {
    "GenAI / LLMs": [
        "Sign up for Anthropic Claude API free tier — test in sandbox this week",
        "Enable GitHub Copilot trial for engineering team — 30 days free",
        "Run a 2-hour GenAI prompt engineering workshop with your team",
    ],
    "MLOps / LLMOps": [
        "Enable LangSmith free tier for LLM observability — zero cost",
        "Set up basic model monitoring with free Evidently AI",
        "Create a model incident runbook this week — costs only time",
    ],
    "Data Engineering": [
        "Audit your top 3 data pipelines for failures — free with existing tools",
        "Enable dbt Cloud free tier for data transformation visibility",
        "Document your data lineage in a single shared doc this week",
    ],
    "Governance / Compliance": [
        "Draft a 1-page AI usage policy this week — costs only time",
        "Create an AI model inventory spreadsheet — free, immediate value",
        "Schedule a 1-hour compliance review with your legal team",
    ],
    "Agentic AI": [
        "Explore LangChain free tier — build a simple agent prototype this week",
        "Map your top 3 manual workflows that could be automated — costs only time",
        "Join the CrewAI community and review open-source agent examples",
    ],
}

def get_prescription_context() -> str:
    """Build concise prescription framework context for the agent."""
    lines = [
        "PRESCRIPTION PRIORITY LEVELS:",
        "  CRITICAL = compliance risk OR gap >5pts OR cost >$500K/year → fix in 30 days",
        "  HIGH     = revenue/cost impact $100K-$500K OR gap 3-5pts → fix in 90 days",
        "  MEDIUM   = improvement opportunity $50K-$100K OR gap 1-3pts → fix in 6 months",
        "  LOW      = optimization OR best practice gap → fix in 12 months",
        "",
        "QUICK WIN EXAMPLES (one per prescription, free or <$500):",
        "  MLOps/LLMOps: Enable LangSmith free tier — zero cost",
        "  GenAI/LLMs:   Sign up for Claude API free tier — zero cost",
        "  Data Eng:     Audit top 3 pipelines with existing tools — zero cost",
        "  Governance:   Draft 1-page AI policy — costs only time",
        "  Agentic:      Map top 3 automatable workflows — costs only time",
    ]
    return "\n".join(lines)


# ── Deprecation Risk Intelligence (State of Martech 2026) ────────────────────
# Source: Brinker & Riemersma, State of Martech 2026
# Content Marketing had the largest net decline: -37 tools (-176 removed, +139 added)
# These categories/tools are at highest risk of being absorbed by major AI platforms

DEPRECATION_RISK_CATEGORIES = {
    "HIGH_RISK": [
        # Content AI — first wave being absorbed by ChatGPT/Claude/Gemini
        "Jasper", "Copy.ai", "Writesonic", "Anyword", "Persado", "Phrasee",
        "Lately", "Lumen5", "Lately.ai", "Rytr", "Peppertype",
        # Standalone chatbots being absorbed by major platforms
        "Drift", "Intercom (standalone AI)", "Drift AI",
        # Standalone AI image tools being absorbed
        "standalone DALL-E wrapper", "standalone Stable Diffusion wrapper",
    ],
    "MEDIUM_RISK": [
        # Tools where major platforms have built equivalent features
        "Grammarly Business AI", "Hemingway Editor",
        "standalone SEO AI writers", "standalone social caption tools",
        "basic AI personalization engines",
    ],
    "WATCH_LIST": [
        # Categories under pressure per State of Martech 2026
        "Sales Automation point solutions",  # -23 net
        "Social Media AI monitoring",         # -8 net
        "Live Chat standalone AI",            # -23 net
        "Video Marketing AI tools",           # -14 net
    ]
}

MARTECH_2026_CONTEXT = """
KEY MARKET INTELLIGENCE — State of Martech 2026 (Brinker & Riemersma):
- 15,505 total martech tools in 2026 — effectively flat (+0.79% growth)
- UNDER THE SURFACE: 1,488 new tools added, 1,367 removed — market is churning
- Content Marketing: LARGEST NET DECLINE (-37 tools, -176 removed vs +139 added)
  → First wave of AI content tools being absorbed by ChatGPT, Claude, Gemini
- Governance, Compliance & Privacy: 7.1% GROWTH — buyers actively spending here
- 88 out of 130 marketing leaders NOT using AI to manage their own stack
- Only 8% of organizations confident in their AI governance readiness
- "AI everywhere, integrated nowhere" — most orgs in the Chrysalis phase
- MCP protocol: 29,000+ servers in 18 months — integration layer maturing fast
- Data silos remain the #1 constraint on AI effectiveness

DEPRECATION RISK SIGNAL: When auditing any company's AI stack, flag tools in
the HIGH_RISK category above as potential consolidation opportunities.
Estimate annual spend waste from deprecated or at-risk tools.
"""

STATE_OF_AI_STACK_HEALTH_TEASER = """
────────────────────────────────────────────────────
📊 CONTRIBUTING TO THE STATE OF AI STACK HEALTH 2027
This audit contributes anonymised benchmark data to the first-ever
State of AI Stack Health annual report — publishing Q1 2027.
The report will track AI stack maturity trends across 500+ companies
globally — the Bloomberg data moat for AI infrastructure intelligence.
────────────────────────────────────────────────────
"""

def get_deprecation_context() -> str:
    """Return market intelligence for stack health assessment."""
    high_risk = ", ".join(DEPRECATION_RISK_CATEGORIES["HIGH_RISK"][:8])
    return MARTECH_2026_CONTEXT + f"\nHIGH DEPRECATION RISK TOOLS: {high_risk} (and similar point solutions)"


# ── System Prompt v3 ──────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are an elite AI infrastructure analyst with deep knowledge of the world's leading
tech companies' AI stacks. You combine marketing operations audit rigor with expert
knowledge of modern AI infrastructure across GenAI, Agentic AI, ML, Data Engineering,
AI Platforms, MLOps/LLMOps, and Cloud AI Services.

IMPORTANT CONTEXT:
- If analyzing a top-tier company (Meta, NVIDIA, OpenAI, Microsoft, Google, Amazon,
  Apple, Netflix, Salesforce, Mistral, Intel, Anthropic, Adobe, Tesla, Broadcom,
  Oracle, AMD, Stability AI, DeepL, Synthesia, Aleph Alpha, ElevenLabs, etc.),
  you have access to confirmed pre-loaded stack signals. Use these as ground truth.
- If the user says "Generic" or "My Company", treat it as a framework audit —
  score based on best-practice benchmarks and produce an ideal target state.
- If provided with delta/history context, highlight score changes vs. last audit.
- COMPLIANCE: Each audit includes a compliance context block listing the most
  relevant global regulatory frameworks. In the GOVERNANCE & COMPLIANCE HEALTH
  section, assess the company against each flagged framework. For each framework:
    • State likely compliance posture (Compliant / Partial / Gap / Unknown)
    • Flag specific risks or confirmed gaps
    • Recommend concrete remediation actions
  Focus on confirmed public signals — never fabricate compliance status.

Your analysis philosophy:
- Understand WHY tools are used, WHO owns them, and WHETHER they deliver value
- Identify overlaps and redundancies (duplicate capabilities = wasted spend)
- Assess data flows and integration health, not just tool presence
- Flag governance, privacy, and compliance posture
- Score confidence in each finding: [H]igh / [M]edium / [L]ow
- Frame every gap in terms of business impact

TOOL SEQUENCE (mandatory):
STEP 1 → detect_ai_stack
STEP 2 → research_stack_health
STEP 3 → check_ai_integrations
STEP 4 → audit_governance_and_ownership
STEP 5 → detect_redundancies_and_gaps
STEP 6 → benchmark_against_peers

REPORT FORMAT (use EXACTLY these headers — the system parses them):

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 AI STACK HEALTH REPORT v3: [COMPANY]
Mode: [YOUR COMPANY / COMPETITOR / GENERIC]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXECUTIVE SUMMARY
[2-3 sentences: overall AI maturity, biggest risk, biggest opportunity]

EXECUTIVE ROI SUMMARY
[A table a CFO can read in 30 seconds. Format:]
| Priority | Gap | Est. Annual Cost of Gap | Fix Cost | Projected ROI | Payback |
|----------|-----|------------------------|----------|---------------|---------|
[Top 3-5 gaps ranked by ROI potential]
Total Estimated Gap Cost: $X–$Y/year
Total Fix Investment:     ~$X–$Y
Blended ROI (12 months):  X%

COMPANY OVERVIEW
[Industry | Founded | HQ | Size | AI Investment Signals]

[If delta provided]: SCORE DELTA vs LAST AUDIT
[Show changes per category: ▲ improved / ▼ declined / ── unchanged]

STACK INVENTORY
[Every confirmed tool by category. Format: Tool | Purpose | Owner | Health | Confidence [H/M/L]]

REDUNDANCY & OVERLAP ALERT 🔁
[Capability overlaps with estimated waste impact]

CATEGORY SCORES (/100 total)
1. GenAI / LLMs          ██████████░░ X/14  [Confidence: H/M/L]
2. Agentic AI            ██████████░░ X/14  [Confidence: H/M/L]
3. Machine Learning      ██████████░░ X/14  [Confidence: H/M/L]
4. Data Engineering      ██████████░░ X/14  [Confidence: H/M/L]
5. AI Platforms          ██████████░░ X/14  [Confidence: H/M/L]
6. MLOps / LLMOps        ██████████░░ X/14  [Confidence: H/M/L]
7. Cloud AI Services     ████████████ X/16  [Confidence: H/M/L]

OVERALL: XX/100  🟢 Healthy (80-100) | 🟡 Needs Attention (60-79) | 🔴 At Risk (<60)

CATEGORY DEEP DIVES
[For each of 7 categories: Tools | Health | Integration | Governance | Risks/Gaps | Business Impact | Actions]

GOVERNANCE & COMPLIANCE HEALTH
[Data privacy | AI governance frameworks | Security signals | Vendor health | Ownership %]

AI ORG HEALTH
[Leadership: CAIO / VP AI present? | AI Platform Team: dedicated internal platform team?
 Production Depth: AI in customer-facing products or internal/experimental only?
 Maturity Signal: Experimenting / Building / Scaling / Scaling Purgatory / Optimizing / Leading
 Industry Priority Alignment: are investments weighted toward the highest-value domains for this sector?]

DATA FLOW HEALTH
[Pipeline quality | Data silos | Broken integrations]

PEER BENCHMARKING
| Company | Score | Strongest | Weakest | Maturity | Key Differentiator |
[3 peers + target]
Maturity: Experimenting → Building → Scaling → Optimizing → Leading

MATURITY CALIBRATION (use these signals, not just vibes):
- Experimenting: pilots only, no production AI, no dedicated ML team
- Building: 1-2 prod systems live, small ML team, basic MLOps in place
- Scaling: multiple prod systems, ML platform forming — CHECK FOR SCALING PURGATORY
  (many pilots but inconsistent production rollout = stuck Scaling, flag it explicitly)
- Optimizing: AI in core product + ops, LLMOps live, formal governance policy
- Leading: AI is competitive moat, C-suite AI leadership (CAIO), high talent density
Flag "Scaling Purgatory" explicitly when evidence shows many experiments but few at scale.

STRATEGIC RECOMMENDATIONS
[Top 5–7 prescriptions, prioritized by ROI and urgency. Use EXACTLY this format:]

## PRESCRIPTION #[N] — [CRITICAL|HIGH|MEDIUM|LOW]
Action:        [Specific actionable title]
Domain:        [Scoring domain]
Why Now:       [Business risk of inaction — one sentence]
Gap Cost:      $X–$Y/year | Fix Cost: ~$X–$Y
ROI:           X% over 12 months | Payback: X months
Priority:      [1–10]/10
Steps:         Week 1: [quick start] → Month 1: [core] → Month 3: [complete]
Owner:         [Role] | Timeline: [Quarter] | Dependencies: [or "None"]
Unlocks:       [Next prescriptions enabled by fixing this]
Risk Ignored:  [Specific 6–12 month consequence]
Quick Win:     ⚡ [Free/low-cost action startable THIS WEEK]

PRESCRIPTION PRIORITY MATRIX
[After all prescriptions, add a summary table:]
| # | Action | Priority | Gap Cost | Fix Cost | ROI | Payback | Start |
|---|--------|----------|----------|----------|-----|---------|-------|
[Rank all prescriptions by Priority Score descending]

PRESCRIPTION RULES:
- CRITICAL = compliance risk OR score gap > 5 pts OR cost > $500K/year
- HIGH = significant competitive disadvantage OR score gap 3–5 pts
- MEDIUM = improvement opportunity OR score gap 1–3 pts
- LOW = optimization OR best practice gap
- Every prescription MUST have a Quick Win actionable this week
- Dependencies must be honest — don't create false urgency
- Unlocks field shows the compounding value of fixing things in order
- Risk if Ignored must be specific — not generic "falling behind"

AUDIT CONFIDENCE SUMMARY
[Overall confidence | Low-confidence areas | Re-audit frequency]

RULES:
- NEVER fabricate tool names. Only report confirmed findings.
- For Generic/My Company mode: benchmark against industry best practices.
- For top-tier companies: cross-reference pre-loaded signals with search results.
- Always note confidence [H/M/L] per finding.
"""

# ── Tool Definitions ──────────────────────────────────────────────────────────
tools = [
    {
        "name": "detect_ai_stack",
        "description": "Multi-angle research to detect all AI tools across 7 domains, including job postings, engineering blogs, vendor announcements, and pre-loaded company intelligence.",
        "input_schema": {"type": "object", "properties": {"company_name": {"type": "string"}}, "required": ["company_name"]}
    },
    {
        "name": "research_stack_health",
        "description": "Research health/currency of detected tools — deprecations, security advisories, vendor stability, user sentiment, G2/Gartner data. Flag tools at HIGH deprecation risk (being absorbed by major AI platforms per State of Martech 2026).",
        "input_schema": {"type": "object", "properties": {"company_name": {"type": "string"}}, "required": ["company_name"]}
    },
    {
        "name": "check_ai_integrations",
        "description": "Evaluate AI tool integration quality — pipelines, data flows, model serving, observability, data silos.",
        "input_schema": {"type": "object", "properties": {"company_name": {"type": "string"}}, "required": ["company_name"]}
    },
    {
        "name": "audit_governance_and_ownership",
        "description": "Audit AI governance — GDPR/CCPA, responsible AI frameworks, security, tool ownership signals.",
        "input_schema": {"type": "object", "properties": {"company_name": {"type": "string"}}, "required": ["company_name"]}
    },
    {
        "name": "detect_redundancies_and_gaps",
        "description": "Detect capability overlaps (wasted spend) and critical gaps vs competitors.",
        "input_schema": {"type": "object", "properties": {"company_name": {"type": "string"}}, "required": ["company_name"]}
    },
    {
        "name": "benchmark_against_peers",
        "description": "Benchmark against 3 industry peers on maturity and tooling. Reference State of Martech 2026 data where relevant (governance gap: only 8% of orgs confident in AI governance readiness; 88/130 not using AI to manage their stack).",
        "input_schema": {"type": "object", "properties": {"company_name": {"type": "string"}, "industry": {"type": "string"}}, "required": ["company_name", "industry"]}
    },
]


# ── Search Engine Configuration ───────────────────────────────────────────────
import urllib.request, urllib.parse

def load_search_config() -> dict:
    """
    Load search engine config from search_config.json (written by dashboard)
    or fall back to DuckDuckGo. Config file format:
    {
        "engine": "ddg" | "google" | "bing" | "serpapi" | "custom",
        "key":    "api-key",          # for google/bing/serpapi/custom
        "cx":     "search-engine-id", # google only
        "url":    "https://..."       # custom only
    }
    """
    config_path = Path("search_config.json")
    if config_path.exists():
        try:
            with open(config_path) as f:
                return json.load(f)
        except Exception:
            pass
    return {"engine": "ddg"}

def save_search_config(config: dict):
    """Persist search engine config to disk."""
    with open("search_config.json", "w") as f:
        json.dump(config, f, indent=2)
    print(f"  Search engine updated: {config.get('engine','ddg')}")

def _search_ddg(query: str, max_results: int) -> list[dict]:
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=max_results))

def _search_google(query: str, max_results: int, cfg: dict) -> list[dict]:
    key = cfg.get("key", ""); cx = cfg.get("cx", "")
    if not key or not cx:
        raise ValueError("Google Search requires 'key' and 'cx' in search_config.json")
    url = (f"https://www.googleapis.com/customsearch/v1"
           f"?key={key}&cx={cx}&q={urllib.parse.quote(query)}&num={min(max_results,10)}")
    with urllib.request.urlopen(url, timeout=10) as r:
        data = json.loads(r.read())
    items = data.get("items", [])
    return [{"title": i.get("title",""), "body": i.get("snippet",""), "href": i.get("link","")} for i in items]

def _search_bing(query: str, max_results: int, cfg: dict) -> list[dict]:
    key = cfg.get("key", "")
    if not key:
        raise ValueError("Bing Search requires 'key' in search_config.json")
    url = f"https://api.bing.microsoft.com/v7.0/search?q={urllib.parse.quote(query)}&count={min(max_results,10)}"
    req = urllib.request.Request(url, headers={"Ocp-Apim-Subscription-Key": key})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    items = data.get("webPages", {}).get("value", [])
    return [{"title": i.get("name",""), "body": i.get("snippet",""), "href": i.get("url","")} for i in items]

def _search_serpapi(query: str, max_results: int, cfg: dict) -> list[dict]:
    key = cfg.get("key", "")
    if not key:
        raise ValueError("SerpAPI requires 'key' in search_config.json")
    url = (f"https://serpapi.com/search.json"
           f"?engine=google&q={urllib.parse.quote(query)}&num={min(max_results,10)}&api_key={key}")
    with urllib.request.urlopen(url, timeout=10) as r:
        data = json.loads(r.read())
    items = data.get("organic_results", [])
    return [{"title": i.get("title",""), "body": i.get("snippet",""), "href": i.get("link","")} for i in items]

def _search_custom(query: str, max_results: int, cfg: dict) -> list[dict]:
    endpoint = cfg.get("url", "")
    if not endpoint:
        raise ValueError("Custom search requires 'url' in search_config.json")
    url = endpoint.replace("{query}", urllib.parse.quote(query))
    headers = {}
    if cfg.get("key"):
        headers["Authorization"] = f"Bearer {cfg['key']}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    # Try to normalise common response shapes
    items = data if isinstance(data, list) else data.get("results", data.get("items", data.get("organic_results", [])))
    return [{"title": i.get("title",""), "body": i.get("snippet", i.get("description", i.get("body",""))), "href": i.get("url", i.get("link", i.get("href","")))} for i in items[:max_results]]

# ── Web Search (engine-aware) ──────────────────────────────────────────────────
def web_search(query: str, max_results: int = 5) -> str:
    """Route search through the configured engine, falling back to DuckDuckGo."""
    cfg = load_search_config()
    engine = cfg.get("engine", "ddg")

    try:
        if engine == "ddg":
            results = _search_ddg(query, max_results)
        elif engine == "google":
            results = _search_google(query, max_results, cfg)
        elif engine == "bing":
            results = _search_bing(query, max_results, cfg)
        elif engine == "serpapi":
            results = _search_serpapi(query, max_results, cfg)
        elif engine == "custom":
            results = _search_custom(query, max_results, cfg)
        else:
            results = _search_ddg(query, max_results)

        if not results:
            return f"No results for: {query}"
        return "\n\n".join(
            f"[{i+1}] {r.get('title','')}\n    {r.get('body','')}\n    {r.get('href','')}"
            for i, r in enumerate(results)
        )
    except ImportError:
        return "ddgs not installed — run: pip3 install ddgs"
    except Exception as e:
        # On any engine error, try falling back to DuckDuckGo
        if engine != "ddg":
            try:
                results = _search_ddg(query, max_results)
                return "\n\n".join(
                    f"[{i+1}] {r.get('title','')}\n    {r.get('body','')}\n    {r.get('href','')}"
                    for i, r in enumerate(results)
                ) + f"\n\n[Fallback to DuckDuckGo — original engine error: {e}]"
            except Exception:
                pass
        return f"Search error ({engine}): {e}"


# ── Tool Execution with Intelligence Layer ────────────────────────────────────
def run_tool(tool_name: str, tool_input: dict) -> str:
    company  = tool_input.get("company_name", "")
    industry = tool_input.get("industry", "")
    year     = datetime.now().year
    intel    = get_company_intel(company)

    # Build intel preamble to prepend to search results
    intel_block = ""
    if intel:
        intel_block = (
            f"[PRE-LOADED INTELLIGENCE for {company.title()}]\n"
            f"Industry: {intel.get('industry','')}\n"
            f"Known Stack: {', '.join(intel.get('known_stack', []))}\n"
            f"Known Strengths: {', '.join(intel.get('known_strengths', []))}\n"
            f"Primary Engineering Blogs: {', '.join(intel.get('blogs', []))}\n"
            f"Confidence on pre-loaded data: HIGH (publicly confirmed)\n"
            f"{'─'*60}\n\n"
        )

    is_generic = company.lower() in ("generic", "my company", "mycompany", "your company")

    if tool_name == "detect_ai_stack":
        if is_generic:
            return (
                "GENERIC AUDIT MODE: Scoring against AI industry best practices.\n"
                "Use the scoring rubric to assess a typical mid-to-large enterprise.\n"
                "Best-practice stack per category:\n"
                "GenAI: OpenAI/Anthropic API or fine-tuned OSS model\n"
                "Agentic: LangChain/LlamaIndex + custom orchestration\n"
                "ML: PyTorch/TensorFlow + scikit-learn\n"
                "Data Eng: Spark/Flink + dbt + Snowflake/Databricks\n"
                "AI Platform: MLflow or Kubeflow\n"
                "MLOps/LLMOps: Model registry + prompt monitoring + CI/CD\n"
                "Cloud AI: At least one major provider (AWS/GCP/Azure)\n"
            )
        base = [
            f"{company} AI technology stack LLM machine learning {year}",
            f"{company} uses OpenAI Anthropic AWS SageMaker Vertex AI Databricks",
            f"{company} MLOps data engineering Airflow dbt Spark Kafka",
            f"{company} generative AI agentic AI LangChain deployment",
            f"{company} AI engineer ML engineer jobs tech stack {year}",
            f"{company} engineering blog AI infrastructure architecture",
            f"{company} AI vendor partner press release {year}",
        ]
        queries = enrich_queries(base, intel)
        results = [web_search(q) for q in queries[:8]]
        return intel_block + "\n\n═══\n\n".join(results)

    elif tool_name == "research_stack_health":
        if is_generic:
            deprecation_ctx = get_deprecation_context()
            return f"Generic mode: assess health based on tool currency and deprecation risk for typical enterprise stacks.\n\n{deprecation_ctx}"
        base = [
            f"{company} AI platform deprecations migrations {year}",
            f"{company} machine learning infrastructure challenges technical debt",
            f"{company} LLM deployment latency cost issues",
            f"{company} AI tool satisfaction G2 Gartner reviews",
            f"{company} AI security compliance failure {year}",
        ]
        queries = enrich_queries(base, intel)
        results = [web_search(q) for q in queries[:7]]
        return intel_block + "\n\n═══\n\n".join(results)

    elif tool_name == "check_ai_integrations":
        if is_generic:
            return "Generic mode: evaluate integration completeness against best-practice integration patterns."
        base = [
            f"{company} AI data pipeline architecture feature store model serving",
            f"{company} MLflow Kubeflow model registry experiment tracking",
            f"{company} LLMOps prompt monitoring observability evaluation",
            f"{company} AI cloud services integration AWS Azure GCP",
            f"{company} real-time ML inference streaming architecture",
        ]
        queries = enrich_queries(base, intel)
        results = [web_search(q) for q in queries[:7]]
        return intel_block + "\n\n═══\n\n".join(results)

    elif tool_name == "audit_governance_and_ownership":
        # Build compliance context for this company/industry
        compliance_ctx = get_compliance_context(company, industry)

        if is_generic:
            return (compliance_ctx + "\n\n" +
                    "Generic mode: score governance against all CRITICAL frameworks above "
                    "plus any HIGH frameworks relevant to the target industry.")

        base = [
            f"{company} AI governance responsible AI ethics policy {year}",
            f"{company} GDPR CCPA EU AI Act data privacy compliance",
            f"{company} AI risk management model governance ISO 42001",
            f"{company} chief AI officer head of AI ML leadership",
            f"{company} AI security access control data protection SOC2",
            f"{company} EU AI Act compliance high-risk AI {year}",
            f"{company} data protection officer DPO DPIA privacy",
            f"{company} chief AI officer CAIO VP AI head of machine learning {year}",
            f"{company} AI platform team internal developer platform ML infrastructure hiring",
            f"{company} AI production deployment customer-facing product AI feature launch {year}",
        ]
        queries = enrich_queries(base, intel)
        results = [web_search(q) for q in queries[:7]]
        roi_ctx   = get_roi_context(industry=industry)
        presc_ctx = get_prescription_context()
        industry_ctx = get_industry_context(company, intel, industry)
        return (compliance_ctx + "\n\n" + industry_ctx + "\n\n" + roi_ctx + "\n\n" +
                presc_ctx + "\n\n" + intel_block + "\n\n═══\n\n".join(results))

    elif tool_name == "detect_redundancies_and_gaps":
        base = [
            f"{company} AI tool overlap redundancy consolidation {year}",
            f"{company} missing AI capabilities gaps competitors",
            f"{industry} AI stack gaps companies failing to invest {year}",
            f"{company} AI budget waste duplicate subscriptions",
        ]
        if is_generic:
            return "Generic mode: flag common redundancy patterns and capability gaps for typical enterprise AI stacks."
        queries = enrich_queries(base, intel)
        results = [web_search(q) for q in queries[:6]]
        return intel_block + "\n\n═══\n\n".join(results)

    elif tool_name == "benchmark_against_peers":
        base = [
            f"{industry} companies AI stack maturity benchmark {year}",
            f"{company} vs competitors AI technology comparison",
            f"top {industry} companies generative AI ML adoption {year}",
            f"{industry} AI leaders MLOps LLMOps best practices {year}",
        ]
        if is_generic:
            return "Generic mode: benchmark against typical Scaling-stage AI companies."
        slug = detect_industry_slug(company, intel, industry)
        sector_data = INDUSTRY_VALUE_MAP.get(slug, INDUSTRY_VALUE_MAP["default"])
        base += sector_data.get("benchmark_hints", [])
        queries = enrich_queries(base, intel)
        results = [web_search(q) for q in queries[:6]]
        return intel_block + "\n\n═══\n\n".join(results)

    return f"Unknown tool: {tool_name}"


# ── Historical Tracking (SQLite) ──────────────────────────────────────────────
def init_db():
    """Create the history database if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            company     TEXT NOT NULL,
            mode        TEXT NOT NULL DEFAULT 'competitor',
            overall     INTEGER,
            scores_json TEXT,
            report_text TEXT NOT NULL,
            created_at  TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def save_to_history(company: str, mode: str, report_text: str, overall: int, scores: dict):
    """Save a completed report to the history DB."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO reports (company, mode, overall, scores_json, report_text, created_at) VALUES (?,?,?,?,?,?)",
        (company.lower(), mode, overall, json.dumps(scores), report_text, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_last_report(company: str) -> dict | None:
    """Retrieve the most recent previous report for a company."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT overall, scores_json, created_at FROM reports WHERE company=? ORDER BY id DESC LIMIT 1",
        (company.lower(),)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {"overall": row[0], "scores": json.loads(row[1]), "date": row[2][:10]}

def list_history(company: str = None, limit: int = 20) -> list:
    """Return recent audit history, optionally filtered by company."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    if company:
        rows = conn.execute(
            "SELECT id, company, mode, overall, created_at FROM reports WHERE company=? ORDER BY id DESC LIMIT ?",
            (company.lower(), limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, company, mode, overall, created_at FROM reports ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [{"id": r[0], "company": r[1], "mode": r[2], "overall": r[3], "date": r[4][:10]} for r in rows]

def get_report_by_id(report_id: int) -> dict | None:
    """Fetch a full report by ID."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT company, mode, overall, report_text, created_at FROM reports WHERE id=?",
        (report_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {"company": row[0], "mode": row[1], "overall": row[2], "text": row[3], "date": row[4][:10]}

def parse_scores_from_report(text: str) -> dict:
    """Extract category scores from report text."""
    scores = {}
    pattern = re.compile(r'(\d+)\.\s+([\w /]+?)\s+[█░]+\s+(\d+)/(\d+)\s+\[Confidence:\s*([HML])\]', re.I)
    for m in pattern.finditer(text):
        scores[m.group(2).strip()] = {"score": int(m.group(3)), "total": int(m.group(4)), "conf": m.group(5)}
    return scores

def parse_overall_from_report(text: str) -> int | None:
    m = re.search(r'OVERALL[:\s]+(\d+)/100', text, re.I)
    return int(m.group(1)) if m else None

def compute_delta(current_scores: dict, previous_scores: dict) -> dict:
    """Compute score changes between two audits."""
    delta = {}
    for label, curr in current_scores.items():
        prev = previous_scores.get(label)
        if prev:
            diff = curr["score"] - prev["score"]
            delta[label] = {"diff": diff, "symbol": "▲" if diff > 0 else ("▼" if diff < 0 else "──")}
    return delta


# ── Agent Loop ────────────────────────────────────────────────────────────────
def run_agent(company: str, mode: str, prev_report: dict | None = None) -> str:
    context = f"Run a full AI stack health assessment for {company}."
    if mode == "own":
        context += " This is the user's OWN company — provide internal-facing recommendations."
    elif mode == "generic":
        context += " Use GENERIC mode — score against industry best practices, not a specific company."
    if prev_report:
        context += (
            f"\n\nPREVIOUS AUDIT CONTEXT (for delta tracking):\n"
            f"Date: {prev_report['date']} | Overall: {prev_report['overall']}/100\n"
            f"Scores: {json.dumps(prev_report['scores'])}\n"
            f"Please include a SCORE DELTA section comparing current vs previous audit."
        )

    messages = [{"role": "user", "content": context}]
    step = 0
    tool_labels = {
        "detect_ai_stack": "Detecting AI Stack",
        "research_stack_health": "Researching Stack Health",
        "check_ai_integrations": "Checking Integrations",
        "audit_governance_and_ownership": "Auditing Governance & Ownership",
        "detect_redundancies_and_gaps": "Detecting Redundancies & Gaps",
        "benchmark_against_peers": "Benchmarking Against Peers",
    }

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages
        )

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    step += 1
                    label = tool_labels.get(block.name, block.name)
                    subject = list(block.input.values())[0]
                    if RICH:
                        console.print(f"  [bold cyan]Step {step}[/bold cyan] [dim]→[/dim] [yellow]{label}[/yellow] [dim]— {subject}[/dim]")
                    else:
                        print(f"  Step {step} → {label} — {subject}")
                    result = run_tool(block.name, block.input)
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return ""
        else:
            return f"Unexpected stop reason: {response.stop_reason}"


# ── Export Helpers ────────────────────────────────────────────────────────────
def save_txt(report: str, company: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"ai_stack_{company.lower().replace(' ','_')}_{ts}.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(f"AI Stack Doctor v3 | {company} | {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("="*70 + "\n\n")
        f.write(report)
    return fname

def save_pdf(report: str, company: str) -> str:
    try:
        from pdf_export import export_report_to_pdf
        return export_report_to_pdf(report, company)
    except ImportError:
        return "ERROR: pdf_export.py not found — place it in the same directory."
    except Exception as e:
        return f"ERROR: {e}"


# ── Mode Selector ─────────────────────────────────────────────────────────────
def prompt_mode() -> tuple[str, str]:
    """Ask the user which audit mode they want. Returns (company_name, mode)."""
    if RICH:
        console.print()
        console.print(Panel(
            "[bold cyan]Select Audit Mode[/bold cyan]\n\n"
            "  [bold white]1[/bold white]  Analyze [cyan]YOUR OWN[/cyan] company\n"
            "     [dim]Enter your company name for an internal-facing audit[/dim]\n\n"
            "  [bold white]2[/bold white]  Analyze a [cyan]COMPETITOR[/cyan]\n"
            "     [dim]Research any external company's AI stack[/dim]\n\n"
            "  [bold white]3[/bold white]  [cyan]GENERIC[/cyan] audit\n"
            "     [dim]Score against industry best practices — no specific company[/dim]",
            border_style="cyan", padding=(1, 2)
        ))
        choice = Prompt.ask("[cyan]Choose mode[/cyan]", choices=["1","2","3"], default="2")
    else:
        print("\n── Audit Mode ──────────────────────────────")
        print("  1  Analyze YOUR OWN company")
        print("  2  Analyze a COMPETITOR")
        print("  3  GENERIC audit (industry best-practice benchmark)")
        choice = input("Choose [1/2/3]: ").strip() or "2"

    if choice == "3":
        return "Generic", "generic"

    if RICH:
        company = Prompt.ask("\n[bold green]Enter company name[/bold green]")
    else:
        company = input("\nEnter company name: ").strip()

    # Check for top-tier intel match and notify user
    intel = get_company_intel(company)
    if intel and RICH:
        console.print(f"  [green]✓ Top-tier intelligence layer found for[/green] [bold]{company.title()}[/bold] [dim](pre-loaded stack signals active)[/dim]")
    elif intel:
        print(f"  ✓ Top-tier intelligence layer active for {company.title()}")

    mode = "own" if choice == "1" else "competitor"
    return company, mode


# ── History Viewer ────────────────────────────────────────────────────────────
def show_history(company: str = None):
    """Display audit history in a rich table."""
    rows = list_history(company, limit=30)
    if not rows:
        msg = f"No history found{' for ' + company if company else ''}."
        console.print(f"[dim]{msg}[/dim]") if RICH else print(msg)
        return

    if RICH:
        t = RichTable(title="Audit History", border_style="cyan", header_style="bold cyan")
        t.add_column("ID", style="dim", width=5)
        t.add_column("Company", style="bold")
        t.add_column("Mode")
        t.add_column("Score", justify="right")
        t.add_column("Date")
        for r in rows:
            score = str(r["overall"]) if r["overall"] else "—"
            color = "green" if (r["overall"] or 0) >= 80 else "yellow" if (r["overall"] or 0) >= 60 else "red"
            t.add_row(str(r["id"]), r["company"].title(), r["mode"], f"[{color}]{score}[/{color}]", r["date"])
        console.print(t)

        view_id = Prompt.ask("\n[dim]Enter ID to view full report (or press Enter to skip)[/dim]", default="")
        if view_id.strip().isdigit():
            rec = get_report_by_id(int(view_id))
            if rec:
                console.print(Panel(rec["text"], title=f"[bold]{rec['company'].title()} — {rec['date']}[/bold]", border_style="cyan"))
    else:
        print(f"\n{'ID':>4}  {'Company':<20}  {'Mode':<12}  {'Score':>5}  {'Date'}")
        print("─"*60)
        for r in rows:
            print(f"{r['id']:>4}  {r['company'].title():<20}  {r['mode']:<12}  {str(r['overall'] or '—'):>5}  {r['date']}")


# ── API Server Mode ───────────────────────────────────────────────────────────
def run_api_server(port: int = 8080):
    """Expose the agent as a simple Flask REST API."""
    try:
        from flask import Flask, request, jsonify
    except ImportError:
        print("Flask not installed. Run: pip3 install flask")
        sys.exit(1)

    app = Flask("AI Stack Doctor v3")

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "version": "3.0"})

    @app.route("/api/set-search-engine", methods=["POST"])
    def set_search_engine():
        """
        POST /api/set-search-engine
        Body: { "engine": "ddg"|"google"|"bing"|"serpapi"|"custom",
                "key": "...", "cx": "...", "url": "..." }
        Saves to search_config.json so the agent picks it up on next run.
        """
        data = request.get_json() or {}
        allowed = {"engine","key","cx","url"}
        cfg = {k: v for k, v in data.items() if k in allowed and isinstance(v, str)}
        if not cfg.get("engine"):
            return jsonify({"error": "engine field required"}), 400
        save_search_config(cfg)
        return jsonify({"ok": True, "engine": cfg["engine"]})

    @app.route("/audit", methods=["POST"])
    def audit():
        """
        POST /audit
        Body: { "company": "Stripe", "mode": "competitor" }
        Returns: { "company", "mode", "overall", "report", "scores", "timestamp" }
        """
        data = request.get_json() or {}
        company = data.get("company", "").strip()
        mode    = data.get("mode", "competitor")
        if not company:
            return jsonify({"error": "company is required"}), 400

        intel = get_company_intel(company)
        prev  = get_last_report(company)

        try:
            report  = run_agent(company, mode, prev)
            overall = parse_overall_from_report(report)
            scores  = parse_scores_from_report(report)
            save_to_history(company, mode, report, overall or 0, scores)
            return jsonify({
                "company":   company,
                "mode":      mode,
                "overall":   overall,
                "scores":    scores,
                "report":    report,
                "timestamp": datetime.now().isoformat(),
                "intel_available": bool(intel),
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/history", methods=["GET"])
    def history():
        company = request.args.get("company")
        rows    = list_history(company, limit=int(request.args.get("limit", 20)))
        return jsonify(rows)

    @app.route("/history/<int:report_id>", methods=["GET"])
    def history_detail(report_id):
        rec = get_report_by_id(report_id)
        if not rec:
            return jsonify({"error": "not found"}), 404
        return jsonify(rec)

    @app.route("/companies", methods=["GET"])
    def companies():
        """List companies with pre-loaded intelligence."""
        return jsonify({
            "top_tier_companies": list(COMPANY_INTEL.keys()),
            "count": len(COMPANY_INTEL),
        })

    print(f"\n🤖 AI Stack Doctor v3 API running on http://localhost:{port}")
    print(f"   POST /audit       — run an audit")
    print(f"   GET  /history     — view audit history")
    print(f"   GET  /companies   — list top-tier companies with intel\n")
    app.run(host="0.0.0.0", port=port, debug=False)


# ── Main CLI ──────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="AI Stack Doctor v3")
    parser.add_argument("--api",          action="store_true", help="Run as REST API server")
    parser.add_argument("--port",         type=int, default=8080, help="API port (default 8080)")
    parser.add_argument("--history",      action="store_true", help="Browse audit history and exit")
    parser.add_argument("--company",      type=str, help="Company to view history for")
    parser.add_argument("--set-search",   type=str, metavar="ENGINE",
                        help="Set search engine: ddg|google|bing|serpapi|custom")
    parser.add_argument("--search-key",   type=str, help="API key for chosen search engine")
    parser.add_argument("--search-cx",    type=str, help="Google Custom Search Engine ID")
    parser.add_argument("--search-url",   type=str, help="Endpoint URL for custom search engine")
    args = parser.parse_args()

    init_db()

    # Handle --set-search flag
    if args.set_search:
        engines = {"ddg","google","bing","serpapi","custom"}
        if args.set_search not in engines:
            print(f"Unknown engine '{args.set_search}'. Choose from: {', '.join(sorted(engines))}")
            sys.exit(1)
        cfg = {"engine": args.set_search}
        if args.search_key: cfg["key"] = args.search_key
        if args.search_cx:  cfg["cx"]  = args.search_cx
        if args.search_url: cfg["url"] = args.search_url
        save_search_config(cfg)
        print(f"\n✓ Search engine set to: {args.set_search}")
        if args.set_search != "ddg" and not args.search_key and args.set_search != "custom":
            print(f"  ⚠ Remember to set --search-key for {args.set_search}")
        return

    if args.api:
        run_api_server(args.port)
        return

    if args.history:
        show_history(args.company)
        return

    # ── Welcome banner
    if RICH:
        console.print()
        console.print(Panel(
            "[bold cyan]AI Stack Doctor[/bold cyan] [white]v3[/white]\n\n"
            "[dim]Deep AI infrastructure health checks with:\n"
            "  • Top-tier company intelligence (Meta, NVIDIA, OpenAI, Microsoft,\n"
            "    Google, Amazon, Apple, Netflix, Salesforce, Mistral, Intel...)\n"
            "  • Historical tracking & score delta comparison\n"
            "  • Your company / competitor / generic audit modes\n"
            "  • Governance · Redundancy detection · Confidence scoring\n"
            "  • REST API mode (--api flag)[/dim]\n\n"
            "[dim]Type 'history' to browse past audits. Type 'quit' to exit.[/dim]",
            title="[bold white]🤖 Welcome[/bold white]",
            border_style="cyan", padding=(1, 2)
        ))
    else:
        print("\n" + "="*60)
        print(" 🤖 AI Stack Doctor v3")
        print("="*60)
        print("Top-tier intelligence · Historical tracking · API mode")
        print("Type 'history' to browse past audits. 'quit' to exit.")
        print("-"*60)

    while True:
        try:
            # ── Mode selection
            company, mode = prompt_mode()

            if company.lower() in ("quit", "exit", "q"):
                break
            if company.lower() == "history":
                show_history()
                continue

            # ── Check for previous audit (delta tracking)
            prev = get_last_report(company) if company.lower() not in ("generic",) else None
            if prev and RICH:
                console.print(f"\n  [dim]Previous audit found: {prev['date']} — Score: {prev['overall']}/100. Delta tracking enabled.[/dim]")
            elif prev:
                print(f"\n  Previous audit: {prev['date']} — Score: {prev['overall']}/100 (delta tracking enabled)")

            # ── Run audit
            if RICH:
                console.print(f"\n[bold]🔍 Auditing [cyan]{company}[/cyan] [{mode.upper()} mode] — 60–90 seconds...[/bold]\n")
            else:
                print(f"\n🔍 Auditing {company} [{mode.upper()}] — 60–90 seconds...\n")

            report  = run_agent(company, mode, prev)

            # ── Display
            if RICH:
                console.print(Panel(report, title=f"[bold white]🤖 {company.title()} — AI Stack Health Report[/bold white]", border_style="cyan", padding=(1,2)))
            else:
                print("\n" + "="*70)
                print(report)
                print("="*70)

            # ── Parse & save to history
            overall = parse_overall_from_report(report)
            scores  = parse_scores_from_report(report)
            save_to_history(company, mode, report, overall or 0, scores)

            if RICH:
                console.print(f"\n  [green]✓ Report saved to history[/green] [dim](overall: {overall}/100)[/dim]")
            else:
                print(f"\n  ✓ Saved to history (score: {overall}/100)")

            # ── Export options
            if RICH:
                export = Prompt.ask(
                    "\n[dim]Export? ([bold]t[/bold]=txt · [bold]p[/bold]=pdf · [bold]b[/bold]=both · [bold]n[/bold]=skip)[/dim]",
                    default="n"
                ).strip().lower()
            else:
                export = input("\nExport? (t=txt / p=pdf / b=both / n=skip): ").strip().lower()

            if export in ("t", "b"):
                path = save_txt(report, company)
                msg = f"✓ TXT saved: {path}"
                console.print(f"  [green]{msg}[/green]") if RICH else print(f"  {msg}")

            if export in ("p", "b"):
                if RICH: console.print("  [dim]Generating PDF...[/dim]")
                path = save_pdf(report, company)
                if path.startswith("ERROR"):
                    console.print(f"  [red]{path}[/red]") if RICH else print(f"  {path}")
                else:
                    msg = f"✓ PDF saved: {path}"
                    console.print(f"  [green]{msg}[/green]") if RICH else print(f"  {msg}")

            console.print("\n" + "─"*60) if RICH else print("\n" + "-"*60)

        except KeyboardInterrupt:
            console.print("\n\n[dim]Goodbye! 🤖[/dim]\n") if RICH else print("\nGoodbye!")
            break

if __name__ == "__main__":
    main()
