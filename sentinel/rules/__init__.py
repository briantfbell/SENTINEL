"""Rule engine: decides what actions to fire for (event, state). Never
writes state (AGENTS.md section 4.5).
"""

from sentinel.rules.registry import RULES, RuleEngine, TableRule

__all__ = ["RULES", "RuleEngine", "TableRule"]
