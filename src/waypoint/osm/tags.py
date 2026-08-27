"""Interest → OpenStreetMap tag mapping."""
from __future__ import annotations

from typing import Dict, List, Tuple

TagPair = Tuple[str, str]

INTEREST_TO_TAGS: Dict[str, List[TagPair]] = {
    "outdoors": [
        ("leisure", "park|nature_reserve|garden"),
        ("tourism", "viewpoint"),
        ("natural", "peak|wood|spring|beach|cave_entrance"),
    ],
    "museums": [("tourism", "museum|gallery")],
    "food": [("amenity", "restaurant|cafe|fast_food")],
    "coffee": [("amenity", "cafe")],
    "history": [("historic", "monument|memorial|castle|ruins"), ("tourism", "attraction")],
    "art": [("tourism", "gallery|museum")],
    "nightlife": [("amenity", "bar|pub|nightclub")],
    "scenic": [("tourism", "viewpoint"), ("natural", "peak")],
    "family": [("tourism", "zoo|theme_park"), ("leisure", "playground")],
    "shopping": [("shop", "mall|clothes|gift"), ("amenity", "marketplace")],
}

DEFAULT_TAGS: List[TagPair] = [
    ("tourism", "museum|attraction|viewpoint"),
    ("leisure", "park|garden|nature_reserve"),
    ("amenity", "cafe|restaurant"),
    ("historic", "monument|memorial|castle"),
]

ALL_INTERESTS = list(INTEREST_TO_TAGS.keys())


def merge_tag_filters(pairs: List[TagPair]) -> Dict[str, str]:
    merged: Dict[str, List[str]] = {}
    for k, v in pairs:
        merged.setdefault(k, []).append(v)
    return {k: "|".join(vs) for k, vs in merged.items()}


def tags_for_interests(interests: List[str]) -> Dict[str, str]:
    pairs: List[TagPair] = []
    for intr in interests:
        pairs.extend(INTEREST_TO_TAGS.get(intr, []))
    if not pairs:
        pairs = DEFAULT_TAGS
    return merge_tag_filters(pairs)
