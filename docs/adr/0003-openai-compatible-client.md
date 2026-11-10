# 3. One OpenAI-compatible client for all open-model providers
Decision: `agent/llm.py` talks to any OpenAI-compatible endpoint (Groq, OpenRouter, Together, Ollama, vLLM).
Why: the open profile runs locally or hosted with the same code; models are chosen per node in config.
