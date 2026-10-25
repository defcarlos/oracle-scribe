# Oracle Scribe (`oracle-scribe`)

**Oracle Scribe** embodies an ancient **Temple Scribe** to perform and interpret bibliomancy (*Sortes*), with built-in support for the historical ***Sortes Homericae*** (*Homeromanteion*, preserved in *PGM* VII. 1–148).

Rather than treating drawn lines as literary trivia or summarizing epic plots, the Temple Scribe reads each verse strictly as a **living oracular utterance**—analyzing its raw sensory imagery, kinetic motion, and emotional climate to mirror the seeker's query and deliver a clear verdict.

---

## Directory Structure

```text
oracle-scribe/
├── SKILL.md                          # Core skill instructions, persona, and interpretive rubric
├── SOUL.md                           # Self-contained Hermes profile prompt (zero-turn startup)
├── README.md                         # Skill documentation and reference guide
├── ROADMAP.md                        # Planned features and future enhancements
├── scripts/
│   └── cast_lot.py                   # CLI utility for 3d6 casting and table lookups
└── resources/
    └── sortes_homericae.json         # Local 216-entry Homeromanteion dataset (PGM VII. 1–148)
```

---

## Key Features & Recent Updates

1. **Offline *Sortes Homericae* Dataset (`resources/sortes_homericae.json`)**
   - Contains all **216** three-dice combinations (`1-1-1` through `6-6-6`) from the *PGM* VII. 1–148 *Homeromanteion*.
   - **Original Homeric Greek & Root-Word Lexicon:** Every surviving entry includes the original Ancient Greek hexameter (`"greek"`) and 2 core symbolic root words with their literal etymological meanings (`"lexicon"`).
   - **Whispered Fragments for the 25 Papyrus Lacunae:** All 25 damaged papyrus lines (`"is_lacuna": true`) include surviving Greek traces, papyrological apparatus notes (referencing *P. Lond.* 121, *P. Bon.* 3, *P. Oxy.* 3831, and Maltomini 1995), and an atmospheric "whispered fragment" (`"fragment"`).
   - **Ancient "Days & Hours" Timing (*Hemeralogia*, *PGM* VII. 155–167):** Embeds the complete 30-day Greco-Egyptian consultation calendar (`"hemeralogia"`) preserved immediately after the *Homeromanteion* in *PGM* VII.
   - **Data Integrity Fixes:** Corrects three transcription errors present in the Wikipedia source table's `Roll` column (`2-6-1`, `3-3-1`, `3-3-4`) as well as 25 OCR typos across the English translations and citations.

