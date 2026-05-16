#!/usr/bin/env python3
"""scan-pending-state.py.

Scan for deferred customer state per harness-spec §H.3:
  - observation_buffer (unsubmitted observation items)
  - research_notes (status: ready_to_draft)
  - staged_submission (status: ready_to_submit)
  - path_traversal_state (paused mid-traversal)

Emit PENDING_STATE: none if empty, else write items to a JSON file and emit
its path. CLAUDE.md surfaces items at session-start before opening framing.

Status: PLACEHOLDER. Authoring per design doc step 5.

Output schema:
  PENDING_STATE: none | <absolute file path>

Runtime: Python 3 stdlib only (pathlib, json).
"""

import sys


def main() -> int:
    print("PENDING_STATE: none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
