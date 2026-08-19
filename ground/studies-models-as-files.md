# 2025-2026 Studies on Models-as-Files vs Models-as-Hosts

## When Is the Same Model Not the Same Service? A Measurement Study of Hosted Open-Weight LLM APIs (2026)
**URL**: https://arxiv.org/abs/2605.02821
**Summary**: Open-weight large language models (LLMs) are usually named as model artifacts, but production users often consume them as hosted API services. This paper argues that the operational unit is a service object: a provider-specific, time-varying endpoint defined by model variant, protocol behavior, context capacity, listed price, latency and throughput distribution, reliability, and task feasibility. Using sampled request logs, provider metadata, compatibility probes, pricing snapshots, and continuous latency measurements collected by AI Ping during Q4 2025, they study how this service layer changes the meaning of "the same model." The results support a measurement view of hosted open-weight LLMs as heterogeneous services, not static catalog entries.

## Models Are Codes: Towards Measuring Malicious Code Poisoning Attacks on Pre-trained Model Hubs (2026)
**URL**: https://doi.org/10.1145/3691620.3695271
**Summary**: Analyzes pre-trained model hubs emphasizing that models are not just weights, but code (models-as-files). The study looks into 705,991 mirrored model repositories and uncovers security risks tied to serialization methods (e.g., PyTorch using Pickle for serialization) and dataset loading scripts. Over 55% of models use Pickle-based serialization which introduces a significant vulnerability when models are treated as file artifacts without secure execution boundaries.

## Inference Economics of Enterprise Coding Agents: A Case Study of Cloud vs. On-Premise LLMs (2026)
**URL**: https://arxiv.org/pdf/2607.13080
**Summary**: This study evaluates the trade-off between using API-based frontier models (hosted services/cloud) and on-premise quantized open-weights models (models-as-files/local). Analyzing LLM telemetry and Git history over contiguous 28-day periods on a production monorepo, they found prompt caching cut API cost significantly, falling below the amortized unit cost of a shared on-premise slice. While the local configuration experienced higher defect-repair burdens, on-premise deployment still saved 40.1% of true Total Cost of Ownership (TCO) under shared GPU allocation.

## It's Not the AI Model That You Paid for (2026)
**URL**: https://ai-trends.today/you-didnt-get-the-ai-model-you-paid-for/
**Summary**: Highlights the divergence between buying a model and buying a service. Argues that inference APIs are services governed by common-law contract and documentation. The routing layer, as seen with Cursor Router or OpenRouter, treats the model name merely as an identifier but dispatches based on cost, complexity, and other constraints. This reinforces the shift from viewing models as static artifacts (files) to viewing them as dynamic service experiences.