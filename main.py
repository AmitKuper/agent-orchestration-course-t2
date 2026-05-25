"""CLI entry point for the AI Debate Platform.

Parses arguments then delegates all business logic to DebateSDK.
External consumers should use DebateSDK directly; this module is the
thin CLI shim only.
"""

import sys

from dotenv import load_dotenv

from src.config import build_cli_parser, load_config
from src.exceptions import InvalidTopicError
from src.sdk.debate_sdk import DebateSDK

load_dotenv()


def main() -> None:
    """Parse CLI arguments and delegate debate execution to DebateSDK."""
    parser = build_cli_parser()
    args = parser.parse_args()

    try:
        config = load_config(args)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    sdk = DebateSDK()
    try:
        if config.resume:
            result = sdk.resume(config)
        else:
            result = sdk.run(config)
    except InvalidTopicError as e:
        print(f"Invalid topic: {e}", file=sys.stderr)
        sys.exit(1)

    if result.errors:
        for err in result.errors:
            print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
