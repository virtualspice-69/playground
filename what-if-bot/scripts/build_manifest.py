#!/usr/bin/env python3
"""Rescan assets/templates/ and regenerate manifest.json.

Run this after dropping new art/meme files into assets/templates/ (the bot
also auto-detects new files at runtime, but this is handy for a quick
sanity check on how many pieces are indexed and in which categories).

Usage:
    python scripts/build_manifest.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import library  # noqa: E402


def main() -> None:
    assets = library.rebuild_manifest()
    by_category: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    for a in assets:
        by_category[a.category] = by_category.get(a.category, 0) + 1
        by_kind[a.kind] = by_kind.get(a.kind, 0) + 1

    print(f"Indexed {len(assets)} assets from assets/templates/")
    print("\nBy category:")
    for cat, count in sorted(by_category.items()):
        print(f"  {cat}: {count}")
    print("\nBy kind:")
    for kind, count in sorted(by_kind.items()):
        print(f"  {kind}: {count}")

    if not assets:
        print(
            "\nNo art found yet. Drop images/GIFs into assets/templates/<category>/ "
            "and rerun this script."
        )


if __name__ == "__main__":
    main()