2. **True Random 3d6 Casting (`scripts/cast_lot.py`)**
   - Uses Python's cryptographic `secrets.randbelow(6) + 1` to generate unbiased 3d6 rolls instead of relying on LLM pseudo-random number selection.
   - **Shadow Omens on Lacuna Re-rolls:** When a roll lands on one of the 25 missing papyrus fragments, the script automatically re-casts the dice until a legible verse is drawn and surfaces the eroded line's surviving Greek trace as a `Shadow Omen`.
   - **Hemeralogia Consultation Check & Threshold Gate (`--check-hour`, `--hour-only`, `--force`):** Evaluates the day of the month and hour of day against *PGM* VII. 155–167 (`ἕωθεν` [at dawn], `μεσημβρίας` [at noon], `δείλης` [in the afternoon], `δι' ὅλης ἡμέρας` [throughout the whole day], or `μὴ χρῶ` [do not use]), computes the **Next Propitious Window**, and automatically withholds rolling the dice on the 6 Forbidden Days (`μὴ χρῶ`) unless `--force` is passed.
   - **Trivia Prevention:** Omits the *Iliad*/*Odyssey* book-and-line citation by default so the agent focuses purely on the imagery and Greek root words.

---

## Supported Consultation Workflows

The skill supports three ways for a seeker to consult the oracle:

| Mode | Seeker Provides | Scribe Action |
| :--- | :--- | :--- |
| **1. Full Casting** | **Question only** *(e.g., "Should I launch this venture now?")* | Runs `python3 scripts/cast_lot.py --check-hour`. Casts immediately on `Propitious` or `Cautionary (Off-Hour)` windows; withholds the dice roll on a `Forbidden Day (μὴ χρῶ)` unless the seeker insists (`--force`). |
| **2. Physical Dice Lookup** | **Question + 3d6 Roll** *(e.g., "I rolled 4-2-6. What lies ahead for my journey?")* | Runs `python3 scripts/cast_lot.py --roll 4-2-6 --check-hour` to look up the exact verse from the local table and interprets it. |
| **3. Custom Bibliomancy** | **Question + Utterance** *(any verse drawn from Homer, Virgil, or another text)* | Interprets the provided utterance directly without rolling. |
| **4. Threshold Hour Check** | **Greeting or Timing Query** *(e.g., "Is the hour favorable to consult the oracle?")* | Runs `python3 scripts/cast_lot.py --hour-only` to check the *Hemeralogia* status and **Next Propitious Window** before any dice are touched. |

> **Note:** If the seeker does not provide a **Question**, the Temple Scribe will never cast or invent a lot prematurely; it will politely ask the seeker to state their query first.

---

## Script Usage (`scripts/cast_lot.py`)

You (or the agent) can run `scripts/cast_lot.py` directly from the command line:

### Roll 3d6 and Draw a Lot (Default)
```bash
python3 scripts/cast_lot.py
```
Example output:
```text
Roll: 6-2-5 (Line 191)
Greek: ἀλλ' ὄρσευ πόλεμόνδε, καὶ ἄλλους ὄρνυθι λαούς
Utterance: "But hurry into battle, and rouse the other soldiers."
Lexicon: ὄρνυμι (ornymi) = to rouse into motion, lead from the front; λαός (laos) = the company of allies awaiting a signal
```

### Check the Propitiousness of the Hour (*Hemeralogia*, *PGM* VII. 155–167)
```bash
# Check the hour and Next Propitious Window without rolling the dice:
python3 scripts/cast_lot.py --hour-only

# Check the hour and cast 3d6 (automatically withholds cast on Forbidden Days unless --force is passed):
python3 scripts/cast_lot.py --check-hour
python3 scripts/cast_lot.py --check-hour --force

# Optional overrides for specific day (1-30) and hour (0-23):
python3 scripts/cast_lot.py --hour-only --day 16 --hour 10
```

### Look Up a Specific 3d6 Roll
Accepts hyphenated (`4-2-6`), comma-separated (`4,2,6`), or compact (`426`) formats:
```bash
python3 scripts/cast_lot.py --roll 4-2-6
```

### Handling Damaged Papyrus (Lacunae & Shadow Omens)
By default, landing on a missing verse triggers an automatic re-roll and surfaces the damaged line's surviving fragment as a `Shadow Omen`:
```bash
python3 scripts/cast_lot.py --roll 1-1-4
```
Example output:
```text
Note: Initial roll(s) [1-1-4] fell upon damaged papyrus (lacuna) and were re-cast.
Shadow Omen (1-1-4, Line 4): [α α δ · · · ]ν[ · · · ] — ...a trace of an ending in -n upon torn papyrus; the voice falls silent before the fourth throw...

Roll: 2-3-1 (Line 49)
Greek: ἄλκιμος ἔσσ', ἵνα τίς σε καὶ ὀψιγόνων εὖ εἴπῃ
Utterance: "be valiant, that later generations may also speak well of you."
Lexicon: ἄλκιμος (alkimos) = valiant, stout-hearted, courageous in defense; ὀψίγονος (opsigonos) = born hereafter, future generations
```
To disable automatic re-rolling on damaged lines, pass `--no-reroll`:
```bash
python3 scripts/cast_lot.py --roll 1-1-4 --no-reroll
```

### Additional Flags
- `--include-ref`: Include the *Iliad* / *Odyssey* book and line reference (e.g., `Od. 15.344`).
- `--json`: Output the result as structured JSON:
  ```json
  {
    "line": 216,
    "roll": "6-6-6",
    "utterance": "Don't dare get it into your mind to escape from me, Dolon.",
    "is_lacuna": false
  }
  ```

---

## Interpretive Method & Output Structure

Every reading delivered by the Temple Scribe follows a four-part structure defined in `SKILL.md`:

1. **📜 The Utterance:** Displays the 3d6 cast (when drawn from the *Sortes Homericae*) and the exact verse.
2. **👁️ The Omen & Imagery:** Analyzes the physical/sensory images, kinetic movement, and emotional climate of the words in isolation.
3. **🔍 The Mirror of the Lot:** Maps those poetic images directly onto the seeker's real-world dilemma.
4. **🏛️ The Scribe's Verdict:**
   - **Portent:** Classified as `Favorable`, `Cautionary`, `Adverse`, or `Ambiguous`.
   - **Counsel:** 1–2 sentences of direct, actionable guidance.
