from abc import ABC, abstractmethod
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
import re
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from src.core.ai_config import AIModelConfig
from src.schemas.ai import (
    AIActionProposalDTO,
    AIActionType,
    AIIntentType,
    AIRecommendationDTO,
)


class BaseAIProvider(ABC):
    """
    Abstract Base Class for AI model backends.
    """

    @abstractmethod
    async def detect_intent(
        self, message: str, context: Dict[str, Any]
    ) -> Tuple[AIIntentType, float, Optional[Dict[str, Any]]]:
        """
        Classifies user message into a structured intent with confidence and extracted parameters.
        """
        pass

    @abstractmethod
    async def generate_response(
        self,
        message: str,
        intent: AIIntentType,
        context: Dict[str, Any],
        action_proposal: Optional[AIActionProposalDTO] = None,
    ) -> Tuple[str, List[str]]:
        """
        Generates contextual natural language reply and quick follow-up prompt chips.
        """
        pass

    @abstractmethod
    async def generate_recommendations(
        self, context: Dict[str, Any]
    ) -> List[AIRecommendationDTO]:
        """
        Generates predictive household recommendations based on current context.
        """
        pass


class MockAIProvider(BaseAIProvider):
    """
    Deterministic, zero-latency, production-safe Mock AI Provider.
    Extracts intents, parameters, and generates rich contextual responses.
    """

    def __init__(self, config: Optional[AIModelConfig] = None):
        self.config = config or AIModelConfig()

    async def detect_intent(
        self, message: str, context: Dict[str, Any]
    ) -> Tuple[AIIntentType, float, Optional[Dict[str, Any]]]:
        msg_lower = message.strip().lower()

        # 1. Shopping write / add
        if any(w in msg_lower for w in ["add to shopping", "add to cart", "buy ", "purchase ", "add item", "shopping list"]):
            # Extract item name
            match = re.search(r"(?:add|buy|need|purchase)\s+(.+?)(?:\s+to\s+(?:the\s+)?(?:shopping|purchase|buy)\s*(?:list)?|\s*$)", msg_lower, re.IGNORECASE)
            item_name = match.group(1).strip() if match else "Item"
            # Cleanup common stop words
            item_name = re.sub(r"^(to\s+the\s+shopping\s+list|some|a|an)\s+", "", item_name, flags=re.IGNORECASE).strip()
            item_title = item_name.title() if item_name else "Groceries"

            return (
                AIIntentType.ADD_SHOPPING_ITEM,
                0.95,
                {
                    "item_name": item_title,
                    "quantity": 1.0,
                    "unit": "item"
                }
            )

        # 2. Shopping query
        if any(w in msg_lower for w in ["shopping list", "what to buy", "groceries", "items to purchase", "buy list"]):
            return (AIIntentType.QUERY_SHOPPING, 0.95, None)

        # 3. Tasks write / create
        if any(w in msg_lower for w in ["create task", "add task", "new task", "remind me to", "assign task", "create chore", "schedule task"]):
            match = re.search(r"(?:create task|add task|new task|remind me to|create chore)\s+(.+)", msg_lower, re.IGNORECASE)
            task_title = match.group(1).strip() if match else "Household Task"
            clean_title = task_title.capitalize()

            return (
                AIIntentType.CREATE_TASK,
                0.95,
                {
                    "title": clean_title,
                    "priority": "HIGH" if "urgent" in msg_lower else "NORMAL",
                    "due_date": (date.today() + timedelta(days=1)).isoformat() if "tomorrow" in msg_lower else date.today().isoformat()
                }
            )

        # 4. Tasks complete
        if any(w in msg_lower for w in ["complete task", "done with", "finish task", "mark task done", "finished"]):
            return (AIIntentType.COMPLETE_TASK, 0.90, {"query": msg_lower})

        # 5. Tasks query
        if any(w in msg_lower for w in ["task", "chore", "to do", "todo", "what do i need to do", "pending work", "today's work", "assigned to me"]):
            return (AIIntentType.QUERY_TASKS, 0.95, None)

        # 6. Bills write / create
        if any(w in msg_lower for w in ["create bill", "add bill", "new bill", "record bill"]):
            match_amt = re.search(r"(\d+(?:\.\d{1,2})?)", msg_lower)
            amount = float(match_amt.group(1)) if match_amt else 1000.0
            
            match_title = re.search(r"(?:create bill|add bill|new bill|record bill)\s+([a-zA-Z\s]+)", msg_lower, re.IGNORECASE)
            title = match_title.group(1).strip().title() if match_title else "Utility Bill"

            return (
                AIIntentType.CREATE_BILL,
                0.95,
                {
                    "title": title or "Utility Expense",
                    "amount": amount,
                    "currency": context.get("currency", "INR"),
                    "due_date": (date.today() + timedelta(days=7)).isoformat()
                }
            )

        # 7. Bills query
        if any(w in msg_lower for w in ["bill", "invoice", "utility", "due payment", "pending payments", "what do i owe", "unpaid"]):
            return (AIIntentType.QUERY_BILLS, 0.95, None)

        # 8. Calendar write / create
        if any(w in msg_lower for w in ["create event", "add event", "schedule meeting", "schedule dinner", "plan event"]):
            return (
                AIIntentType.CREATE_EVENT,
                0.95,
                {
                    "title": "Family Event",
                    "start_time": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                    "end_time": (datetime.now(timezone.utc) + timedelta(days=1, hours=2)).isoformat()
                }
            )

        # 9. Calendar query
        if any(w in msg_lower for w in ["calendar", "event", "schedule", "plan", "agenda", "upcoming meetings"]):
            return (AIIntentType.QUERY_EVENTS, 0.95, None)

        # 10. Inventory query / low stock
        if any(w in msg_lower for w in ["pantry", "inventory", "stock", "running low", "low stock", "supplies", "how much", "remaining"]):
            return (AIIntentType.QUERY_INVENTORY, 0.95, None)

        # 11. Members query
        if any(w in msg_lower for w in ["member", "family", "who lives", "who is in", "residents"]):
            return (AIIntentType.QUERY_MEMBERS, 0.95, None)

        # 12. Notifications query
        if any(w in msg_lower for w in ["alert", "notification", "updates", "recent activity"]):
            return (AIIntentType.QUERY_NOTIFICATIONS, 0.95, None)

        # 13. Subscription status
        if any(w in msg_lower for w in ["subscription", "quota", "plan", "credits", "renewal"]):
            return (AIIntentType.SUBSCRIPTION_STATUS, 0.95, None)

        # Default fallback
        return (AIIntentType.GENERAL_HOUSEHOLD_QUERY, 0.80, None)

    async def generate_response(
        self,
        message: str,
        intent: AIIntentType,
        context: Dict[str, Any],
        action_proposal: Optional[AIActionProposalDTO] = None,
    ) -> Tuple[str, List[str]]:
        home_name = context.get("home_name", "Home")

        if action_proposal:
            return (
                f"I have prepared the action for **{home_name}**: {action_proposal.description}. Please confirm below to execute it.",
                ["Confirm Action", "Cancel"]
            )

        # 1. QUERY_TASKS
        if intent == AIIntentType.QUERY_TASKS:
            tasks = context.get("tasks", [])
            if not tasks:
                return (
                    f"All chores and tasks are completed for **{home_name}**! Great job keeping the household running smoothly.",
                    ["What bills are due?", "Check pantry stock", "+ Create new task"]
                )
            task_list = "\n".join([f"• **{t.get('title')}** (Priority: {t.get('priority', 'NORMAL')})" for t in tasks[:5]])
            return (
                f"Here are the active tasks for **{home_name}**:\n\n{task_list}\n\nWould you like me to assign or complete any of these?",
                ["What bills are due?", "+ Add to shopping", "Check low stock"]
            )

        # 2. QUERY_BILLS
        if intent == AIIntentType.QUERY_BILLS:
            bills = context.get("bills", [])
            if not bills:
                return (
                    f"There are no outstanding bills due for **{home_name}**.",
                    ["Show active tasks", "Check shopping list"]
                )
            curr = context.get("currency", "INR")
            bill_list = "\n".join([f"• **{b.get('title')}**: {curr} {float(b.get('amount', 0)):,.2f} (Due: {b.get('due_date')})" for b in bills[:5]])
            return (
                f"Here are the upcoming bills for **{home_name}**:\n\n{bill_list}",
                ["Show active tasks", "+ Record new bill", "Check shopping list"]
            )

        # 3. QUERY_INVENTORY
        if intent == AIIntentType.QUERY_INVENTORY:
            low_stock = context.get("low_stock", [])
            if not low_stock:
                return (
                    f"Your household pantry and supplies at **{home_name}** are well-stocked. No items are below minimum threshold.",
                    ["Show shopping list", "What tasks are due?"]
                )
            items_str = "\n".join([f"• **{item.get('name')}**: {item.get('quantity')} {item.get('unit')} remaining" for item in low_stock[:5]])
            return (
                f"The following supplies are running low at **{home_name}**:\n\n{items_str}\n\nWould you like me to add these to the shopping list?",
                ["Add low stock to shopping", "Show tasks", "View calendar"]
            )

        # 4. QUERY_SHOPPING
        if intent == AIIntentType.QUERY_SHOPPING:
            shopping = context.get("shopping_items", [])
            if not shopping:
                return (
                    f"The purchase list for **{home_name}** is currently empty.",
                    ["+ Add Milk to shopping", "Check low stock", "What tasks are due?"]
                )
            items_str = "\n".join([f"• {s.get('name')} ({s.get('quantity')} {s.get('unit')})" for s in shopping[:5]])
            return (
                f"Here is your active shopping list for **{home_name}**:\n\n{items_str}",
                ["+ Add more items", "Check low stock", "Show tasks"]
            )

        # 5. QUERY_EVENTS
        if intent == AIIntentType.QUERY_EVENTS:
            events = context.get("events", [])
            if not events:
                return (
                    f"No upcoming calendar events scheduled for **{home_name}**.",
                    ["+ Schedule Event", "Show active tasks"]
                )
            ev_str = "\n".join([f"• **{e.get('title')}** at {e.get('start_time')}" for e in events[:5]])
            return (
                f"Upcoming events for **{home_name}**:\n\n{ev_str}",
                ["Show active tasks", "Check bills"]
            )

        # 6. QUERY_MEMBERS
        if intent == AIIntentType.QUERY_MEMBERS:
            members = context.get("members", [])
            mem_str = ", ".join([m.get("display_name", "Resident") for m in members])
            return (
                f"Active household members at **{home_name}**: {mem_str or 'You'}.",
                ["Show tasks", "Check bills"]
            )

        # General Fallback
        return (
            f"Hello! I am your Ozhzo Household Assistant for **{home_name}**. I can help you manage chores, track bills, restock pantry items, schedule events, and organize shopping. How can I assist you today?",
            ["What's due today?", "What bills are due?", "Check pantry stock", "Show shopping list"]
        )

    async def generate_recommendations(
        self, context: Dict[str, Any]
    ) -> List[AIRecommendationDTO]:
        recs: List[AIRecommendationDTO] = []
        home_name = context.get("home_name", "Home")

        # 1. Low stock restock recommendation
        low_stock = context.get("low_stock", [])
        if low_stock:
            item = low_stock[0]
            recs.append(
                AIRecommendationDTO(
                    domain="INVENTORY",
                    priority="HIGH",
                    title=f"Restock {item.get('name')}",
                    reason=f"{item.get('name')} has only {item.get('quantity')} {item.get('unit')} left.",
                    suggested_action=AIActionProposalDTO(
                        action_type=AIActionType.ADD_SHOPPING_ITEM,
                        title=f"Add {item.get('name')} to Shopping List",
                        description=f"Add 1 {item.get('unit')} of {item.get('name')} to household purchase list.",
                        params={"item_name": item.get("name"), "quantity": 1.0, "unit": item.get("unit", "item")}
                    )
                )
            )

        # 2. Upcoming bill reminder recommendation
        bills = context.get("bills", [])
        if bills:
            bill = bills[0]
            recs.append(
                AIRecommendationDTO(
                    domain="BILL",
                    priority="NORMAL",
                    title=f"Prepare payment for {bill.get('title')}",
                    reason=f"{bill.get('title')} is pending payment of {context.get('currency', 'INR')} {float(bill.get('amount', 0)):,.2f} due on {bill.get('due_date')}.",
                    suggested_action=None
                )
            )

        # 3. Tasks routine recommendation
        tasks = context.get("tasks", [])
        if not tasks:
            recs.append(
                AIRecommendationDTO(
                    domain="TASK",
                    priority="LOW",
                    title="Household is caught up",
                    reason=f"No pending chores at {home_name}. Enjoy your time!",
                    suggested_action=None
                )
            )

        return recs


def get_ai_provider(config: Optional[AIModelConfig] = None) -> BaseAIProvider:
    """
    Factory function providing the active AI model implementation.
    """
    cfg = config or AIModelConfig()
    # Default and fallback is MockAIProvider
    return MockAIProvider(cfg)
