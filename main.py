"""CLI entry point for the AI Debate Platform."""

import sys
from pathlib import Path

from dotenv import load_dotenv

from orchestrator import DebateOrchestrator, InvalidTopicError
from src.config import build_cli_parser, load_config
from src.constants import FILE_CONVERSATION
from src.cost import CostTracker
from src.output import OutputManager
from src.state import ConversationState

load_dotenv()


def main() -> None:
    """Parse CLI arguments, build config, and run or resume the debate."""
    parser = build_cli_parser()
    args = parser.parse_args()

    try:
        config = load_config(args)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    if config.resume:
        folder = Path(config.outdir)
        output_manager = OutputManager(folder)
        state = ConversationState.load_from_file(folder / FILE_CONVERSATION)
    else:
        output_manager = OutputManager.create_run_folder(config.outdir, config.topic)
        state = ConversationState(output_manager.conversation_path)

    cost_tracker = CostTracker(output_manager.folder.name)
    orchestrator = DebateOrchestrator(config, output_manager, state, cost_tracker)

    try:
        if config.resume:
            orchestrator.resume_debate()
        else:
            orchestrator.run_debate()
    except InvalidTopicError as e:
        print(f"Invalid topic: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
