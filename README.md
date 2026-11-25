# Suricata-Check MCP Server

<!-- mcp-name: io.github.koen1999/suricata-check-mcp -->

This project provides a [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that exposes `suricata-check` rule analysis to AI agents. It runs `suricata-check` on demand and returns structured findings that AI agents can use to validate and improve Suricata rules.

## Key Features

* **Structured Rule Analysis:** Runs `suricata-check` checkers against provided rules and returns machine-readable findings, with a single error convention (tools raise actionable `ValueError`s on invalid input).
* **MCP Server Implementation:** Built on [FastMCP](https://gofastmcp.com), exposing tools to any MCP-compatible client or AI agent.
* **File Processing:** Processes entire Suricata rules files and returns a per-file report with per-rule issues and aggregated statistics.
* **Checker Discovery:** The `list_checkers` tool enumerates all available checkers and their issue codes for use in `include`/`exclude` selection.
* **Built-in Guidance:** The server provides instructions to MCP clients on how to use the tools and interpret the issue codes, so agents can validate and fix rules without additional prompting.
* **Configurable Checkers:** Every tool accepts `include`/`exclude` regex lists to select which checker types run.

## Getting Started

Follow these steps to get the project running locally.

### Prerequisites

* Python 3.10+
* `suricata-check` must be importable in your environment (installed automatically as a dependency).

### Installation

1. **Create Virtual Environment:**

    ```bash
    python -m venv .venv
    ```

2. **Activate Environment:**
    * *On Unix/macOS:* `source .venv/bin/activate`
    * *On Windows (PowerShell):* `.venv\Scripts\Activate.ps1`
3. **Install Dependencies:** Compile and install the pinned requirements (the same workflow used by CI):

    ```bash
    python -m pip install --upgrade pip pip-tools
    pip-compile --extra test -o requirements.txt pyproject.toml
    pip install -r requirements.txt
    ```

    Alternatively, install the package in editable mode (with the optional test extras):

    ```bash
    pip install -e ".[test]"
    ```

## Usage Guide

### Running the MCP Server

Start the server with the console script:

```bash
suricata-check-mcp
```

or directly from Python:

```bash
python -m suricata_check_mcp
```

By default the server runs on the stdio transport. HTTP-based transports can be selected with
the `--transport` flag (choices: `stdio`, `http`, `sse`, `streamable-http`), optionally together
with `--host` and `--port`:

```bash
suricata-check-mcp --transport http --host 127.0.0.1 --port 8000
```

All logging is written to `stderr`, so stdout stays reserved for MCP protocol messages on the
stdio transport.

Connect any MCP client to the server. For example, an MCP client configuration using the stdio transport:

```json
{
  "mcpServers": {
    "suricata-check": {
      "command": "suricata-check-mcp"
    }
  }
}
```

### Tools

* **`analyze_rule(rule, include, exclude)`:** Analyzes a Suricata rule (or set of rules) and returns a structured dict of issues found by `suricata-check`. When the input is empty or cannot be parsed as a Suricata rule, a `ValueError` with an actionable message is raised instead of returning an error string.
* **`process_rules_file(rules, evaluate_disabled, include, exclude)`:** Processes a Suricata rules file and returns a report containing structured per-rule entries, a `summary`, and per-checker findings in `issues_by_group` and `issues_by_type`.
* **`list_checkers()`:** Lists all checkers discovered by `suricata-check` together with their issue codes, whether they are enabled by default, and a short description. Use this tool to discover valid values for the `include`/`exclude` regex arguments instead of guessing checker codes.

All tools validate the `include`/`exclude` regexes and raise a `ValueError` naming the offending pattern when one is invalid.

### Example output

`process_rules_file` returns one structured entry per rule, containing the original rule text, the line range the rule was parsed from (when known), and the issues found for the rule:

```json
{
  "rules": [
    {
      "rule": "alert http $HOME_NET any -> $EXTERNAL_NET any (msg:\"Test HTTP rule\"; content:\"GET\"; sid:12345; rev:1;)",
      "lines": {"begin": 1, "end": 1},
      "issues": [
        {"code": "S101", "message": "Whitespace issue...", "checker": "WhitespaceChecker"}
      ]
    }
  ],
  "summary": {"overall_summary": {}, "issues_by_group": {}, "issues_by_type": {}},
  "issues_by_group": {},
  "issues_by_type": {}
}
```

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for how to set up the development environment, run the tests and linters, and submit changes.

## License

EUPL-1.2 — see [LICENSE](LICENSE) for details.
