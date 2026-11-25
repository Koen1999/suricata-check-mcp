"""Suricata MCP package.

This package encapsulates the core logic for the Suricata-Check Model Context Provider (MCP).
"""

from suricata_check_mcp._suricata_check_mcp import (
    analyze_rule,
    list_checkers,
    mcp,
    process_rules_file,
)
from suricata_check_mcp._version import (
    __version__,
)

__all__ = [
    "__version__",
    "analyze_rule",
    "list_checkers",
    "mcp",
    "process_rules_file",
]
