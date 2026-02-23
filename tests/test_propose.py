from ai_etl.propose import build_unified_diff, extract_proposed_rulebook


def test_extract_proposed_rulebook():
    text = """# Title\n\n## Proposed Rulebook\nRule A\nRule B\n\n## Rationale\nBecause."""
    proposed = extract_proposed_rulebook(text)
    assert proposed == "Rule A\nRule B"


def test_build_unified_diff():
    original = "Rule A\nRule B\n"
    proposed = "Rule A\nRule C\n"
    diff = build_unified_diff(original, proposed)
    assert "-Rule B" in diff
    assert "+Rule C" in diff
