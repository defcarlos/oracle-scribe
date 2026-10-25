#!/usr/bin/env python3
"""
Cast or look up a lot from the Sortes Homericae (Homeromanteion, PGM VII. 1-148)
with support for Homeric Greek hexameters, root-word lexicon, whispered lacuna
fragments, and PGM VII. 155-167 Hemeralogia ("Days and Hours for Divination").

Usage:
  python3 scripts/cast_lot.py                    # Roll 3d6 (auto-rerolls damaged papyrus lacunae)
  python3 scripts/cast_lot.py --check-hour       # Check PGM VII timing; casts on Propitious/Off-Hour, gates on Forbidden Day
  python3 scripts/cast_lot.py --hour-only        # Check PGM VII timing and Next Propitious Window without rolling dice
  python3 scripts/cast_lot.py --check-hour --force  # Override Forbidden Day gate and roll 3d6 anyway
  python3 scripts/cast_lot.py --roll 4-2-6       # Look up a specific 3d6 roll
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
from typing import Any, Final, Literal, TypedDict

DICE_COUNT: Final[int] = 3
DICE_SIDES: Final[int] = 6
MAX_HEMERALOGIA_DAY: Final[int] = 30
RESOURCE_PATH: Final[Path] = (
    Path(__file__).resolve().parent.parent / "resources" / "sortes_homericae.json"
)
ROLL_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^\s*([1-6])(?:[\s,:-]+([1-6])[\s,:-]+([1-6])|([1-6])([1-6]))\s*$"
)

type TimeOfDay = Literal["dawn", "noon", "afternoon", "dusk", "deep_night"]
type HourStatus = Literal[
    "Propitious",
    "Cautionary (Off-Hour)",
    "Forbidden Day (Apophras)",
]


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


class HemeralogiaWindow(TypedDict):
    """Schema for a consultation window in PGM VII. 155-167."""

    greek: str
    label: str
    hours_range: list[int] | list[list[int]]
    counsel: str


class HemeralogiaData(TypedDict):
    """Schema for the PGM VII. 155-167 Hemeralogia calendar."""

    source: str
    description: str
    windows: dict[str, HemeralogiaWindow]
    days: dict[str, str]


class OracleResource(TypedDict):
    """Top-level schema for resources/sortes_homericae.json."""

    source: str
    url: str
    total_combinations: int
    lacunae_count: int
    lots: dict[str, LotEntry]
    hemeralogia: HemeralogiaData


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
    status: HourStatus
    counsel: str
    next_propitious_window: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "day_of_month": self.day_of_month,
            "hour_24": self.hour_24,
            "time_of_day": self.time_of_day,
            "prescribed_window": self.prescribed_label,
            "prescribed_greek": self.prescribed_greek,
            "status": self.status,
            "counsel": self.counsel,
        }
        if self.next_propitious_window is not None:
            payload["next_propitious_window"] = self.next_propitious_window
        return payload


@dataclass(frozen=True, slots=True)
class CastResult:
    """Immutable result of casting or looking up a 3d6 lot (or gated/hour-only check)."""

    line: int | None
    roll: str | None
    utterance: str | None
    greek: str | None
    lexicon: tuple[LexiconItem, ...]
    is_lacuna: bool
    fragment: LacunaFragment | None = None
    reference: str | None = None
    shadow_omens: tuple[ShadowOmen, ...] = ()
    hour_evaluation: HourEvaluation | None = None
    cast_withheld: bool = False

    @property
    def lacuna_rerolls(self) -> tuple[str, ...]:
        """Rolls that landed on damaged papyrus lacunae before a legible verse was drawn."""
        return tuple(omen.roll for omen in self.shadow_omens)

    def to_dict(self, *, include_ref: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.hour_evaluation is not None:
            payload["hemeralogia"] = self.hour_evaluation.to_dict()
        if self.cast_withheld:
            payload["cast_withheld"] = True
            return payload

        payload.update(
            {
                "line": self.line,
                "roll": self.roll,
                "utterance": self.utterance,
                "greek": self.greek,
                "lexicon": list(self.lexicon),
                "is_lacuna": self.is_lacuna,
            }
        )
        if self.fragment is not None:
            payload["fragment"] = dict(self.fragment)
        if self.shadow_omens:
            payload["lacuna_rerolls"] = list(self.lacuna_rerolls)
            payload["shadow_omens"] = [omen.to_dict() for omen in self.shadow_omens]
        if include_ref:
            payload["reference"] = self.reference
        return payload


def load_oracle_data(resource_path: Path = RESOURCE_PATH) -> OracleResource:
    """Load and validate the full Sortes Homericae JSON resource."""
    if not resource_path.is_file():
        raise FileNotFoundError(f"Oracle table not found at {resource_path}")
    data = json.loads(resource_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("lots"), dict):
        raise ValueError(f"Malformed oracle table in {resource_path}: missing 'lots' mapping.")
    hemeralogia = data.get("hemeralogia")
    if not isinstance(hemeralogia, dict) or not isinstance(hemeralogia.get("days"), dict):
        raise ValueError(
            f"Malformed oracle table in {resource_path}: missing 'hemeralogia' schedule."
        )
    return data  # type: ignore[return-value]


def load_lots(resource_path: Path = RESOURCE_PATH) -> dict[str, LotEntry]:
    """Load the 216 Sortes Homericae lots from the local JSON resource."""
    return load_oracle_data(resource_path)["lots"]


def classify_time_of_day(hour_24: int) -> TimeOfDay:
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


def _normalize_intervals(hours_range: Sequence[Any]) -> list[tuple[int, int]]:
    """Normalize a single [start, end] or nested [[s1, e1], [s2, e2]] into (start, end) tuples."""
    if not hours_range:
        return []
    if isinstance(hours_range[0], int):
        return [(int(hours_range[0]), int(hours_range[1]))]
    return [(int(span[0]), int(span[1])) for span in hours_range]


def _is_hour_in_window(hour_24: int, hours_range: Sequence[Any]) -> bool:
    """Check whether hour_24 falls within any (start, end) interval in hours_range."""
    return any(start <= hour_24 <= end for start, end in _normalize_intervals(hours_range))


def _find_next_propitious_window(
    hemeralogia: HemeralogiaData,
    table_day: int,
    current_hour: int,
) -> str:
    """Find and format the next propitious consultation window from (table_day, current_hour)."""
    days_map = hemeralogia["days"]
    windows_map = hemeralogia["windows"]

    # 1. Check if a prescribed window opens later today on the same day
    today_key = days_map[str(table_day)]
    today_info = windows_map[today_key]
    for start, end in _normalize_intervals(today_info["hours_range"]):
        if start > current_hour:
            if today_key == "dawn_and_afternoon":
                sub_info = windows_map["dawn" if start == 5 else "afternoon"]
                label, greek = sub_info["label"], sub_info["greek"]
            else:
                label, greek = today_info["label"], today_info["greek"]
            return f"Today (Day {table_day}), {start:02d}:00–{end:02d}:00 — {label} [{greek}]"

    # 2. Otherwise scan forward across the 30-day cycle
    for offset in range(1, MAX_HEMERALOGIA_DAY + 1):
        cand_day = ((table_day - 1 + offset) % MAX_HEMERALOGIA_DAY) + 1
        cand_key = days_map[str(cand_day)]
        if cand_key == "do_not_use":
            continue
        cand_info = windows_map[cand_key]
        intervals = _normalize_intervals(cand_info["hours_range"])
        if not intervals:
            continue
        start, end = intervals[0]
        day_prefix = "Tomorrow" if offset == 1 else f"In {offset} days"
        return (
            f"{day_prefix} (Day {cand_day}), {start:02d}:00–{end:02d}:00 — "
            f"{cand_info['label']} [{cand_info['greek']}]"
        )

    return "Unknown"


def evaluate_hour(
    hemeralogia: HemeralogiaData,
    *,
    day_of_month: int | None = None,
    hour_24: int | None = None,
) -> HourEvaluation:
    """Evaluate consultation timing according to PGM VII. 155-167."""
    now = datetime.now().astimezone()
    raw_day = day_of_month if day_of_month is not None else now.day
    if not 1 <= raw_day <= 31:
        raise ValueError(f"Invalid day '{raw_day}'. Must be between 1 and 31.")
    # Map 31st day of a modern solar month to day 30 of the 30-day Greco-Egyptian table
    table_day = min(raw_day, MAX_HEMERALOGIA_DAY)

    current_hour = hour_24 if hour_24 is not None else now.hour
    if not 0 <= current_hour <= 23:
        raise ValueError(f"Invalid hour '{current_hour}'. Must be between 0 and 23.")

    days_map = hemeralogia["days"]
    windows_map = hemeralogia["windows"]
    window_key = days_map[str(table_day)]
    window_info = windows_map[window_key]
    period = classify_time_of_day(current_hour)
    period_label = period.replace("_", " ")

    status: HourStatus
    next_window: str | None = None
    if window_key == "do_not_use":
        status = "Forbidden Day (Apophras)"
        counsel = window_info["counsel"]
        next_window = _find_next_propitious_window(hemeralogia, table_day, current_hour)
    elif _is_hour_in_window(current_hour, window_info["hours_range"]):
        status = "Propitious"
        counsel = window_info["counsel"]
    else:
        status = "Cautionary (Off-Hour)"
        next_window = _find_next_propitious_window(hemeralogia, table_day, current_hour)
        counsel = (
            f"Day {table_day} is prescribed for '{window_info['label']}' ({window_info['greek']}), "
            f"whereas the current hour falls in '{period_label}'. "
            "Proceed with heightened mindfulness, as the temple doors are only half-parted."
        )

    return HourEvaluation(
        day_of_month=table_day,
        hour_24=current_hour,
        time_of_day=period_label,
        prescribed_window_key=window_key,
        prescribed_greek=window_info["greek"],
        prescribed_label=window_info["label"],
        status=status,
        counsel=counsel,
        next_propitious_window=next_window,
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

    shadow_omens: list[ShadowOmen] = []
    while lots[roll_key]["is_lacuna"] and auto_reroll:
        shadow_omens.append(_build_shadow_omen(lots[roll_key]))
        roll_key = roll_3d6()
        if roll_key not in lots:
            raise KeyError(f"Re-rolled key '{roll_key}' not found in oracle table.")

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
        help=(
            "Evaluate the consultation hour via PGM VII. 155-167 (Hemeralogia). "
            "Proceeds on Propitious/Off-Hour, and withholds casting on Forbidden Days unless --force is set."
        ),
    )
    parser.add_argument(
        "--hour-only",
        action="store_true",
        help="Check the PGM VII. 155-167 Hemeralogia status and Next Propitious Window without casting dice.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Override the Forbidden Day (Apophras) ritual gate and cast the dice anyway.",
    )
    parser.add_argument(
        "--day",
        type=int,
        default=None,
        help="Optional day of the month (1-30) for --check-hour / --hour-only (defaults to current local day).",
    )
    parser.add_argument(
        "--hour",
        type=int,
        default=None,
        help="Optional hour of the day (0-23) for --check-hour / --hour-only (defaults to current local hour).",
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
        if heval.next_propitious_window is not None:
            lines.append(f"Next Propitious Window: {heval.next_propitious_window}")
        if result.cast_withheld:
            if heval.status == "Forbidden Day (Apophras)":
                lines.append(
                    "Gate: Casting withheld on a Forbidden Day (μὴ χρῶ). "
                    "Pass --force only if the seeker explicitly insists on overriding the threshold."
                )
            return "\n".join(lines)
        lines.append("")

    if result.shadow_omens:
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
        should_eval_hour = (
            args.check_hour
            or args.hour_only
            or args.day is not None
            or args.hour is not None
        )
        if should_eval_hour:
            hour_eval = evaluate_hour(
                oracle_data["hemeralogia"],
                day_of_month=args.day,
                hour_24=args.hour,
            )

        # Withhold dice casting if --hour-only is requested OR if today is a Forbidden Day
        # and --force was not passed (unless looking up a physical --roll already thrown by the user).
        is_forbidden_gate = (
            hour_eval is not None
            and hour_eval.status == "Forbidden Day (Apophras)"
            and not args.force
            and args.roll is None
        )
        if args.hour_only or is_forbidden_gate:
            result = CastResult(
                line=None,
                roll=None,
                utterance=None,
                greek=None,
                lexicon=(),
                is_lacuna=False,
                hour_evaluation=hour_eval,
                cast_withheld=True,
            )
        else:
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
