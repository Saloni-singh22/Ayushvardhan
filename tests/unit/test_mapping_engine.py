import pytest

from app.services.mapping_engine import (
    MappingCandidate,
    MappingEngine,
    MappingTier,
    NamasteTerm,
    SEMANTIC_SYSTEM_URI,
    TM2_SYSTEM_URI,
)


def build_engine() -> MappingEngine:
    return MappingEngine(db=None)


def test_score_candidate_assigns_tm2_tier():
    engine = build_engine()
    term = NamasteTerm(
        code="AYU-001",
        display="Vata dosha imbalance",
        definition="Vata dosha imbalance affecting bodily functions",
        synonyms=["Vata imbalance"],
        categories=["dosha"],
    )
    candidate = MappingCandidate(
        source_code=term.code,
        source_display=term.display,
        source_system=term.system_url,
        target_code="XK7G.0",
        target_display="Vata dosha imbalance",
        target_definition="Vata dosha imbalance affecting bodily functions",
        target_system=TM2_SYSTEM_URI,
    )

    engine._score_candidate(term, candidate, validation_scores={})

    assert candidate.tier == MappingTier.DIRECT_TM2
    assert candidate.aggregate_score >= 0.7


def test_semantic_bridge_matches_keyword():
    engine = build_engine()
    term = NamasteTerm(
        code="AYU-099",
        display="Ama accumulation disorder",
    )

    results = engine._semantic_bridges(term)
    assert results
    assert any(candidate.target_system == SEMANTIC_SYSTEM_URI for candidate in results)


def test_deduplicate_candidates_limits_results():
    engine = build_engine()
    term = NamasteTerm(code="AYU-100", display="Test term")
    candidates = [
        MappingCandidate(
            source_code=term.code,
            source_display=term.display,
            source_system=term.system_url,
            target_code=f"CODE-{i}",
            target_display="Display",
            target_system=TM2_SYSTEM_URI,
        )
        for i in range(20)
    ]

    unique = engine._deduplicate_candidates(candidates)
    assert len(unique) == engine._max_candidates_per_term


@pytest.mark.parametrize(
    "display,expected_terms",
    [
        ("Prameha diabetes", 2),
        ("Simple term", 1),
    ],
)
def test_build_search_terms_deduplicates(display: str, expected_terms: int):
    engine = build_engine()
    term = NamasteTerm(
        code="AYU-200",
        display=display,
        definition="Prameha metabolic disorder",
        synonyms=["Prameha diabetes"],
        categories=["metabolic"],
    )

    terms = engine._build_search_terms(term)
    assert len(terms) >= expected_terms
    assert len(terms) == len(set(t.lower() for t in terms))


def test_build_search_terms_handles_diacritics():
    engine = build_engine()
    term = NamasteTerm(
        code="AYU-300",
        display="doShAvasthA (vAta)",
        synonyms=[],
        categories=["dosha"],
    )

    terms = engine._build_search_terms(term)
    lowered = [t.lower() for t in terms]
    assert any("vata" in value for value in lowered)
    assert "traditional medicine" in lowered
