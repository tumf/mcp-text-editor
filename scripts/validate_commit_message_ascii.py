#!/usr/bin/env python3
"""Pre-commit commit-msg hook to enforce ASCII-only commit messages.

This hook fails if any non-ASCII character exists in the commit message.
"""

from __future__ import annotations

import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("commit-msg hook: missing commit message file path", file=sys.stderr)
        return 2

    commit_msg_path = sys.argv[1]
    message = open(commit_msg_path, "r", encoding="utf-8").read()

    non_ascii_chars = [ch for ch in message if ord(ch) > 127]
    if non_ascii_chars:
        sample = "".join(sorted(set(non_ascii_chars))[:10])
        print("Non-ASCII characters detected in commit message.", file=sys.stderr)
        print("Please use English-only ASCII characters.", file=sys.stderr)
        print(f"Offending characters (sample): {sample!r}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
