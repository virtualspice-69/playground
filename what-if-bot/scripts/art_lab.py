#!/usr/bin/env python3
"""$IF art lab — generate batches of character art, rate them, and use the
ratings to tighten the prompt over time.

This runs on YOUR machine (it needs outbound internet to the image API).
Workflow:

    # 1. Generate a batch of variations across all preset scenes
    python scripts/art_lab.py generate --count 2

    # 2. Look at them in art_lab_output/, then rate the ones worth judging
    python scripts/art_lab.py rate 0003 good "jaw and eyes are perfect"
    python scripts/art_lab.py rate 0004 bad "skin went matte, lost the sheen"

    # 3. See what's working — the ratings accumulate in art_lab_ratings.json
    python scripts/art_lab.py report

    # Try a one-off idea without touching the presets:
    python scripts/art_lab.py generate --scene "crashing through a bank vault door" --count 4

    # Lock in a look: reuse the exact seed of a render you loved
    python scripts/art_lab.py generate --scene-key throne --seed 812345 --count 1

Every image is saved alongside the exact prompt + seed that produced it, so a
result you like is always reproducible.
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from services import image_gen  # noqa: E402

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "art_lab_output")
RATINGS_PATH = os.path.join(OUTPUT_DIR, "ratings.json")


def _load_ratings() -> dict:
    if not os.path.exists(RATINGS_PATH):
        return {}
    with open(RATINGS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_ratings(data: dict) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(RATINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _next_index() -> int:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    existing = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".jpg")]
    if not existing:
        return 1
    nums = [int(f.split("_")[0]) for f in existing if f.split("_")[0].isdigit()]
    return max(nums, default=0) + 1


async def _generate_one(index: int, label: str, scene: str, seed: int | None, size: tuple[int, int]) -> None:
    prompt = image_gen.build_character_prompt(scene)
    width, height = size

    if seed is None:
        import random

        seed = random.randint(0, 2**31 - 1)

    stem = f"{index:04d}_{label}"
    print(f"  generating {stem} (seed {seed})...", flush=True)

    try:
        data = await image_gen.generate_image(prompt, width=width, height=height, seed=seed)
    except Exception as exc:
        print(f"  !! {stem} failed: {exc}")
        return

    img_path = os.path.join(OUTPUT_DIR, f"{stem}.jpg")
    with open(img_path, "wb") as f:
        f.write(data)

    meta = {
        "index": f"{index:04d}",
        "label": label,
        "scene": scene,
        "seed": seed,
        "size": [width, height],
        "prompt": prompt,
        "character_prompt": config.CHARACTER_PROMPT,
        "model": config.IMAGE_GEN_MODEL,
        "created": datetime.now().isoformat(timespec="seconds"),
        "url": image_gen.build_url(prompt, width=width, height=height, seed=seed),
    }
    with open(os.path.join(OUTPUT_DIR, f"{stem}.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"  saved {img_path}")


async def cmd_generate(args: argparse.Namespace) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if args.scene:
        jobs = [("custom", args.scene)]
    elif args.scene_key:
        scene = image_gen.PRESET_SCENES.get(args.scene_key)
        if not scene:
            print(f"Unknown scene key. Options: {', '.join(image_gen.PRESET_SCENES)}")
            return
        jobs = [(args.scene_key, scene)]
    else:
        jobs = list(image_gen.PRESET_SCENES.items())

    size = (args.width, args.height)
    index = _next_index()

    print(f"Generating {len(jobs) * args.count} image(s) into {OUTPUT_DIR}\n")

    tasks = []
    for label, scene in jobs:
        for _ in range(args.count):
            tasks.append(_generate_one(index, label, scene, args.seed, size))
            index += 1

    # A few at a time — the free tier throttles aggressive parallelism.
    batch_size = 3
    for i in range(0, len(tasks), batch_size):
        await asyncio.gather(*tasks[i : i + batch_size])

    print(f"\nDone. Open {OUTPUT_DIR} and rate what you see:")
    print("  python scripts/art_lab.py rate <index> good|bad \"why\"")


def cmd_rate(args: argparse.Namespace) -> None:
    ratings = _load_ratings()
    key = args.index.zfill(4)

    matches = [f for f in os.listdir(OUTPUT_DIR) if f.startswith(key) and f.endswith(".jpg")] if os.path.isdir(OUTPUT_DIR) else []
    if not matches:
        print(f"No image found with index {key}. Run 'generate' first.")
        return

    ratings[key] = {
        "verdict": args.verdict,
        "note": args.note or "",
        "file": matches[0],
        "rated": datetime.now().isoformat(timespec="seconds"),
    }
    _save_ratings(ratings)
    print(f"Recorded {key} as {args.verdict}: {args.note or '(no note)'}")


SHEET_CSS = """
* { box-sizing: border-box; }
body { margin: 0; padding: 32px; background: #0a0f0a; color: #e8ffe8;
       font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
h1 { margin: 0 0 4px; font-size: 24px; color: #6cff6c; letter-spacing: -0.02em; }
p.sub { margin: 0 0 28px; color: #7a9a7a; font-size: 14px; }
.grid { display: grid; gap: 20px;
        grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); }
figure { margin: 0; background: #111a11; border: 1px solid #1f331f;
         border-radius: 10px; overflow: hidden; }
figure img { width: 100%; aspect-ratio: 1; object-fit: cover; display: block;
             background: #0d150d; }
figcaption { padding: 10px 12px; font-size: 13px; display: flex;
             justify-content: space-between; align-items: center; }
.name { color: #6cff6c; font-weight: 600; }
.seed { color: #5f7f5f; font-family: ui-monospace, monospace; font-size: 11px; }
"""


def cmd_sheet(args: argparse.Namespace) -> None:
    """Builds an HTML contact sheet that loads variations live in the browser.

    Nothing is downloaded — each tile points straight at the generation URL,
    so opening the file renders a fresh batch. Reload for new variations."""
    if args.scene:
        jobs = [("custom", args.scene)]
    else:
        jobs = list(image_gen.PRESET_SCENES.items())

    tiles = []
    seed_base = args.seed if args.seed is not None else 1000
    n = 0
    for label, scene in jobs:
        for variant in range(args.count):
            seed = seed_base + n
            prompt = image_gen.build_character_prompt(scene)
            url = image_gen.build_url(prompt, width=args.width, height=args.height, seed=seed)
            tiles.append(
                f'<figure><img loading="lazy" src="{url}" alt="{label}">'
                f'<figcaption><span class="name">{label}</span>'
                f'<span class="seed">seed {seed}</span></figcaption></figure>'
            )
            n += 1

    html = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>$IF — art contact sheet</title>"
        f"<style>{SHEET_CSS}</style></head><body>"
        "<h1>$IF — character variations</h1>"
        f"<p class='sub'>{n} renders · model: {config.IMAGE_GEN_MODEL} · "
        "images generate on load, give it a moment. Reload for a fresh batch.</p>"
        f"<div class='grid'>{''.join(tiles)}</div>"
        "</body></html>"
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, "contact_sheet.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Wrote {out_path} ({n} tiles)")
    print("Open it in your browser to see the batch.")


def cmd_report(args: argparse.Namespace) -> None:
    ratings = _load_ratings()
    if not ratings:
        print("No ratings yet. Generate a batch, then rate a few.")
        return

    good = {k: v for k, v in ratings.items() if v["verdict"] == "good"}
    bad = {k: v for k, v in ratings.items() if v["verdict"] == "bad"}

    print(f"Rated {len(ratings)} images — {len(good)} good, {len(bad)} bad\n")

    def _dump(title: str, group: dict) -> None:
        if not group:
            return
        print(f"{title}:")
        for key, val in sorted(group.items()):
            meta_path = os.path.join(OUTPUT_DIR, val["file"].replace(".jpg", ".json"))
            seed = scene = "?"
            if os.path.exists(meta_path):
                with open(meta_path, encoding="utf-8") as f:
                    meta = json.load(f)
                seed, scene = meta["seed"], meta["label"]
            print(f"  {key} [{scene}] seed={seed} — {val['note']}")
        print()

    _dump("GOOD", good)
    _dump("BAD", bad)

    print(
        "Feed this report back to Claude and it can tighten CHARACTER_PROMPT / "
        "NEGATIVE_PROMPT in config.py based on what consistently works."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="$IF character art lab")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="generate a batch of variations")
    gen.add_argument("--count", type=int, default=1, help="images per scene (default 1)")
    gen.add_argument("--scene", help="freeform scene description (overrides presets)")
    gen.add_argument("--scene-key", help="a single preset scene key, e.g. throne")
    gen.add_argument("--seed", type=int, help="fixed seed, to reproduce or vary one render")
    gen.add_argument("--width", type=int, default=1024)
    gen.add_argument("--height", type=int, default=1024)

    rate = sub.add_parser("rate", help="record your verdict on a generated image")
    rate.add_argument("index", help="the 4-digit index, e.g. 0003")
    rate.add_argument("verdict", choices=["good", "bad"])
    rate.add_argument("note", nargs="?", help="what worked or what broke")

    sheet = sub.add_parser("sheet", help="build an HTML contact sheet of live variations")
    sheet.add_argument("--count", type=int, default=2, help="variants per scene (default 2)")
    sheet.add_argument("--scene", help="freeform scene description (overrides presets)")
    sheet.add_argument("--seed", type=int, help="starting seed (default 1000)")
    sheet.add_argument("--width", type=int, default=1024)
    sheet.add_argument("--height", type=int, default=1024)

    sub.add_parser("report", help="summarize all ratings so far")

    args = parser.parse_args()

    if args.command == "generate":
        asyncio.run(cmd_generate(args))
    elif args.command == "rate":
        cmd_rate(args)
    elif args.command == "sheet":
        cmd_sheet(args)
    elif args.command == "report":
        cmd_report(args)


if __name__ == "__main__":
    main()
