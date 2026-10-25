#!/usr/bin/env python3
"""
Cast or look up a lot from the Sortes Homericae (Homeromanteion, PGM VII. 1-148)
with support for Homeric Greek hexameters, root-word lexicon, whispered lacuna
fragments, and PGM VII. 155-167 Hemeralogia ("Days and Hours for Divination").

Usage:
  python3 scripts/cast_lot.py                    # Roll 3d6 (auto-rerolls damaged papyrus lacunae)
  python3 scripts/cast_lot.py --roll 4-2-6       # Look up a specific 3d6 roll
  python3 scripts/cast_lot.py --check-hour       # Evaluate PGM VII Days & Hours timing alongside the cast
  python3 scripts/cast_lot.py --no-reroll        # Do not auto-reroll if landing on a papyrus lacuna
  python3 scripts/cast_lot.py --include-ref      # Include the Homeric book/line citation
  python3 scripts/cast_lot.py --json             # Output raw JSON
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
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


class LexiconItem(TypedDict):
    """A single Greek root/symbolic term and its literal meaning."""

    term: str
    meaning: str


class LacunaFragment(TypedDict):
    """Papyrological trace and shadow omen for a damaged line."""

    greek_fragment: str
    whisper: str
    apparatus: str


class LotEntry(TypedDict):
    """Schema for a single Sortes Homericae entry in sortes_homericae.json."""

    line: int
    roll: str
    lot: str | None
    greek: str | None
    lexicon: list[LexiconItem]
    fragment: LacunaFragment | None
    reference: str | None
    is_lacuna: bool


@dataclass(frozen=True, slots=True)
class ShadowOmen:
    """Surviving papyrus trace from a lacuna encountered prior to or during casting."""

    roll: str
    line: int
    greek_fragment: str
    whisper: str
    apparatus: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "roll": self.roll,
            "line": self.line,
            "greek_fragment": self.greek_fragment,
            "whisper": self.whisper,
            "apparatus": self.apparatus,
        }


@dataclass(frozen=True, slots=True)
class HourEvaluation:
    """Evaluation of the consultation time against PGM VII. 155-167 (Hemeralogia)."""

    day_of_month: int
    hour_24: int
    time_of_day: str
    prescribed_window_key: str
    prescribed_greek: str
    prescribed_label: str
    status: str  # "Propitious", "Cautionary (Off-Hour)", or "Forbidden Day (Apophras)"
    counsel: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "day_of_month": self.day_of_month,
            "hour_24": self.hour_24,
            "time_of_day": self.time_of_day,
            "prescribed_window": self.prescribed_label,
            "prescribed_greek": self.prescribed_greek,
            "status": self.status,
            "counsel": self.counsel,
        }


@dataclass(frozen=True, slots=True)
class CastResult:
    """Immutable result of casting or looking up a 3d6 lot."""

    line: int
    roll: str
    utterance: str | None
    greek: str | None
    lexicon: tuple[LexiconItem, ...]
    is_lacuna: bool
    fragment: LacunaFragment | None = None
    reference: str | None = None
    lacuna_rerolls: tuple[str, ...] = ()
    shadow_omens: tuple[ShadowOmen, ...] = ()
    hour_evaluation: HourEvaluation | None = None

    def to_dict(self, *, include_ref: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "line": self.line,
            "roll": self.roll,
            "utterance": self.utterance,
            "greek": self.greek,
            "lexicon": list(self.lexicon),
            "is_lacuna": self.is_lacuna,
        }
        if self.fragment is not None:
            payload["fragment"] = dict(self.fragment)
        if self.lacuna_rerolls:
            payload["lacuna_rerolls"] = list(self.lacuna_rerolls)
        if self.shadow_omens:
            payload["shadow_omens"] = [omen.to_dict() for omen in self.shadow_omens]
        if self.hour_evaluation is not None:
            payload["hemeralogia"] = self.hour_evaluation.to_dict()
        if include_ref:
            payload["reference"] = self.reference
        return payload


def load_oracle_data(resource_path: Path = RESOURCE_PATH) -> dict[str, Any]:
    """Load the full Sortes Homericae JSON resource."""
    if not resource_path.is_file():
        raise FileNotFoundError(f"Oracle table not found at {resource_path}")
    data = json.loads(resource_path.read_text(encoding="utf-8"))
    if not isinstance(data.get("lots"), dict):
        raise ValueError(f"Malformed oracle table in {resource_path}: missing 'lots' mapping.")
    return data


def load_lots(resource_path: Path = RESOURCE_PATH) -> dict[str, LotEntry]:
    """Load the 216 Sortes Homericae lots from the local JSON resource."""
    return load_oracle_data(resource_path)["lots"]


def classify_time_of_day(hour_24: int) -> str:
    """Classify a 24-hour clock value into ancient consultation periods."""
    if 5 <= hour_24 <= 10:
        return "dawn"
    if 11 <= hour_24 <= 13:
        return "noon"
    if 14 <= hour_24 <= 18:
        return "afternoon"
    if 19 <= hour_24 <= 21:
        return "dusk"
    return "deep_night"


def evaluate_hour(
    hemeralogia: Mapping[str, Any],
    *,
    day_of_month: int | None = None,
    hour_24: int | None = None,
) -> HourEvaluation:
    """Evaluate consultation timing according to PGM VII. 155-167."""
    now = datetime.now()
    raw_day = day_of_month if day_of_month is not None else now.day
    if not 1 <= raw_day <= 31:
        raise ValueError(f"Invalid day '{raw_day}'. Must be between 1 and 31.")
    # Map 31st day of modern solar month to day 30 of the 30-day Greco-Egyptian table
    table_day = min(raw_day, 30)

    current_hour = hour_24 if hour_24 is not None else now.hour
    if not 0 <= current_hour <= 23:
        raise ValueError(f"Invalid hour '{current_hour}'. Must be between 0 and 23.")

    days_map = hemeralogia["days"]
    windows_map = hemeralogia["windows"]
    window_key = days_map[str(table_day)]
    window_info = windows_map[window_key]
    period = classify_time_of_day(current_hour)

    if window_key == "do_not_use":
        status = "Forbidden Day (Apophras)"
        counsel = window_info["counsel"]
    elif window_key == "whole_day" and 5 <= current_hour <= 20:
        status = "Propitious"
        counsel = window_info["counsel"]
    elif window_key == period or (
        window_key == "dawn_and_afternoon" and period in ("dawn", "afternoon")
    ):
        status = "Propitious"
        counsel = window_info["counsel"]
    else:
        status = "Cautionary (Off-Hour)"
        counsel = (
            f"Day {table_day} is prescribed for '{window_info['label']}' ({window_info['greek']}), "
            f"whereas the current hour falls in '{period.replace('_', ' ')}'. "
            "Proceed with heightened mindfulness, as the temple doors are only half-parted."
        )

    return HourEvaluation(
        day_of_month=table_day,
        hour_24=current_hour,
        time_of_day=period.replace("_", " "),
        prescribed_window_key=window_key,
        prescribed_greek=window_info["greek"],
        prescribed_label=window_info["label"],
        status=status,
        counsel=counsel,
    )


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


def _build_shadow_omen(entry: LotEntry) -> ShadowOmen:
    frag = entry.get("fragment") or {
        "greek_fragment": "[· · ·]",
        "whisper": "...an eroded line where the papyrus fibers have parted...",
        "apparatus": "P. Lond. 121 (PGM VII) lacuna.",
    }
    return ShadowOmen(
        roll=entry["roll"],
        line=entry["line"],
        greek_fragment=frag["greek_fragment"],
        whisper=frag["whisper"],
        apparatus=frag["apparatus"],
    )


def cast_or_lookup(
    lots: Mapping[str, LotEntry],
    specific_roll: str | None = None,
    *,
    auto_reroll: bool = True,
    include_ref: bool = False,
    hour_evaluation: HourEvaluation | None = None,
) -> CastResult:
    """Cast 3d6 or look up a specific roll, optionally re-rolling damaged papyrus lacunae."""
    if auto_reroll and not any(not entry["is_lacuna"] for entry in lots.values()):
        raise ValueError("Cannot auto-reroll: all entries in the oracle table are marked as lacunae.")

    roll_key = normalize_roll(specific_roll) if specific_roll is not None else roll_3d6()
    if roll_key not in lots:
        raise KeyError(f"Roll '{roll_key}' not found in oracle table.")

    lacuna_rolls: list[str] = []
    shadow_omens: list[ShadowOmen] = []
    while lots[roll_key]["is_lacuna"] and auto_reroll:
        lacuna_rolls.append(roll_key)
        shadow_omens.append(_build_shadow_omen(lots[roll_key]))
        roll_key = roll_3d6()

    entry = lots[roll_key]
    return CastResult(
        line=entry["line"],
        roll=entry["roll"],
        utterance=entry["lot"],
        greek=entry.get("greek"),
        lexicon=tuple(entry.get("lexicon") or ()),
        is_lacuna=entry["is_lacuna"],
        fragment=entry.get("fragment"),
        reference=entry["reference"] if include_ref else None,
        lacuna_rerolls=tuple(lacuna_rolls),
        shadow_omens=tuple(shadow_omens),
        hour_evaluation=hour_evaluation,
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
        "--check-hour",
        action="store_true",
        help="Evaluate the auspiciousness of the consultation hour via PGM VII. 155-167 (Hemeralogia).",
    )
    parser.add_argument(
        "--day",
        type=int,
        default=None,
        help="Optional day of the month (1-30) for --check-hour (defaults to current local day).",
    )
    parser.add_argument(
        "--hour",
        type=int,
        default=None,
        help="Optional hour of the day (0-23) for --check-hour (defaults to current local hour).",
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
    if result.hour_evaluation is not None:
        heval = result.hour_evaluation
        lines.append(
            f"Hemeralogia (PGM VII. 155-167): Day {heval.day_of_month}, Hour {heval.hour_24:02d}:00 "
            f"({heval.time_of_day}) — {heval.status}"
        )
        lines.append(
            f"Prescribed Window: {heval.prescribed_label} [{heval.prescribed_greek}]"
        )
        lines.append(f"Hour Counsel: {heval.counsel}")
        lines.append("")

    if result.lacuna_rerolls:
        rerolls = ", ".join(result.lacuna_rerolls)
        lines.append(
            f"Note: Initial roll(s) [{rerolls}] fell upon damaged papyrus (lacuna) and were re-cast."
        )
        for omen in result.shadow_omens:
            lines.append(
                f"Shadow Omen ({omen.roll}, Line {omen.line}): {omen.greek_fragment} — {omen.whisper}"
            )
        lines.append("")

    lines.append(f"Roll: {result.roll} (Line {result.line})")
    if result.is_lacuna:
        lines.append("Utterance: [Lacuna — the papyrus fragment for this roll is lost]")
        if result.fragment is not None:
            lines.append(f"Fragment: {result.fragment['greek_fragment']}")
            lines.append(f"Whisper: {result.fragment['whisper']}")
            lines.append(f"Apparatus: {result.fragment['apparatus']}")
    else:
        if result.greek:
            lines.append(f"Greek: {result.greek}")
        lines.append(f'Utterance: "{result.utterance}"')
        if result.lexicon:
            lex_str = "; ".join(f"{item['term']} = {item['meaning']}" for item in result.lexicon)
            lines.append(f"Lexicon: {lex_str}")
    if include_ref and result.reference:
        lines.append(f"Reference: {result.reference}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    args = build_parser().parse_args(argv)

    try:
        oracle_data = load_oracle_data()
        lots = oracle_data["lots"]
        hour_eval: HourEvaluation | None = None
        if args.check_hour or args.day is not None or args.hour is not None:
            hour_eval = evaluate_hour(
                oracle_data["hemeralogia"],
                day_of_month=args.day,
                hour_24=args.hour,
            )
        result = cast_or_lookup(
            lots=lots,
            specific_roll=args.roll,
            auto_reroll=not args.no_reroll,
            include_ref=args.include_ref,
            hour_evaluation=hour_eval,
        )
    except (ValueError, KeyError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(
            json.dumps(
                result.to_dict(include_ref=args.include_ref),
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print(format_text_output(result, include_ref=args.include_ref))

    return 0


if __name__ == "__main__":
    sys.exit(main())
