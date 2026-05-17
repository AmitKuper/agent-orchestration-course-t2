"""CLI entry point for the AI Debate Platform."""

import sys

from dotenv import load_dotenv

from src.config import build_cli_parser, load_config

load_dotenv()


def main() -> None:
    """Parse CLI arguments, build config, and launch the orchestrator."""
    parser = build_cli_parser()
    args = parser.parse_args()

    try:
        config = load_config(args)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    # Phase 4: replace stub with Orchestrator(config).run()
    print(f"Config loaded: topic='{config.topic}', turns={config.turns}")


if __name__ == "__main__":
    main()
