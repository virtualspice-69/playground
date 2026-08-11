"""Loads the pre-made art/meme library (the 250+ pieces you drop into
assets/templates/) from a manifest.json index, rebuilding it if missing or
if new files are found that aren't in it yet.

Folder layout example:

    assets/templates/
        memes/            <- static meme templates for /meme text overlay
            template1.jpg
            template2.png
        gallery/           <- finished art/animations for /random and /gif
            piece1.png
            piece2.gif
        ...any other subfolder name becomes a "category"
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import asdict, dataclass

import config

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
ANIMATION_EXTS = {".gif", ".mp4", ".webm", ".mov"}


@dataclass
class Asset:
    rel_path: str
    kind: str  # "image" or "animation"
    category: str

    @property
    def abs_path(self) -> str:
        return os.path.join(config.ASSETS_DIR, self.rel_path)


def _classify(ext: str) -> str | None:
    ext = ext.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in ANIMATION_EXTS:
        return "animation"
    return None


def scan_assets() -> list[Asset]:
    assets: list[Asset] = []
    if not os.path.isdir(config.ASSETS_DIR):
        return assets

    for root, _dirs, files in os.walk(config.ASSETS_DIR):
        for fname in files:
            if fname == "manifest.json" or fname.startswith("."):
                continue
            ext = os.path.splitext(fname)[1]
            kind = _classify(ext)
            if not kind:
                continue
            abs_path = os.path.join(root, fname)
            rel_path = os.path.relpath(abs_path, config.ASSETS_DIR)
            category = os.path.relpath(root, config.ASSETS_DIR)
            category = "general" if category == "." else category.split(os.sep)[0]
            assets.append(Asset(rel_path=rel_path, kind=kind, category=category))

    return sorted(assets, key=lambda a: a.rel_path)


def rebuild_manifest() -> list[Asset]:
    assets = scan_assets()
    os.makedirs(config.ASSETS_DIR, exist_ok=True)
    with open(config.MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump([asdict(a) for a in assets], f, indent=2)
    return assets


def load_manifest(auto_rebuild: bool = True) -> list[Asset]:
    if not os.path.exists(config.MANIFEST_PATH):
        if auto_rebuild:
            return rebuild_manifest()
        return []
    with open(config.MANIFEST_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    assets = [Asset(**entry) for entry in raw]

    if auto_rebuild:
        on_disk = {a.rel_path for a in scan_assets()}
        known = {a.rel_path for a in assets}
        if on_disk != known:
            return rebuild_manifest()

    return assets


def random_asset(kind: str | None = None, category: str | None = None) -> Asset | None:
    assets = load_manifest()
    if kind:
        assets = [a for a in assets if a.kind == kind]
    if category:
        assets = [a for a in assets if a.category == category]
    return random.choice(assets) if assets else None


def categories() -> list[str]:
    assets = load_manifest()
    return sorted({a.category for a in assets})
