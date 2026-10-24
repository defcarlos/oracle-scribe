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

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
import re
import secrets
import sys
from typing import Any, Final, TypedDict

DICE_COUNT: Final[int] = 3
DICE_SIDES: Final[int] = 6
RESOURCE_PATH: Final[Path] = (
    Path(__file__).resolve().parent.parent / "resources" / "sortes_homericae.json"
)
ROLL_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^\s*([1-6])(?:[\s,:-]+([1-6])[\s,:-]+([1-6])|([1-6])([1-6]))\s*$"
)


class LotEntry(TypedDict):
    """Schema for a single Sortes Homericae entry in sortes_homericae.json."""

    line: int
    roll: str
    lot: str | None
    reference: str | None
    is_lacuna: bool


@dataclass(frozen=True, slots=True)
class CastResult:
    """Immutable result of casting or looking up a 3d6 lot."""

    line: int
    roll: str
    utterance: str | None
    is_lacuna: bool
    reference: str | None = None
    lacuna_rerolls: tuple[str, ...] = ()

    def to_dict(self, *, include_ref: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "line": self.line,
            "roll": self.roll,
            "utterance": self.utterance,
            "is_lacuna": self.is_lacuna,
        }
        if self.lacuna_rerolls:
            payload["lacuna_rerolls"] = list(self.lacuna_rerolls)
        if include_ref:
            payload["reference"] = self.reference
        return payload


def load_lots(resource_path: Path = RESOURCE_PATH) -> dict[str, LotEntry]:
    """Load the 216 Sortes Homericae lots from the local JSON resource."""
    if not resource_path.is_file():
        raise FileNotFoundError(f"Oracle table not found at {resource_path}")
    data = json.loads(resource_path.read_text(encoding="utf-8"))
    lots = data.get("lots")
    if not isinstance(lots, dict):
        raise ValueError(f"Malformed oracle table in {resource_path}: missing 'lots' mapping.")
    return lots


def roll_3d6() -> str:
    """Roll three 6-sided dice using cryptographically strong randomness."""
    return "-".join(str(secrets.randbelow(DICE_SIDES) + 1) for _ in range(DICE_COUNT))


def normalize_roll(raw: str) -> str:
    """Validate and normalize a 3d6 string (e.g. '4-2-6', '4,2,6', or '426') to 'd1-d2-d3'."""
    match = ROLL_PATTERN.match(raw)
    if not match:
        raise ValueError(
            f"Invalid roll '{raw}'. Must consist of exactly three dice values "
            "between 1 and 6 (e.g., '4-2-6', '4,2,6', or '426')."
        )
    d1 = match.group(1)
    d2 = match.group(2) or match.group(4)
    d3 = match.group(3) or match.group(5)
    return f"{d1}-{d2}-{d3}"


def cast_or_lookup(
    lots: Mapping[str, LotEntry],
    specific_roll: str | None = None,
    *,
    auto_reroll: bool = True,
    include_ref: bool = False,
) -> CastResult:
    """Cast 3d6 or look up a specific roll, optionally re-rolling damaged papyrus lacunae."""
    if auto_reroll and not any(not entry["is_lacuna"] for entry in lots.values()):
        raise ValueError("Cannot auto-reroll: all entries in the oracle table are marked as lacunae.")

    roll_key = normalize_roll(specific_roll) if specific_roll is not None else roll_3d6()
    if roll_key not in lots:
        raise KeyError(f"Roll '{roll_key}' not found in oracle table.")

    lacuna_rolls: list[str] = []
    while lots[roll_key]["is_lacuna"] and auto_reroll:
        lacuna_rolls.append(roll_key)
        roll_key = roll_3d6()

    entry = lots[roll_key]
    return CastResult(
        line=entry["line"],
        roll=entry["roll"],
        utterance=entry["lot"],
        is_lacuna=entry["is_lacuna"],
        reference=entry["reference"] if include_ref else None,
        lacuna_rerolls=tuple(lacuna_rolls),
    )


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""
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
    return parser


def format_text_output(result: CastResult, *, include_ref: bool = False) -> str:
    """Format a CastResult for human/agent CLI consumption."""
    lines: list[str] = []
    if result.lacuna_rerolls:
        rerolls = ", ".join(result.lacuna_rerolls)
        lines.append(
            f"Note: Initial roll(s) [{rerolls}] fell upon damaged papyrus (lacuna) and were re-cast."
        )
    lines.append(f"Roll: {result.roll} (Line {result.line})")
    if result.is_lacuna:
        lines.append("Utterance: [Lacuna — the papyrus fragment for this roll is lost]")
    else:
        lines.append(f'Utterance: "{result.utterance}"')
    if include_ref and result.reference:
        lines.append(f"Reference: {result.reference}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    args = build_parser().parse_args(argv)

    try:
        lots = load_lots()
        result = cast_or_lookup(
            lots=lots,
            specific_roll=args.roll,
            auto_reroll=not args.no_reroll,
            include_ref=args.include_ref,
        )
    except (ValueError, KeyError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result.to_dict(include_ref=args.include_ref), indent=2, ensure_ascii=False))
    else:
        print(format_text_output(result, include_ref=args.include_ref))

    return 0


if __name__ == "__main__":
    sys.exit(main())
