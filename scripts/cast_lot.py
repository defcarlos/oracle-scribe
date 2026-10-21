#!/usr/bin/env python3
"""
Cast or look up a lot from the Sortes Homericae (Homeromanteion, PGM VII. 1-148).

Usage:
  python3 scripts/cast_lot.py                  # Roll 3d6 (auto-rerolls damaged papyrus lacunae)
  python3 scripts/cast_lot.py --roll 4-2-6     # Look up a specific 3d6 roll
  python3 scripts/cast_lot.py --no-reroll      # Do not auto-reroll if landing on a papyrus lacuna
  python3 scripts/cast_lot.py --include-ref    # Include the Homeric book/line citation
  python3 scripts/cast_lot.py --json           # Output raw JSON
"""

import argparse
import json
import re
import secrets
import sys
from pathlib import Path
from typing import Any


RESOURCE_PATH = Path(__file__).resolve().parent.parent / "resources" / "sortes_homericae.json"


def load_lots() -> dict[str, dict[str, Any]]:
    if not RESOURCE_PATH.exists():
        raise FileNotFoundError(f"Oracle table not found at {RESOURCE_PATH}")
    with RESOURCE_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data["lots"]


def roll_3d6() -> str:
    d1 = secrets.randbelow(6) + 1
    d2 = secrets.randbelow(6) + 1
    d3 = secrets.randbelow(6) + 1
    return f"{d1}-{d2}-{d3}"


def normalize_roll(raw: str) -> str:
    digits = re.findall(r"[1-6]", raw)
    if len(digits) != 3:
        raise ValueError(
            f"Invalid roll '{raw}'. Must consist of three dice values between 1 and 6 (e.g., '3-4-2')."
        )
    return f"{digits[0]}-{digits[1]}-{digits[2]}"


def cast_or_lookup(
    lots: dict[str, dict[str, Any]],
    specific_roll: str | None = None,
    auto_reroll: bool = True,
    include_ref: bool = False,
) -> dict[str, Any]:
    lacuna_rolls: list[str] = []

    if specific_roll is not None:
        roll_key = normalize_roll(specific_roll)
        entry = lots[roll_key]
        if entry["is_lacuna"] and auto_reroll:
            lacuna_rolls.append(roll_key)
            while entry["is_lacuna"]:
                roll_key = roll_3d6()
                entry = lots[roll_key]
                if entry["is_lacuna"]:
                    lacuna_rolls.append(roll_key)
    else:
        while True:
            roll_key = roll_3d6()
            entry = lots[roll_key]
            if entry["is_lacuna"] and auto_reroll:
                lacuna_rolls.append(roll_key)
                continue
            break

    result: dict[str, Any] = {
        "line": entry["line"],
        "roll": entry["roll"],
        "utterance": entry["lot"],
        "is_lacuna": entry["is_lacuna"],
    }
    if lacuna_rolls:
        result["lacuna_rerolls"] = lacuna_rolls
    if include_ref:
        result["reference"] = entry["reference"]

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cast 3d6 or look up a roll in the Sortes Homericae (Homeromanteion)."
    )
    parser.add_argument(
        "--roll",
        type=str,
        default=None,
        help="Specific 3d6 roll to look up (e.g. '4-2-6' or '426'). If omitted, rolls 3d6 randomly.",
    )
    parser.add_argument(
        "--no-reroll",
        action="store_true",
        help="Do not automatically re-roll if the dice land on a missing papyrus fragment (lacuna).",
    )
    parser.add_argument(
        "--include-ref",
        action="store_true",
        help="Include the Iliad/Odyssey citation (omitted by default to avoid plot trivia).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Format output as JSON.",
    )

    args = parser.parse_args()

    try:
        lots = load_lots()
        result = cast_or_lookup(
            lots=lots,
            specific_roll=args.roll,
            auto_reroll=not args.no_reroll,
            include_ref=args.include_ref,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result.get("lacuna_rerolls"):
            rerolls = ", ".join(result["lacuna_rerolls"])
            print(f"Note: Initial roll(s) [{rerolls}] fell upon damaged papyrus (lacuna) and were re-cast.")
        print(f"Roll: {result['roll']} (Line {result['line']})")
        if result["is_lacuna"]:
            print("Utterance: [Lacuna — the papyrus fragment for this roll is lost]")
        else:
            print(f"Utterance: \"{result['utterance']}\"")
        if args.include_ref and result.get("reference"):
            print(f"Reference: {result['reference']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
