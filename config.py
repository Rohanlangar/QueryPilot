# config.py

# Use the coder-specialized variant for SQL generation specifically — it materially
# outperforms base Qwen2.5 at SQL synthesis at the same 7B size.
SCHEMA_AGENT_MODEL = "qwen2.5:7b"
# Use qwen2.5:7b (already pulled locally); can be upgraded to qwen2.5-coder:7b
SQL_GEN_MODEL = "qwen2.5:7b"
OPTIMIZATION_MODEL = "qwen2.5:7b"
EXPLANATION_MODEL = "qwen2.5:7b"

MAX_SQL_GEN_RETRIES = 3
MAX_ROWS_TO_LLM = 50          # cap rows shown to Explanation Agent
DEFAULT_ROW_LIMIT = 1000      # enforced LIMIT if user doesn't ask for all rows

OLLAMA_BASE_URL = "http://localhost:11434"

# Embedding model — uses nomic-embed-text served via Ollama (already installed locally)
EMBEDDING_MODEL = "nomic-embed-text:latest"
