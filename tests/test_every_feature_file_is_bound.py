"""
Guard: no .feature file can be silently uncollected (FS-55 acceptance criterion).

pytest-bdd only runs a feature file that some test module binds with a
scenarios(...) or scenario(...) call. A feature file nobody binds is never
executed, and nothing fails to say so. This test fails if that happens.
"""
from __future__ import annotations

import re
from pathlib import Path

TESTS = Path(__file__).parent
FEATURES = sorted((TESTS / "features").glob("*.feature"))

# scenarios("../features/x.feature") or scenario("../features/x.feature", "name"),
# including calls split over several lines.
_BINDING = re.compile(r"""\bscenarios?\(\s*["']([^"']+\.feature)["']""")


def _bound_feature_names() -> set[str]:
    bound: set[str] = set()
    for module in TESTS.rglob("*.py"):
        if module.name == Path(__file__).name:
            continue
        for path in _BINDING.findall(module.read_text(encoding="utf-8")):
            bound.add(Path(path).name)
    return bound


def test_there_are_feature_files_to_check():
    assert FEATURES, "tests/features contains no .feature files; the guard is checking nothing"


def test_every_feature_file_is_bound_by_a_scenarios_call():
    bound = _bound_feature_names()
    unbound = [f.name for f in FEATURES if f.name not in bound]
    assert not unbound, f"feature files no test module binds, so they never run: {unbound}"


def test_every_bound_feature_file_exists():
    existing = {f.name for f in FEATURES}
    missing = sorted(_bound_feature_names() - existing)
    assert not missing, f"scenarios() calls point at feature files that do not exist: {missing}"
