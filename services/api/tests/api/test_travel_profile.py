from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

from tests.helpers import API, register

pytestmark = [pytest.mark.db, pytest.mark.redis, pytest.mark.usefixtures("clean_state")]

PROFILE = f"{API}/me/travel-profile"

VALID_PROFILE: dict[str, Any] = {
    "travel_styles": ["food", "nature", "romance"],
    "pace": "relaxed",
    "budget_style": "comfortable",
    "accommodation_style": "boutique",
    "walking_tolerance": "low",
    "dietary": ["no_pork"],
    "day_start": "09:30:00",
    "day_end": "22:00:00",
}


def _csrf(client: AsyncClient) -> dict[str, str]:
    return {"X-CSRF-Token": client.cookies["atu_csrf"]}


async def _put(client: AsyncClient, body: dict[str, Any]) -> Response:
    return await client.put(PROFILE, json=body, headers=_csrf(client))


async def _patch_prefs(client: AsyncClient, body: dict[str, Any]) -> Response:
    return await client.patch(f"{PROFILE}/preferences", json=body, headers=_csrf(client))


async def test_options_are_public_and_describe_the_registry(client: AsyncClient) -> None:
    response = await client.get(f"{API}/meta/travel-profile-options")

    assert response.status_code == 200
    body = response.json()
    assert {o["value"] for o in body["paces"]} == {"relaxed", "balanced", "packed"}
    assert body["max_travel_styles"] == 5
    assert "JPY" in body["currencies"]
    keys = [k["key"] for group in body["preference_groups"] for k in group["keys"]]
    assert "food.street_food" in keys
    assert len(keys) == len(set(keys))


async def test_new_user_gets_default_profile(client: AsyncClient) -> None:
    await register(client)

    response = await client.get(PROFILE)

    assert response.status_code == 200
    body = response.json()
    assert body["pace"] == "balanced"
    assert body["walking_tolerance"] == "medium"
    assert body["onboarding_completed"] is False
    assert body["preferences"] == []


async def test_profile_requires_authentication(client: AsyncClient) -> None:
    assert (await client.get(PROFILE)).status_code == 401


async def test_replace_profile_round_trips(client: AsyncClient) -> None:
    await register(client)

    response = await _put(client, VALID_PROFILE)

    assert response.status_code == 200
    stored = (await client.get(PROFILE)).json()
    for field, value in VALID_PROFILE.items():
        assert stored[field] == value


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"travel_styles": ["food", "space_travel"]}, "travel_styles"),
        ({"travel_styles": ["food", "food"]}, "travel_styles"),
        (
            {"travel_styles": ["food", "culture", "nature", "relaxation", "adventure", "shopping"]},
            "travel_styles",
        ),
        ({"pace": "frantic"}, "pace"),
        ({"dietary": ["carnivore"]}, "dietary"),
        ({"walking_tolerance": "none"}, "walking_tolerance"),
    ],
)
async def test_replace_profile_rejects_invalid_values(
    client: AsyncClient, change: dict[str, Any], field: str
) -> None:
    await register(client)

    response = await _put(client, {**VALID_PROFILE, **change})

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"].startswith(field)


async def test_day_must_end_after_it_starts(client: AsyncClient) -> None:
    await register(client)

    response = await _put(client, {**VALID_PROFILE, "day_start": "20:00:00", "day_end": "08:00:00"})

    assert response.status_code == 422


async def test_preferences_upsert_update_and_remove(client: AsyncClient) -> None:
    await register(client)

    first = await _patch_prefs(
        client,
        {
            "upsert": [
                {"key": "food.street_food", "weight": 1},
                {"key": "style.crowds", "weight": -1},
            ],
            "source": "onboarding",
        },
    )
    assert first.status_code == 200
    assert {(p["key"], p["weight"], p["source"]) for p in first.json()["preferences"]} == {
        ("food.street_food", 1.0, "onboarding"),
        ("style.crowds", -1.0, "onboarding"),
    }

    second = await _patch_prefs(
        client,
        {"upsert": [{"key": "food.street_food", "weight": 0.5}], "remove": ["style.crowds"]},
    )

    assert [(p["key"], p["weight"], p["source"]) for p in second.json()["preferences"]] == [
        ("food.street_food", 0.5, "explicit")
    ]


@pytest.mark.parametrize(
    "body",
    [
        {"upsert": [{"key": "food.unicorn_steak", "weight": 1}]},
        {"upsert": [{"key": "food.cafes", "weight": 1.5}]},
        {"upsert": [{"key": "food.cafes", "weight": 1}, {"key": "food.cafes", "weight": 0.5}]},
        {"upsert": [{"key": "food.cafes", "weight": 1}], "remove": ["food.cafes"]},
        {"remove": ["not.a.key"]},
        {"upsert": [], "source": "inferred"},  # clients can't claim inferred preferences
    ],
)
async def test_preferences_reject_invalid_patches(
    client: AsyncClient, body: dict[str, Any]
) -> None:
    await register(client)

    assert (await _patch_prefs(client, body)).status_code == 422


async def test_complete_onboarding_is_reflected_on_the_user(client: AsyncClient) -> None:
    await register(client)
    assert (await client.get(f"{API}/auth/me")).json()["onboarding_completed"] is False

    response = await client.post(f"{PROFILE}/complete-onboarding", headers=_csrf(client))

    assert response.status_code == 200
    assert response.json()["onboarding_completed"] is True
    assert (await client.get(f"{API}/auth/me")).json()["onboarding_completed"] is True


async def test_profiles_are_isolated_between_users(app: FastAPI, client: AsyncClient) -> None:
    await register(client, "maya@example.com")
    await _put(client, VALID_PROFILE)
    await _patch_prefs(client, {"upsert": [{"key": "food.wine", "weight": 1}]})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as other:
        await register(other, "leo@example.com")
        theirs = (await other.get(PROFILE)).json()

    assert theirs["pace"] == "balanced"
    assert theirs["preferences"] == []


# ---------- account (/me) ----------


async def test_patch_me_updates_only_sent_fields(client: AsyncClient) -> None:
    await register(client, display_name="Maya")

    response = await client.patch(
        f"{API}/me", json={"home_currency": "jpy", "units": "imperial"}, headers=_csrf(client)
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["display_name"], body["home_currency"], body["units"]) == (
        "Maya",
        "JPY",
        "imperial",
    )


@pytest.mark.parametrize(
    "body", [{"home_currency": "XYZ"}, {"units": "furlongs"}, {"display_name": "   "}]
)
async def test_patch_me_validates(client: AsyncClient, body: dict[str, Any]) -> None:
    await register(client)

    response = await client.patch(f"{API}/me", json=body, headers=_csrf(client))

    assert response.status_code == 422


async def test_patch_me_requires_csrf(client: AsyncClient) -> None:
    await register(client)

    response = await client.patch(f"{API}/me", json={"units": "imperial"})

    assert response.status_code == 403
