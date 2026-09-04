from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional
import logging

from src.schemas.automations import ConditionGroupSchema, ConditionOperator, ConditionRuleSchema

logger = logging.getLogger("ozhzo.automation.conditions")


class AutomationConditionEngine:
    """
    Deterministic, safe condition evaluation engine.
    Completely isolates execution from arbitrary code evaluation.
    """

    @staticmethod
    def _get_nested_field(payload: Dict[str, Any], field_path: str) -> Any:
        parts = field_path.split(".")
        current: Any = payload
        for p in parts:
            if isinstance(current, dict):
                current = current.get(p)
            elif hasattr(current, p):
                current = getattr(current, p)
            else:
                return None
        return current

    @classmethod
    def evaluate_rule(cls, rule: ConditionRuleSchema, payload: Dict[str, Any]) -> bool:
        actual_value = cls._get_nested_field(payload, rule.field)
        target_value = rule.value

        op = rule.op

        if op == ConditionOperator.EXISTS:
            return actual_value is not None

        if actual_value is None:
            return False

        # 1. Numeric comparisons
        if op in (ConditionOperator.GREATER_THAN, ConditionOperator.LESS_THAN):
            try:
                num_actual = Decimal(str(actual_value))
                num_target = Decimal(str(target_value))
                if op == ConditionOperator.GREATER_THAN:
                    return num_actual > num_target
                else:
                    return num_actual < num_target
            except Exception:
                return False

        # 2. String contains comparison
        if op == ConditionOperator.CONTAINS:
            return str(target_value).lower() in str(actual_value).lower()

        # 3. Equality comparisons
        if op == ConditionOperator.EQUALS:
            # Handle boolean strings
            if isinstance(target_value, bool):
                return bool(actual_value) == target_value
            # Handle numeric equality
            try:
                return Decimal(str(actual_value)) == Decimal(str(target_value))
            except Exception:
                return str(actual_value).strip().lower() == str(target_value).strip().lower()

        if op == ConditionOperator.NOT_EQUALS:
            try:
                return Decimal(str(actual_value)) != Decimal(str(target_value))
            except Exception:
                return str(actual_value).strip().lower() != str(target_value).strip().lower()

        return False

    @classmethod
    def evaluate_group(cls, group: Optional[ConditionGroupSchema], payload: Dict[str, Any]) -> bool:
        if not group or not group.rules:
            # Empty condition group trivially evaluates to True
            return True

        operator = (group.operator or "AND").upper()

        if operator == "AND":
            for rule in group.rules:
                if not cls.evaluate_rule(rule, payload):
                    return False
            return True
        elif operator == "OR":
            for rule in group.rules:
                if cls.evaluate_rule(rule, payload):
                    return True
            return False

        return True
