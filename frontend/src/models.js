export const FREE_MODELS = [
  {
    id: 'openrouter/free',
    name: 'Free Router',
    description: 'Zero-cost OpenRouter routing across currently available free models.',
  },
  {
    id: 'openrouter/stepfun/step-3.5-flash:free',
    name: 'Step 3.5 Flash',
    description: 'Fast long-context free model that works well for document QA and summaries.',
  },
  {
    id: 'openrouter/qwen/qwen3-next-80b-a3b-instruct:free',
    name: 'Qwen3 Next 80B',
    description: 'Strong retrieval-friendly instruction following with stable long-context answers.',
  },
  {
    id: 'openrouter/arcee-ai/trinity-large-preview:free',
    name: 'Trinity Large',
    description: 'Large-context free option for synthesis across multiple retrieved chunks.',
  },
  {
    id: 'openrouter/nvidia/nemotron-3-super-120b-a12b:free',
    name: 'Nemotron 3 Super',
    description: 'High-capacity free model for harder multi-step document reasoning.',
  },
  {
    id: 'openrouter/meta-llama/llama-3.3-70b-instruct:free',
    name: 'Llama 3.3 70B',
    description: 'Stronger reasoning for policy analysis and long-form synthesis.',
  },
  {
    id: 'openrouter/mistralai/mistral-small-3.1-24b-instruct:free',
    name: 'Mistral Small 3.1',
    description: 'Lightweight option for concise document answers.',
  },
];

export const EMBEDDING_MODELS = [
  {
    id: 'google/models/gemini-embedding-001',
    name: 'Gemini Embedding',
    description: 'Google embedding model. Good quality, but limited by Gemini API quota.',
  },
  {
    id: 'openrouter/qwen/qwen3-embedding-0.6b',
    name: 'Qwen3 Embedding 0.6B',
    description: 'Lowest-cost OpenRouter embedding option and a practical replacement for Gemini free-tier limits.',
  },
  {
    id: 'openrouter/openai/text-embedding-3-small',
    name: 'OpenAI Embedding 3 Small',
    description: 'OpenRouter-hosted embedding model with lower cost than Gemini-paid usage.',
  },
  {
    id: 'openrouter/openai/text-embedding-3-large',
    name: 'OpenAI Embedding 3 Large',
    description: 'Higher-quality OpenRouter embedding model for stronger semantic retrieval.',
  },
];
