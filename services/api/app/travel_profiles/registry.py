"""The travel-profile vocabulary (ADR-009).

Single source of truth for allowed values: the API validates against it and the web app renders
its onboarding/profile controls from `GET /meta/travel-profile-options`, so labels never drift.
Values are stable identifiers stored in the database — rename labels freely, never values.
"""

from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True)
class Option:
    value: str
    label: str
    description: str = ""


@dataclass(frozen=True)
class PreferenceKey:
    key: str
    label: str
    group: str
    description: str = ""


class Pace(StrEnum):
    RELAXED = "relaxed"
    BALANCED = "balanced"
    PACKED = "packed"


class BudgetStyle(StrEnum):
    SHOESTRING = "shoestring"
    MODERATE = "moderate"
    COMFORTABLE = "comfortable"
    LUXURY = "luxury"


class AccommodationStyle(StrEnum):
    HOSTEL = "hostel"
    BUDGET_HOTEL = "budget_hotel"
    BOUTIQUE = "boutique"
    LUXURY = "luxury"
    APARTMENT = "apartment"


class WalkingTolerance(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


TRAVEL_STYLES: tuple[Option, ...] = (
    Option("food", "Food-first", "Trips planned around what you'll eat."),
    Option("culture", "Culture & history", "Museums, temples, old towns and stories."),
    Option("nature", "Nature & scenery", "Gardens, coastlines, mountains and views."),
    Option("relaxation", "Slow & restful", "Room to breathe, linger and recharge."),
    Option("adventure", "Adventure", "Active days and things you haven't tried."),
    Option("shopping", "Shopping", "Markets, boutiques and design stores."),
    Option("nightlife", "Nightlife", "Bars, live music and late evenings."),
    Option("romance", "Romantic", "Beautiful settings for two."),
)
MAX_TRAVEL_STYLES = 5

PACES: tuple[Option, ...] = (
    Option(Pace.RELAXED, "Relaxed", "A few highlights a day, long meals, no rushing."),
    Option(Pace.BALANCED, "Balanced", "A full day with breathing room."),
    Option(Pace.PACKED, "Packed", "See as much as possible."),
)

BUDGET_STYLES: tuple[Option, ...] = (
    Option(BudgetStyle.SHOESTRING, "Shoestring", "Keep costs as low as possible."),
    Option(BudgetStyle.MODERATE, "Moderate", "Good value, the occasional treat."),
    Option(BudgetStyle.COMFORTABLE, "Comfortable", "Comfort matters more than saving."),
    Option(BudgetStyle.LUXURY, "Luxury", "The best experiences, price secondary."),
)

ACCOMMODATION_STYLES: tuple[Option, ...] = (
    Option(AccommodationStyle.HOSTEL, "Hostels"),
    Option(AccommodationStyle.BUDGET_HOTEL, "Simple hotels"),
    Option(AccommodationStyle.BOUTIQUE, "Boutique hotels"),
    Option(AccommodationStyle.LUXURY, "Luxury hotels"),
    Option(AccommodationStyle.APARTMENT, "Apartments"),
)

WALKING_TOLERANCES: tuple[Option, ...] = (
    Option(WalkingTolerance.LOW, "Keep walking short", "Prefer taxis or transit between stops."),
    Option(WalkingTolerance.MEDIUM, "Some walking is fine", "Happy to walk 15–20 minutes."),
    Option(WalkingTolerance.HIGH, "Love to walk", "Walking is part of the experience."),
)

DIETARY: tuple[Option, ...] = (
    Option("vegetarian", "Vegetarian"),
    Option("vegan", "Vegan"),
    Option("halal", "Halal"),
    Option("kosher", "Kosher"),
    Option("gluten_free", "Gluten-free"),
    Option("dairy_free", "Dairy-free"),
    Option("no_pork", "No pork"),
    Option("no_seafood", "No seafood"),
    Option("nut_allergy", "Nut allergy"),
)

PREFERENCE_GROUPS: tuple[Option, ...] = (
    Option("food", "Food & drink"),
    Option("culture", "Culture"),
    Option("nature", "Nature & outdoors"),
    Option("shopping", "Shopping"),
    Option("experiences", "Experiences & evenings"),
    Option("style", "How you like to explore"),
)

PREFERENCE_KEYS: tuple[PreferenceKey, ...] = (
    PreferenceKey("food.street_food", "Street food", "food"),
    PreferenceKey("food.local_markets", "Food markets", "food"),
    PreferenceKey("food.fine_dining", "Fine dining", "food"),
    PreferenceKey("food.cafes", "Cafés & coffee", "food"),
    PreferenceKey("food.desserts", "Sweets & bakeries", "food"),
    PreferenceKey("food.bars", "Bars & cocktails", "food"),
    PreferenceKey("food.wine", "Wine & tastings", "food"),
    PreferenceKey("culture.museums", "Museums", "culture"),
    PreferenceKey("culture.history", "Historic sites", "culture"),
    PreferenceKey("culture.architecture", "Architecture", "culture"),
    PreferenceKey("culture.art", "Art & galleries", "culture"),
    PreferenceKey("culture.religious_sites", "Temples, shrines & churches", "culture"),
    PreferenceKey("culture.performing_arts", "Live performance", "culture"),
    PreferenceKey("nature.parks_gardens", "Parks & gardens", "nature"),
    PreferenceKey("nature.viewpoints", "Viewpoints", "nature"),
    PreferenceKey("nature.hiking", "Hiking", "nature"),
    PreferenceKey("nature.beaches", "Beaches", "nature"),
    PreferenceKey("shopping.markets", "Markets & flea markets", "shopping"),
    PreferenceKey("shopping.boutiques", "Boutiques & design", "shopping"),
    PreferenceKey("shopping.malls", "Department stores & malls", "shopping"),
    PreferenceKey("experiences.nightlife", "Clubs & late nights", "experiences"),
    PreferenceKey("experiences.classes", "Classes & workshops", "experiences"),
    PreferenceKey("experiences.wellness", "Spas & wellness", "experiences"),
    PreferenceKey("experiences.photography", "Photo spots", "experiences"),
    PreferenceKey(
        "style.famous_sights", "Famous landmarks", "style", "The places everyone talks about."
    ),
    PreferenceKey(
        "style.hidden_gems", "Hidden gems", "style", "Places locals love that guides skip."
    ),
    PreferenceKey("style.crowds", "Lively, busy places", "style", "Energy and crowds."),
)

PREFERENCE_KEYS_BY_KEY = {pref.key: pref for pref in PREFERENCE_KEYS}
TRAVEL_STYLE_VALUES = frozenset(option.value for option in TRAVEL_STYLES)
DIETARY_VALUES = frozenset(option.value for option in DIETARY)
