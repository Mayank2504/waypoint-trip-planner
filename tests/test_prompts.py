from waypoint.agent.prompts import plan_prompt, refine_prompt, regen_day_prompt


def test_plan_prompt_fast_and_full_rules():
    common = dict(
        city="Paris",
        days=3,
        pace="balanced",
        interests=["art"],
        constraints="none",
        notes="",
        radius_km=5,
        poi_limit=40,
    )
    assert "Call search_pois ONCE" in plan_prompt(**common, fast_mode=True)
    assert "at least 2 times" in plan_prompt(**common, fast_mode=False)


def test_refine_and_regen_prompts_preserve_contract():
    itinerary = {"city": "Paris", "days": [{"day": 1}]}
    assert "Existing JSON" in refine_prompt(
        itin=itinerary, request="more art", fast_mode=True
    )
    regen = regen_day_prompt(
        itin=itinerary, target_day=1, request="new morning", fast_mode=True
    )
    assert "ONLY modify" in regen
    assert "All other days must remain EXACTLY unchanged" in regen
