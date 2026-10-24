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
   - Contains all **216** three-dice combinations (`1-1-1` through `6-6-6`) from the Oxford Classical Text translation of *PGM* VII. 1–148.
   - **Data Integrity Fixes:** Corrects three transcription errors present in the Wikipedia source table's `Roll` column so that every 3d6 combination maps to its canonical line:
     - Line 67: Fixed `1-6-1` → `2-6-1`
     - Line 85: Fixed `3-1-1` → `3-3-1`
     - Line 88: Fixed `3-4-4` → `3-3-4`
   - **Lacuna Tracking:** Explicitly marks the **25 damaged papyrus lines** (`"is_lacuna": true`) where the ancient text was lost (`...`).

2. **True Random 3d6 Casting (`scripts/cast_lot.py`)**
   - Uses Python's cryptographic `secrets.randbelow(6) + 1` to generate unbiased 3d6 rolls instead of relying on LLM pseudo-random number selection.
   - **Automatic Lacuna Re-rolling:** When a roll lands on one of the 25 missing papyrus fragments, the script automatically re-casts the dice until a legible verse is drawn and logs the eroded roll(s) so the Scribe can weave the silent fragment into the narrative.
   - **Trivia Prevention:** Omits the *Iliad*/*Odyssey* book-and-line citation by default so the agent focuses purely on the imagery of the words.

---

## Supported Consultation Workflows

The skill supports three ways for a seeker to consult the oracle:

| Mode | Seeker Provides | Scribe Action |
| :--- | :--- | :--- |
| **1. Full Casting** | **Question only** *(e.g., "Should I launch this venture now?")* | Runs `python3 scripts/cast_lot.py` to roll 3d6, draws the verse from `sortes_homericae.json`, and interprets it. |
| **2. Physical Dice Lookup** | **Question + 3d6 Roll** *(e.g., "I rolled 4-2-6. What lies ahead for my journey?")* | Runs `python3 scripts/cast_lot.py --roll 4-2-6` to look up the exact verse from the local table and interprets it. |
| **3. Custom Bibliomancy** | **Question + Utterance** *(any verse drawn from Homer, Virgil, or another text)* | Interprets the provided utterance directly without rolling. |

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
Utterance: "But hurry into battle, and rouse the other soldiers."
```

### Look Up a Specific 3d6 Roll
Accepts hyphenated (`4-2-6`), comma-separated (`4,2,6`), or compact (`426`) formats:
```bash
python3 scripts/cast_lot.py --roll 4-2-6
```

### Handling Damaged Papyrus (Lacunae)
By default, landing on a missing verse triggers an automatic re-roll:
```bash
python3 scripts/cast_lot.py --roll 1-1-4
```
Example output:
```text
Note: Initial roll(s) [1-1-4] fell upon damaged papyrus (lacuna) and were re-cast.
Roll: 2-3-1 (Line 49)
Utterance: "be valiant, that later generations may also speak well of you."
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
