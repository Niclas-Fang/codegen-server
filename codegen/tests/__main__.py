"""Run all test suites."""

import sys
from tests.runner import Outcome
from tests.test_connection import TestConnection
from tests.test_models import TestModels
from tests.test_fim import TestFIM
from tests.test_chat import TestChat
from tests.test_rag import TestRAG
from tests.test_boundary import TestBoundary


SUITES = [
    ("connection", TestConnection),
    ("models", TestModels),
    ("fim", TestFIM),
    ("chat", TestChat),
    ("rag", TestRAG),
    ("boundary", TestBoundary),
]

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        for name, cls in SUITES:
            print(f"\n[{name}]")
            t = cls()
            t.list_tests()
        sys.exit(0)

    all_results = []
    total_fail = 0

    for name, cls in SUITES:
        print(f"\n{'─'*60}\n  Suite: {name}\n{'─'*60}")
        t = cls()
        t.run_all()
        all_results.extend(t.results)
        fails = sum(1 for r in t.results if r.actual not in (Outcome.PASS, Outcome.SKIP))
        total_fail += fails

    print(f"\n{'='*64}")
    print(f"TOTAL: {len(all_results)} tests, {total_fail} failures")
    sys.exit(1 if total_fail else 0)
