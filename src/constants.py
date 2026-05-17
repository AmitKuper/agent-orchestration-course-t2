"""All magic values and defaults for the AI Debate Platform."""

# Debate defaults
DEFAULT_TURNS = 20
DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_NAME_A = "Agent A"
DEFAULT_NAME_B = "Agent B"
DEFAULT_OUTDIR = "outputs"
DEFAULT_LOG_LEVEL = "INFO"

# Validation defaults
MIN_RESPONSE_LEN = 50
MAX_RETRIES = 3

# Timeouts in seconds
DEBATER_TIMEOUT = 120
JUDGE_TIMEOUT = 180
DEBATE_TIMEOUT = 3600

# Output file names
FILE_CONFIG = "config.json"
FILE_CONVERSATION = "conversation.jsonl"
FILE_LOG = "debate.log"
FILE_RESULT_PREFIX = "result"

# Words that trigger the disrespectful language check
DISRESPECTFUL_PATTERNS = [
    "fuck", "shit", "asshole", "bitch", "bastard", "cunt", "prick",
]

# Strings that indicate an API error response
API_ERROR_MARKERS = [
    "error:", "exception:", "traceback", "rate_limit_error",
    "overloaded_error", "api_error",
]
