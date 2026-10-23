# Oracle Scribe — Project Roadmap

This roadmap tracks planned enhancements for **`oracle-scribe`**, organized into four pillars: deepening the historical *PGM VII* papyrus dataset, expanding to additional ancient *Sortes* traditions, introducing multi-lot ritual spreads, and integrating with companion divination workflows.

---

## Pillar 1: Deepen Historical *PGM VII* (*Sortes Homericae*) Authenticity

Features that distinguish `oracle-scribe` from static random-verse generators by grounding readings in the physical and linguistic reality of the London Magical Papyrus (*PGM* VII. 1–148):

- [ ] **1.1 Original Homeric Greek & Root-Word Lexicon (`resources/sortes_homericae.json`)**
  - Add the original Ancient Greek hexameter line (`"greek"`) to all 191 surviving verses.
  - Tag each verse with 1–2 core Greek symbolic terms and their literal meanings (e.g., *nostos* [homecoming/return], *mētis* [cunning/resourcefulness], *thymos* [spirited breath/passion], *moira* [allotted portion], *ate* [ruinous folly]).
  - Update `SKILL.md` / `SOUL.md` so the Temple Scribe displays the Greek line alongside the translation and draws on the literal etymology of key words without referencing epic plot trivia.

- [ ] **1.2 Ancient "Days & Hours" Timing (*Hemeralogia*, *PGM* VII. 149–154)**
  - Incorporate the historical table of propitious and cautionary consultation hours preserved adjacent to the *Homeromanteion* in *PGM* VII.
  - Add an optional `--check-hour` flag to `scripts/cast_lot.py` that evaluates the time of casting (dawn, midday, dusk, deep night) and reports the traditional quality of the hour.

- [ ] **1.3 "Whispered Fragments" for the 25 Papyrus Lacunae**
  - Add scholarly conjectures and partial surviving Greek words (from Preisendanz, Maltomini, and Betz) to the 25 `"is_lacuna": true` entries.
  - When a roll lands on a damaged line and auto-rerolls, surface the surviving fragment as a "shadow omen" before delivering the primary verse.

---

## Pillar 2: Multi-Tradition *Sortes* Engine (`--corpus`)

Expand `scripts/cast_lot.py` and `resources/` to support additional historical lot-oracle systems, interpreted through the same **Symbol & Mirror** rubric rather than canned static fortunes:

- [ ] **2.1 Anatolian Knucklebone Oracles (*Kleromanteia*, `5d4` Astragaloi)**
  - Add `resources/sortes_astragaloi.json` based on the 2nd-century CE stone pillar inscriptions from Kremna, Termessos, and Oinoanda in SW Asia Minor.
  - Implement true `5d4` knucklebone mechanics (where the four flat/curved sides of the *astragalos* bear the traditional values `1`, `3`, `4`, and `6`), mapping all 56 unordered combinations to their presiding deity (*Hermes Kerdemporos*, *Zeus Olympios*, *Tyche*, *Nemesis*, etc.) and 4-line oracle verse.

- [ ] **2.2 *Sortes Astrampsychi* (Greco-Egyptian Decad Oracle)**
  - Implement the historical question-and-decad permutation lookup table from the *Sortes Astrampsychi*, allowing seekers to match their dilemma to one of the 92 classical life questions and draw a lot from `1` to `10`.

- [ ] **2.3 Classical & Lyric Bibliomancy Packs (`virgil`, `hafez`)**
  - Add curated verse tables for *Sortes Vergilianae* (*Aeneid*) and *Fal-e Hafez* (*Divan of Hafez*) selectable via `python3 scripts/cast_lot.py --corpus <homer|astragaloi|virgil|hafez>`.

---

## Pillar 3: Multi-Lot Castings & Ritual Spreads (`--spread`)

Support structured multi-verse castings in `scripts/cast_lot.py` and `SKILL.md` for complex or multi-path queries:

- [ ] **3.1 The Triad Cast (`--spread triad`)**
  - Draws three non-repeating lots in sequence:
    1. **The Threshold:** The true state of the matter right now.
    2. **The Wind:** The hidden force helping or opposing the seeker.
    3. **The Shore:** Where the current path leads if no course correction is made.

- [ ] **3.2 The Crossroads Cast (`--spread crossroads`)**
  - Draws two lots side-by-side (`Path A` vs. `Path B`) when a seeker is weighing two explicit alternatives, comparing the kinetic imagery and portent of each path.

- [ ] **3.3 Clarifying Counter-Cast**
  - When an initial reading yields an **Ambiguous** portent, allow a targeted follow-up cast that reads the second verse specifically as the turning key to the first.

---

## Pillar 4: Seeker's Chronicle & Cross-Agent Synthesis

Connect `oracle-scribe` with long-term reflection and companion Hermes profiles (`astro-gatekeeper`, `tarot-reader`):

- [ ] **4.1 Private Seeker's Chronicle (Local Consultation Log)**
  - Add an optional `--log` / `scripts/chronicle.py` utility that records the timestamp, seeker's query, `3d6` roll, drawn verse, and Scribe's portent into a local journal file (git-ignored so personal queries are never committed or pushed).
  - Support adding post-hoc reflection notes to track how an omen manifested in real life.

- [ ] **4.2 Astro-Oracular & Tarot Synthesis**
  - Define a workflow for pairing an `astro-gatekeeper` timing window (active Mahadasha/Antardasha/Pratyantardasha or major transit) or a `tarot-reader` spread with a *Sortes Homericae* casting—using the drawn Homeric line as the poetic epigraph and meditative anchor for that season.
