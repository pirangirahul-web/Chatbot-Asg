"""Custom Rasa actions for the Eco-Travel Advisor."""
import logging
import json
from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, FollowupAction
from rasa_sdk.types import DomainDict

from .climate_api import calculate_carbon
from .amadeus_api import fetch_hotels
from .ranking import rank_options

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Form validation
# ---------------------------------------------------------------------------
class ValidateTripIntakeForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_trip_intake_form"

    async def validate_destination(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if not slot_value or len(str(slot_value).strip()) < 2:
            dispatcher.utter_message(text="Please give me a valid destination name.")
            return {"destination": None}
        # Normalize case
        return {"destination": str(slot_value).strip().title()}

    async def validate_travel_dates(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if not slot_value:
            return {"travel_dates": None}
        return {"travel_dates": str(slot_value)}

    async def validate_budget(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        try:
            b = float(str(slot_value).replace("$", "").replace(",", ""))
            if b <= 0:
                raise ValueError
            return {"budget": str(int(b))}
        except (TypeError, ValueError):
            dispatcher.utter_message(text="Budget should be a positive number (e.g. 1500).")
            return {"budget": None}

    async def validate_sustainability_level(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        allowed = {"low", "medium", "high"}
        val = str(slot_value).lower().strip()
        if val not in allowed:
            dispatcher.utter_message(
                text="Please choose low, medium, or high sustainability."
            )
            return {"sustainability_level": None}
        return {"sustainability_level": val}


# ---------------------------------------------------------------------------
# Carbon calculation
# ---------------------------------------------------------------------------
class ActionCalculateCarbon(Action):
    def name(self) -> Text:
        return "action_calculate_carbon"

    def run(self, dispatcher, tracker, domain):
        transport = tracker.get_slot("transport_mode") or "flight"
        destination = tracker.get_slot("destination") or "Paris"
        origin = "London"

        try:
            result = calculate_carbon(origin, destination, transport)
            co2e = result["co2e"]
            source = result["source"]
        except Exception:
            logger.exception("Carbon calc failed")
            dispatcher.utter_message(text="I couldn't calculate carbon right now. Try again later.")
            return []

        # Human-readable message
        dispatcher.utter_message(
            text=f"🌍 Estimated carbon: **{co2e} kg CO₂e** "
                 f"({transport} · {origin} → {destination}, source: {source})."
        )

        # Colour code
        if co2e < 200:
            level, emoji = "green", "🟢"
        elif co2e < 600:
            level, emoji = "amber", "🟡"
        else:
            level, emoji = "red", "🔴"

        # Custom JSON card for the frontend
        dispatcher.utter_message(
            json_message={
                "type": "carbon_card",
                "level": level,
                "emoji": emoji,
                "co2e": co2e,
                "transport": transport,
                "origin": origin,
                "destination": destination,
                "source": source,
            }
        )

        if level == "red":
            dispatcher.utter_message(response="utter_high_emission_warning")

        return [SlotSet("carbon_estimate", float(co2e))]


# ---------------------------------------------------------------------------
# Fetch hotels
# ---------------------------------------------------------------------------
class ActionFetchHotelsFlights(Action):
    def name(self) -> Text:
        return "action_fetch_hotels_flights"

    def run(self, dispatcher, tracker, domain):
        city = tracker.get_slot("destination") or "Paris"
        try:
            hotels = fetch_hotels(city)
        except Exception:
            logger.exception("Hotel fetch failed")
            dispatcher.utter_message(text="I couldn't fetch hotels. Please try again.")
            return []

        if not hotels:
            dispatcher.utter_message(text=f"No hotels found for {city}.")
            return []

        return [SlotSet("recommendations", json.dumps(hotels))]


# ---------------------------------------------------------------------------
# Rank options
# ---------------------------------------------------------------------------
class ActionRankOptions(Action):
    def name(self) -> Text:
        return "action_rank_options"

    def run(self, dispatcher, tracker, domain):
        raw = tracker.get_slot("recommendations")
        if not raw:
            return []

        try:
            hotels = json.loads(raw)
        except json.JSONDecodeError:
            return []

        level = tracker.get_slot("sustainability_level") or "medium"
        budget = tracker.get_slot("budget")
        try:
            budget = float(budget) if budget else None
        except (TypeError, ValueError):
            budget = None

        ranked = rank_options(hotels, level, budget)

        if not ranked:
            dispatcher.utter_message(text="No matching options found.")
            return []

        dispatcher.utter_message(
            text=f"Here are your top eco-friendly stays "
                 f"(sustainability: {level}):"
        )

        # Emit each hotel as a JSON card
        for h in ranked[:3]:
            carbon = h["carbon_kg"]
            if carbon < 15:
                emoji = "🟢"
            elif carbon < 30:
                emoji = "🟡"
            else:
                emoji = "🔴"

            dispatcher.utter_message(
                json_message={
                    "type": "hotel_card",
                    "name": h["name"],
                    "price": h["price"],
                    "eco_rating": h["eco_rating"],
                    "carbon_kg": carbon,
                    "emoji": emoji,
                    "score": h.get("score", 0),
                }
            )

        return []


# ---------------------------------------------------------------------------
# Human handover
# ---------------------------------------------------------------------------
class ActionHandoverToHuman(Action):
    def name(self) -> Text:
        return "action_handover_to_human"

    def run(self, dispatcher, tracker, domain):
        context = {
            "sender_id": tracker.sender_id,
            "destination": tracker.get_slot("destination"),
            "travel_dates": tracker.get_slot("travel_dates"),
            "budget": tracker.get_slot("budget"),
            "sustainability_level": tracker.get_slot("sustainability_level"),
            "carbon_estimate": tracker.get_slot("carbon_estimate"),
            "transcript": [
                {"role": "user" if e.get("event") == "user" else "bot",
                 "text": e.get("text")}
                for e in tracker.events
                if e.get("event") in ("user", "bot") and e.get("text")
            ][-20:],
        }
        logger.info("Handover context: %s", json.dumps(context))
        # Emit JSON event so the frontend can show the handover badge
        dispatcher.utter_message(
            json_message={"type": "handover", "status": "started"}
        )
        return [SlotSet("handover_requested", True)]


# ---------------------------------------------------------------------------
# Two-stage fallback
# ---------------------------------------------------------------------------
class ActionTwoStageClarification(Action):
    def name(self) -> Text:
        return "action_two_stage_clarification"

    def run(self, dispatcher, tracker, domain):
        fallback_count = sum(
            1 for e in tracker.events
            if e.get("event") == "user"
            and e.get("parse_data", {}).get("intent", {}).get("name") == "nlu_fallback"
        )

        if fallback_count >= 2:
            dispatcher.utter_message(response="utter_fallback_2")
            return [FollowupAction("action_handover_to_human")]

        dispatcher.utter_message(response="utter_fallback_1")
        return []


# ---------------------------------------------------------------------------
# Reset slots
# ---------------------------------------------------------------------------
class ActionResetSlots(Action):
    def name(self) -> Text:
        return "action_reset_slots"

    def run(self, dispatcher, tracker, domain):
        return [
            SlotSet("destination", None),
            SlotSet("travel_dates", None),
            SlotSet("budget", None),
            SlotSet("sustainability_level", None),
            SlotSet("transport_mode", None),
            SlotSet("carbon_estimate", None),
            SlotSet("recommendations", None),
            SlotSet("handover_requested", False),
        ]