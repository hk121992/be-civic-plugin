#!/usr/bin/env python3
"""Tests for gen_submission_id.py (W33 §3).

Asserts each submission type yields the right prefix and that the UUID part
matches the server's validation regex. Pure stdlib; run with:

    python3 scripts/test_gen_submission_id.py
    # or: python3 -m unittest scripts.test_gen_submission_id
"""

from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path

# Load the sibling module by path (the scripts dir is not a package).
_SPEC = importlib.util.spec_from_file_location(
    "gen_submission_id", Path(__file__).resolve().parent / "gen_submission_id.py"
)
assert _SPEC and _SPEC.loader
gen_submission_id = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(gen_submission_id)

# The server's validation regex (anchored), per contract §3.
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)

EXPECTED_PREFIX = {
    "issue": "iss",
    "validation": "val",
    "feedback": "fbk",
    "rating": "rat",
}


class TestGenSubmissionId(unittest.TestCase):
    def test_prefix_per_type(self):
        for submission_type, prefix in EXPECTED_PREFIX.items():
            with self.subTest(type=submission_type):
                sid = gen_submission_id.gen_submission_id(submission_type)
                self.assertTrue(
                    sid.startswith(prefix + "_"),
                    f"{sid!r} should start with {prefix + '_'!r}",
                )

    def test_uuid_matches_server_regex(self):
        # Generate many to exercise the random fill and version/variant nibbles.
        for submission_type in EXPECTED_PREFIX:
            prefix = EXPECTED_PREFIX[submission_type]
            for _ in range(500):
                sid = gen_submission_id.gen_submission_id(submission_type)
                uuid_part = sid[len(prefix) + 1 :]
                self.assertRegex(uuid_part, UUID_RE)

    def test_uuid7_version_and_variant_bits(self):
        # Direct check on the raw UUIDv7: version nibble must be 7; the
        # variant high bits must be 0b10 (first hex digit of field 4 in 8..b).
        for _ in range(500):
            u = gen_submission_id.uuid7_hex()
            self.assertRegex(u, UUID_RE)
            self.assertEqual(u[14], "7", f"version nibble must be 7 in {u}")
            self.assertIn(u[19], "89ab", f"variant nibble must be 8-b in {u}")

    def test_timestamp_is_monotonic_ordering_prefix(self):
        # UUIDv7 is time-ordered: the leading 48-bit timestamp means an id
        # minted later sorts >= one minted earlier (string compare on hex).
        import time

        first = gen_submission_id.uuid7_hex()
        time.sleep(0.005)
        second = gen_submission_id.uuid7_hex()
        # Compare only the 48-bit timestamp prefix (first 12 hex chars minus
        # the hyphen at index 8): chars 0-7 + 9-12.
        ts_first = first[0:8] + first[9:13]
        ts_second = second[0:8] + second[9:13]
        self.assertLessEqual(ts_first, ts_second)

    def test_unknown_type_raises(self):
        with self.assertRaises(SystemExit):
            gen_submission_id.gen_submission_id("bogus")


if __name__ == "__main__":
    unittest.main()
