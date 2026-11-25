"""MCP provider implementation exposing suricata-check results using FastMCP."""

import functools
import logging
import re
from collections.abc import Sequence
from typing import Any

import pydantic
import suricata_check
from fastmcp import FastMCP
from suricata_check.checkers.interface import CheckerInterface, DummyChecker
from suricata_check.utils.rule import parse

logger = logging.getLogger(__name__)

INSTRUCTIONS = """Provides structured feedback on Suricata rules using suricata-check.

Tools:
- `analyze_rule`: checks a single rule provided as text. Use it to validate a rule you wrote or modified, and re-run it after every change to verify that issues are resolved.
- `process_rules_file`: checks all rules in a rules file, given as a path on the machine running this server. Use it to assess an existing ruleset.
- `list_checkers`: lists the available checkers and their issue codes. Use it to find valid values for the `include` and `exclude` regular expressions, which match issue codes.

Reading results: every issue has a `code`, a `message` and the `checker` that reported it. The message explains what is wrong and what to change. The first letter of the code indicates the type of issue:
- `M` (mandatory): the rule is invalid or incomplete and will most probably not be used by Suricata. Always fix these.
- `S` (style guide): adherence to the Suricata Style Guide, hinting at interpretability or efficiency issues.
- `C` (community): best practices proposed by the community.
- `P` and `Q` (principles): rule design issues relating to specificity and coverage, only available when the suricata-check-design-principles extension is installed.

Fixing rules: preserve the detection logic design and the `sid` of the rule, and do not remove rule options merely to silence an issue. Treat `S`, `C`, `P` and `Q` issues as recommendations that should be weighed against the intent of the rule.

Suppressing issues: instead of fixing an issue that is not relevant, suppress it, and tell the user which issues you suppressed and why.
- For all rules: use the `exclude` argument with specific issue codes or types, e.g. `exclude=["S800"]` or `exclude=["S.*"]`.
- For individual rules: if an issue is not relevant for some rules but is relevant for others, suppress it only in those rules by adding `suricata-check "<code regex>"` to their `metadata` option, e.g. `metadata: suricata-check "S800";`. This in-rule suppression is applied by `process_rules_file` but not by `analyze_rule`, so also pass `exclude` to `analyze_rule` to verify such a rule.

Documentation: for more information on the issue codes, writing better rules and suppressing issues, refer to the suricata-check documentation at https://suricata-check.teuwen.net/
"""  # noqa: E501

mcp = FastMCP("suricata-check", instructions=INSTRUCTIONS)

DEFAULT_INCLUDE = (".*",)


class CheckerInfo(pydantic.BaseModel):
    """A checker discovered by suricata-check together with its issue codes.

    The checker name doubles as the issue group used in the `issues_by_group` summaries returned by the `process_rules_file` tool.
    """  # noqa: E501

    name: str
    description: str | None = None
    enabled_by_default: bool
    codes: dict[str, dict[str, int]]


class ListCheckersOutput(pydantic.BaseModel):
    """The list of checkers available for selection in the analysis tools."""

    checkers: list[CheckerInfo]


