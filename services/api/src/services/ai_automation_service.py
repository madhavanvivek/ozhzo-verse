import re
from typing import Optional
from uuid import uuid4

from src.schemas.automations import (
    ActionType,
    AIAutomationProposalRequest,
    AIAutomationProposalResponse,
    AutomationActionSchema,
    ConditionGroupSchema,
    ConditionOperator,
    ConditionRuleSchema,
    ScheduleConfigSchema,
    TriggerType,
)


class AIAutomationService:
    """
    Translates user natural language requests into structured, explainable, and validated automation proposals.
    Strictly adheres to: AI Proposes -> User Confirms -> Authoritative Creation.
    """

    @classmethod
    def propose_automation_from_prompt(
        cls, request: AIAutomationProposalRequest
    ) -> AIAutomationProposalResponse:
        prompt = request.prompt.strip()
        p_lower = prompt.lower()

        # 1. Pantry low stock -> Add to shopping list
        if any(w in p_lower for w in ["low", "pantry", "stock", "running out", "depleted"]) and any(w in p_lower for w in ["shopping", "buy", "cart", "purchase"]):
            # Extract item name
            match = re.search(r"(?:when|if|whenever)?\s*([a-zA-Z\s]+?)\s*(?:is|runs|gets)?\s*(?:low|out of stock)", p_lower)
            raw_item = match.group(1).strip() if match else "Item"
            raw_item = re.sub(r"^(the|pantry|our|some)\s+", "", raw_item).strip().title()
            item_name = raw_item or "Household Supply"

            conditions = ConditionGroupSchema(
                operator="AND",
                rules=[
                    ConditionRuleSchema(
                        field="quantity",
                        op=ConditionOperator.LESS_THAN,
                        value=2.0
                    )
                ]
            )

            actions = [
                AutomationActionSchema(
                    action_type=ActionType.ADD_SHOPPING_ITEM,
                    params={
                        "name": item_name,
                        "quantity": 1.0,
                        "unit": "pcs"
                    }
                )
            ]

            return AIAutomationProposalResponse(
                proposal_id=str(uuid4()),
                name=f"Auto-Restock {item_name}",
                description=f"Automatically adds {item_name} to the shopping list when stock falls below 2.",
                trigger_type=TriggerType.INVENTORY_LOW,
                conditions=conditions,
                actions=actions,
                schedule=None,
                explanation=f"Whenever '{item_name}' quantity in household inventory falls below 2, Ozhzo will add 1 pcs of '{item_name}' to the household purchase list.",
                requires_confirmation=True
            )

        # 2. Recurring Bill reminder / task
        elif any(w in p_lower for w in ["bill", "utility", "electricity", "water", "rent", "internet"]) and any(w in p_lower for w in ["remind", "pay", "due", "monthly"]):
            match_title = re.search(r"(?:pay|for|the)\s+([a-zA-Z\s]+?)(?:\s+bill|\s+every|\s+each|$)", p_lower)
            title = match_title.group(1).strip().title() if match_title else "Utility"
            bill_title = f"{title} Bill"

            conditions = ConditionGroupSchema(
                operator="AND",
                rules=[
                    ConditionRuleSchema(
                        field="status",
                        op=ConditionOperator.EQUALS,
                        value="UNPAID"
                    )
                ]
            )

            actions = [
                AutomationActionSchema(
                    action_type=ActionType.CREATE_NOTIFICATION,
                    params={
                        "title": f"Upcoming: {bill_title}",
                        "body": f"Please verify payment for {bill_title} before its due date.",
                        "priority": "HIGH",
                        "requires_action": True
                    }
                ),
                AutomationActionSchema(
                    action_type=ActionType.CREATE_TASK,
                    params={
                        "title": f"Pay {bill_title}",
                        "priority": "HIGH",
                        "due_in_days": 2
                    }
                )
            ]

            return AIAutomationProposalResponse(
                proposal_id=str(uuid4()),
                name=f"Monthly Reminder: {bill_title}",
                description=f"Creates high-priority notification and task when {bill_title} is approaching due date.",
                trigger_type=TriggerType.BILL_APPROACHING,
                conditions=conditions,
                actions=actions,
                schedule=ScheduleConfigSchema(cron="0 9 1 * *", timezone="Asia/Kolkata"),
                explanation=f"When {bill_title} becomes due or on the 1st of each month, Ozhzo creates an urgent notification and task for household managers.",
                requires_confirmation=True
            )

        # 3. Scheduled Chores / Recurring cleaning
        elif any(w in p_lower for w in ["clean", "chore", "task", "sunday", "weekly", "trash", "plants", "garden"]):
            match_task = re.search(r"(?:task|to|chore)\s+(.+?)(?:\s+every|\s+on|\s+each|$)", p_lower)
            task_name = match_task.group(1).strip().capitalize() if match_task else "Weekly Household Maintenance"

            actions = [
                AutomationActionSchema(
                    action_type=ActionType.CREATE_TASK,
                    params={
                        "title": task_name,
                        "priority": "NORMAL",
                        "due_in_days": 1
                    }
                )
            ]

            return AIAutomationProposalResponse(
                proposal_id=str(uuid4()),
                name=f"Recurring: {task_name}",
                description=f"Automatically creates chore '{task_name}' on schedule.",
                trigger_type=TriggerType.SCHEDULE,
                conditions=ConditionGroupSchema(operator="AND", rules=[]),
                actions=actions,
                schedule=ScheduleConfigSchema(cron="0 8 * * 0", interval_days=7, timezone="Asia/Kolkata"),
                explanation=f"Every Sunday at 8:00 AM, Ozhzo will generate task '{task_name}' for household members.",
                requires_confirmation=True
            )

        # 4. Default general household rule
        else:
            return AIAutomationProposalResponse(
                proposal_id=str(uuid4()),
                name="Household Activity Notification",
                description="Sends a notification when household activity is recorded.",
                trigger_type=TriggerType.TASK_COMPLETED,
                conditions=ConditionGroupSchema(operator="AND", rules=[]),
                actions=[
                    AutomationActionSchema(
                        action_type=ActionType.CREATE_NOTIFICATION,
                        params={
                            "title": "Chore Completed",
                            "body": "A household task was marked complete.",
                            "priority": "LOW"
                        }
                    )
                ],
                schedule=None,
                explanation="Sends a low-priority update whenever a chore or task is completed in the household.",
                requires_confirmation=True
            )
