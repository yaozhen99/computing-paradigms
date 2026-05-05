# StateKanban

**AI-Driven State-Machine Kanban Engine** -- an LLM-orchestrated software factory that transforms a PRD into working code through an automated kanban pipeline.

---

## Overview

StateKanban models the software development lifecycle as a **deterministic finite state machine** driving a **kanban board**. AI agents (Coder, Reviewer, Tester, Integrator) push work items through states (`backlog -> in_progress -> review -> test -> done`) while a central message bus coordinates all events. Every state transition is validated, logged, and reproducible.

Key capabilities:

- **State-machine kanban** -- work items advance only through defined transitions; illegal moves are rejected.
- **LLM role agents** -- each agent (Coder, Reviewer, Tester, Integrator, Architect) receives only the viewport it needs and returns a structured response.
- **Pluggable adapters** -- swap between Anthropic, CLI (human-in-the-loop), or Mock backends without changing core logic.
- **Valve rate limiter** -- token-bucket throttling prevents API overruns.
- **Snapshot & replay** -- capture full board state at any point; restore or replay later.
- **Built-in tools** -- `write_file`, `read_file`, `run_shell`, `call_llm`, `search_code` are available to every agent.

---

## Installation

### Prerequisites

- Python 3.11+
- pip or uv package manager
- An Anthropic API key (if using the Anthropic adapter)

### Install from source

```bash
# Clone the repository
git clone <repo-url> statekanban
cd statekanban/03_source/backend

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install the package
pip install -e ".[dev]"
```

### Configuration

Set the required environment variables:

```bash
# Required for Anthropic adapter
export ANTHROPIC_API_KEY="sk-ant-..."

# Optional -- defaults shown
export STATEKANBAN_LLM_MODEL="claude-sonnet-4-20250514"
export STATEKANBAN_MAX_TOKENS="4096"
export STATEKANBAN_VALVE_RATE="10"          # tokens per second (rate limiter)
export STATEKANBAN_VALVE_CAPACITY="50"      # bucket capacity
export STATEKANBAN_LOG_LEVEL="INFO"
```

Alternatively, create a `.env` file in the project root.

---

## Quick Start

### 1. Launch with the CLI adapter (no API key needed)

The CLI adapter lets a human play the role of each agent from the terminal -- perfect for exploring the system.

```bash
python -m statekanban --adapter cli --project ./my-project
```

This starts an interactive session:

```
StateKanban v0.1.0 | adapter=cli | project=./my-project
=========================================================
Board: 0 backlog | 0 in_progress | 0 review | 0 test | 0 done

> add "Implement login endpoint" --priority high
Item #1 created [backlog]

> move 1 in_progress
Item #1: backlog -> in_progress  (assigned: coder)

> status
  #1 [in_progress] Implement login endpoint  (coder)
```

### 2. Launch with the Anthropic adapter (fully automated)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python -m statekanban --adapter anthropic --project ./my-project --prd prd_final.md
```

The engine will automatically create work items from the PRD and drive them through the pipeline.

### 3. Programmatic usage

```python
from statekanban import KanbanBoard, KanbanItem
from statekanban.adapters.mock_adapter import MockAdapter
from statekanban.core.process import Process

# Create a board
board = KanbanBoard()

# Add a work item
item = KanbanItem(title="Write unit tests", priority="high")
board.add(item)

# Set up an agent with the mock adapter
adapter = MockAdapter(responses={"coder": "def test_example(): pass"})
process = Process(board=board, adapter=adapter, role="coder")

# Run one step
result = process.step()
print(result)  # StepResult(item_id=1, action="code", output="def test_example(): pass")

# Move item forward
board.move(item.id, "review")
```

---

## CLI Reference

```
usage: python -m statekanban [-h] --adapter {anthropic,cli,mock}
                              --project PROJECT_DIR
                              [--prd PRD_FILE]
                              [--model MODEL]
                              [--max-tokens TOKENS]
                              [--log-level {DEBUG,INFO,WARNING,ERROR}]

options:
  -h, --help            Show help message and exit
  --adapter             LLM adapter to use (anthropic | cli | mock)
  --project             Path to the project workspace directory
  --prd                 Path to PRD file for initial backlog seeding
  --model               LLM model name (default: claude-sonnet-4-20250514)
  --max-tokens          Max tokens per LLM call (default: 4096)
  --log-level           Logging verbosity (default: INFO)
```

### Interactive commands (CLI adapter)

| Command | Description |
|---------|-------------|
| `add TITLE [--priority P]` | Create a new work item in backlog |
| `move ITEM_ID STATE` | Transition an item to a new state |
| `status` | Show current board overview |
| `detail ITEM_ID` | Show full item details and history |
| `step` | Run one agent processing step |
| `run` | Run the full pipeline to completion |
| `snapshot` | Save current board state to disk |
| `restore SNAPSHOT_ID` | Restore board from a saved snapshot |
| `quit` | Exit the session |

---

## Project Structure

```
03_source/backend/statekanban/
  __init__.py          # Package exports
  config.py            # Settings (pydantic-settings)
  snapshot.py          # Snapshot save/restore logic
  core/
    errors.py          # Custom exceptions
    kanban.py          # KanbanBoard & KanbanItem
    viewport.py        # Role-based view construction
    message_bus.py     # Async event bus
    process.py         # Agent orchestration loop
    valve.py           # Token-bucket rate limiter
    registry.py        # Role & tool registry
  adapters/
    base.py            # Abstract LLMAdapter
    anthropic_adapter.py
    cli_adapter.py
    mock_adapter.py
  roles/
    base.py            # Abstract Role
    coder.py
    reviewer.py
    tester.py
    integrator.py
    architect.py
  tools/
    write_file.py
    read_file.py
    run_shell.py
    call_llm.py
    search_code.py
  cli/
    main.py            # CLI entry point
```

---

## License

See the project root for license information.