def _validate_regexes(
    include: Sequence[str],
    exclude: Sequence[str],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Validates the include and exclude regexes and returns them as tuples.

    Raises:
        ValueError: Naming the offending pattern if a regex cannot be compiled.
    """
    defaults: dict[str, tuple[str, ...]] = {"include": DEFAULT_INCLUDE, "exclude": ()}

    validated: list[tuple[str, ...]] = []
    for kind, regexes in (("include", include), ("exclude", exclude)):
        for regex in regexes:
            try:
                re.compile(regex)
            except re.error as error:
                msg = f"Invalid {kind} regular expression: {regex} ({error})"
                logger.warning(msg)
                raise ValueError(msg) from error
        validated.append(tuple(regexes) if regexes else defaults[kind])

    return validated[0], validated[1]


@functools.lru_cache(maxsize=1)
def _get_all_checkerclasses() -> tuple[type[CheckerInterface], ...]:
    """Returns all checker classes discovered by suricata-check, including extensions."""
    # Ensure extension modules are imported through the public core API before walking subclasses.
    suricata_check.get_checkers(include=DEFAULT_INCLUDE, exclude=())

    checker_classes: list[type[CheckerInterface]] = []
    pending = [CheckerInterface]
    while pending:
        checker_class = pending.pop()
        pending.extend(checker_class.__subclasses__())

        if checker_class in (CheckerInterface, DummyChecker):
            continue

        if issubclass(checker_class, DummyChecker):
            # Instantiating the dummy retrieves the error message about failed imports.
            checker_class()

        checker_classes.append(checker_class)

    return tuple(sorted(checker_classes, key=lambda cls: cls.__name__))


@mcp.tool("analyze_rule")
def analyze_rule(
    rule: str,
    include: Sequence[str] = DEFAULT_INCLUDE,
    exclude: Sequence[str] = (),
) -> dict[str, Any]:
    """Analyzes a given Suricata rule or set of rules using the suricata-check checkers.

    Use this tool when the AI agent needs to validate a rule created elsewhere. The tool runs the suricata-check checkers on the parsed rule and returns structured feedback on potential issues found (e.g., syntax errors, deprecated keywords).

    The tool either returns the analysis report or raises a ``ValueError`` with an actionable message when the input is empty or cannot be parsed as a Suricata rule.

    Args:
        rule: A Suricata rule or set of rules, provided as a non-empty string.
        include: List of all checker codes to enable. Regexes can be provided.
        exclude: List of all checker codes to disable. Regexes can be provided.

    Raises:
        ValueError: If the input is empty, cannot be parsed as a Suricata rule, or an invalid ``include``/``exclude`` regex is provided.
    """  # noqa: E501
    validated_include, validated_exclude = _validate_regexes(include, exclude)

    if not rule.strip():
        logger.warning(
            """Rule analysis called with empty or invalid rule to review: %s""",
            rule,
        )
        msg = (
            "Rule analysis called with empty or invalid rule to review. "
            "The rule should be provided as a non-empty string. "
            f"Received: {rule}"
        )
        raise ValueError(msg)

    parsed_rule = parse(rule)
    if parsed_rule is None:
        logger.info("Failed to parse rule using suricata-check parse utility: %s", rule)
        msg = (
            "Failed to parse the given input as a Suricata rule. "
            "Ensure the input follows the Suricata rule syntax: an action, protocol, source "
            "address and port, direction, destination address and port, followed by rule "
            "options in parentheses, e.g. "
            f'alert tcp $HOME_NET any -> $EXTERNAL_NET $HTTP_PORTS (msg:"Test rule"; '
            "sid:1000001; rev:1;) "
            "and that the rule option parentheses are balanced. "
            f"Received: {rule}"
        )
        raise ValueError(msg)

    logger.info("Successfully parsed rule, proceeding with analysis: %s", rule)
    checkers = suricata_check.get_checkers(
        validated_include,
        validated_exclude,
    )
    return suricata_check.analyze_rule(parsed_rule, checkers=checkers).to_dict()


@mcp.tool("list_checkers")
def list_checkers() -> ListCheckersOutput:
    """Lists all checkers available in suricata-check together with their issue codes.

    Use this tool to discover valid values for the ``include`` and ``exclude`` regex arguments of the other tools instead of guessing checker codes. Issue codes follow the regex ``[A-Z]{1,}[0-9]{3}``; the checker name is the issue group used in the summaries of the `process_rules_file` tool.
    """  # noqa: E501
    checker_classes = _get_all_checkerclasses()
    return ListCheckersOutput(
        checkers=[
            CheckerInfo(
                name=checker_class.__name__,
                codes={
                    code: dict(mapping) for code, mapping in checker_class.codes.items()
                },
                description=(
                    (checker_class.__doc__ or "").strip().splitlines()[0]
                    if checker_class.__doc__ is not None
                    else None
                ),
                enabled_by_default=checker_class.enabled_by_default,
            )
            for checker_class in checker_classes
        ],
    )


@mcp.tool("process_rules_file")
def process_rules_file(
    rules: str,
    evaluate_disabled: bool = False,
    include: Sequence[str] = DEFAULT_INCLUDE,
    exclude: Sequence[str] = (),
) -> dict[str, Any]:
    """Processes a rules file and returns a list of rules and their issues.

    Each entry in the returned ``rules`` list contains the original rule text, the line range the rule was parsed from (when known), and the issues reported by suricata-check for that rule.

    Args:
        rules: A path to a Suricata rules file.
        evaluate_disabled: A flag indicating whether disabled rules should be evaluated.
        include: List of all checker codes to enable. Regexes can be provided.
        exclude: List of all checker codes to disable. Regexes can be provided.

    Raises:
        ValueError: If an invalid ``include``/``exclude`` regex is provided.
    """  # noqa: E501
    validated_include, validated_exclude = _validate_regexes(include, exclude)
    checkers = suricata_check.get_checkers(
        validated_include,
        validated_exclude,
    )
    output = suricata_check.process_rules_file(
        rules,
        evaluate_disabled,
        checkers=checkers,
    )
    return {
        "rules": [rule.to_dict() for rule in output.rules],
        "summary": output.summary.to_dict() if output.summary is not None else None,
        "issues_by_group": (
            output.summary.issues_by_group if output.summary is not None else {}
        ),
        "issues_by_type": (
            output.summary.issues_by_type if output.summary is not None else {}
        ),
    }
