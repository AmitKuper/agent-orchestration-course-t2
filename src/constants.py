"""All magic values and defaults for the AI Debate Platform."""

# Debate defaults
DEFAULT_TURNS = 20
DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_NAME_A = "Agent A"
DEFAULT_NAME_B = "Agent B"
DEFAULT_OUTDIR = "outputs"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_BACKEND = "api"
DEFAULT_TEMPERATURE: float | None = None  # None = model default

# Token limits per agent type
MAX_TOKENS_DEBATE = 2048
MAX_TOKENS_JUDGE = 4096

# Validation defaults
MIN_RESPONSE_LEN = 50
MAX_RETRIES = 3
NOVELTY_THRESHOLD = 0.75  # SequenceMatcher ratio above which a response is "too similar"

# Timeouts in seconds
DEBATER_TIMEOUT = 300
JUDGE_TIMEOUT = 600
DEBATE_TIMEOUT = 7200

# Output file names
FILE_CONFIG = "config.json"
FILE_CONVERSATION = "conversation.jsonl"
FILE_LOG = "debate.log"
FILE_RESULT_PREFIX = "result"

# Docs paths
COST_MD_PATH = "docs/cost.md"

# Words that trigger the disrespectful language check
DISRESPECTFUL_PATTERNS = [
    "fuck",
    "shit",
    "asshole",
    "bitch",
    "bastard",
    "cunt",
    "prick",
]

# Strings that indicate an API error response
API_ERROR_MARKERS = [
    "error:",
    "exception:",
    "traceback",
    "rate_limit_error",
    "overloaded_error",
    "api_error",
]
