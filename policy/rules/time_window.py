"""Time window policy rule implementation for Pharos Policy Gatekeeper.

Enforces execution bounds based on UTC time of day and day of week
with dependency injection support for deterministic offline testing.
"""

from datetime import datetime, time, timezone
from typing import Any, Dict, List, Optional, Set

from policy.rules.base import BaseRule
from policy.schema import ActionRequest, RuleEvaluationResult, RuleType

WEEKDAY_NAMES = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]


def parse_time_str(t_str: str) -> time:
    """Parses a time string in HH:MM or HH:MM:SS format."""
    parts = [int(p) for p in t_str.strip().split(":")]
    if len(parts) == 2:
        return time(hour=parts[0], minute=parts[1], second=0)
    elif len(parts) == 3:
        return time(hour=parts[0], minute=parts[1], second=parts[2])
    raise ValueError(f"Invalid time format '{t_str}'. Expected HH:MM or HH:MM:SS.")


class TimeWindowRule(BaseRule):
    """Evaluates whether an action is executed within an authorized UTC time window."""

    def __init__(
        self,
        rule_id: str,
        name: str,
        enabled: bool = True,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            rule_id=rule_id,
            name=name,
            rule_type=RuleType.TIME_WINDOW,
            enabled=enabled,
            parameters=parameters,
        )
        params = self.parameters or {}

        # Allowed time of day (default: 08:00 to 20:00 UTC)
        start_str = params.get("allowed_start_utc", "08:00:00")
        end_str = params.get("allowed_end_utc", "20:00:00")
        self.start_time: time = parse_time_str(start_str)
        self.end_time: time = parse_time_str(end_str)
        self.start_str = start_str
        self.end_str = end_str

        # Allowed days of the week (default: Monday - Friday)
        allowed_days_raw = params.get("allowed_days_of_week", ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"])
        self.allowed_days: Set[str] = {str(d).strip().upper() for d in allowed_days_raw}

    def _evaluate(
        self, request: ActionRequest, context: Optional[Dict[str, Any]] = None
    ) -> RuleEvaluationResult:
        # Determine evaluation timestamp with clock dependency injection support
        ts = None
        if context and "evaluation_time" in context:
            ctx_val = context["evaluation_time"]
            if isinstance(ctx_val, datetime):
                dt = ctx_val.astimezone(timezone.utc)
            elif isinstance(ctx_val, (int, float)):
                dt = datetime.fromtimestamp(ctx_val, tz=timezone.utc)
            else:
                return RuleEvaluationResult(
                    rule_id=self.rule_id,
                    rule_type=self.rule_type,
                    passed=False,
                    message=f"Invalid evaluation_time type in context: {type(ctx_val)}.",
                )
        elif request.timestamp is not None:
            if not isinstance(request.timestamp, (int, float)) or request.timestamp < 0:
                return RuleEvaluationResult(
                    rule_id=self.rule_id,
                    rule_type=self.rule_type,
                    passed=False,
                    message=f"Invalid or negative timestamp in request: {request.timestamp}.",
                )
            try:
                dt = datetime.fromtimestamp(request.timestamp, tz=timezone.utc)
            except (ValueError, OverflowError, OSError) as e:
                return RuleEvaluationResult(
                    rule_id=self.rule_id,
                    rule_type=self.rule_type,
                    passed=False,
                    message=f"Timestamp value {request.timestamp} out of range or malformed: {str(e)}.",
                )
        else:
            return RuleEvaluationResult(
                rule_id=self.rule_id,
                rule_type=self.rule_type,
                passed=False,
                message="Missing timestamp in request and no evaluation_time provided in context.",
            )

        # 1. Day of Week Check
        weekday_name = WEEKDAY_NAMES[dt.weekday()]
        if weekday_name not in self.allowed_days:
            return RuleEvaluationResult(
                rule_id=self.rule_id,
                rule_type=self.rule_type,
                passed=False,
                message=(
                    f"Execution on {weekday_name} is not permitted. "
                    f"Authorized days: {sorted(list(self.allowed_days))}."
                ),
            )

        # 2. Time of Day Check (Inclusive boundaries)
        curr_time = dt.timetz().replace(tzinfo=None)  # naive time for comparison

        if self.start_time <= self.end_time:
            # Standard daytime window (e.g. 08:00 to 20:00)
            in_window = self.start_time <= curr_time <= self.end_time
        else:
            # Overnight window (e.g. 22:00 to 06:00)
            in_window = curr_time >= self.start_time or curr_time <= self.end_time

        time_str = curr_time.strftime("%H:%M:%S")
        if not in_window:
            return RuleEvaluationResult(
                rule_id=self.rule_id,
                rule_type=self.rule_type,
                passed=False,
                message=(
                    f"Current time {time_str} UTC is outside authorized operating window "
                    f"({self.start_str} to {self.end_str} UTC)."
                ),
            )

        return RuleEvaluationResult(
            rule_id=self.rule_id,
            rule_type=self.rule_type,
            passed=True,
            message=(
                f"Execution at {weekday_name} {time_str} UTC is within authorized window "
                f"({self.start_str} to {self.end_str} UTC)."
            ),
        )
