# Realm of Warriors - Engineering Plan

## Goals
- Ship interactive character creation and level-up CLIs that validate inputs and save JSON.
- Keep all game content data-driven (JSON in `data/`) and reusable across CLI, future GUI/web, and PDF export.
- Provide PDF output using HTML/CSS templates in `assets/` and generated files in `exports/`.
- Maintain permissive but well-reported validation so homebrew tweaks are surfaced, not blocked.

## Current Repository Layout

```
core/                # Domain models and loaders (race, ancestry, profession, path, talent, background)
data/                # Game data JSON (races, ancestries, professions, paths, talents, backgrounds)
tools/               # CLIs (interactive_builder.py, interactive_levelup.py, pdf_generator.py)
assets/              # HTML/CSS templates and charactertemplate.json sample
characters/          # User-saved character JSON files
exports/             # Generated PDFs
tests/               # Pytest suite and fixture JSON
docs/                # Project plans (this file) and notes
template_model.py    # CharacterTemplate dataclass + JSON round-trip helpers
character_builder.py # Core builder orchestration (used by interactive builder)
levelup_manager.py   # Core level-up orchestration (used by interactive levelup)
validation.py        # CharacterValidator & ValidationResult
ROW_constants.py     # Enums and shared constants
```

Run CLIs from the project root:
- `python tools/interactive_builder.py`
- `python tools/interactive_levelup.py`
- `python tools/pdf_generator.py`

## Key Components
- **Domain (core/)**: Data classes plus loader helpers for races, ancestries, professions, paths, backgrounds, and talents. `CharacterBuilder` and `LevelUpManager` consume these loaders.
- **Validation (validation.py)**: `CharacterValidator` checks ability-score methods, ID existence, path prerequisites, talent ranks, advancement spends, ability increases, and whole-character consistency. CLIs call it automatically.
- **Template Model (template_model.py)**: Defines `CharacterTemplate`, handles JSON ⇄ dataclass serialization, and keeps the saved file shape stable.
- **Builder Flow (character_builder.py + tools/interactive_builder.py)**: Guides through ability scores → race → ancestry → profession → path → background → pending choices, then validates and saves/prints the character JSON.
- **Level-Up Flow (levelup_manager.py + tools/interactive_levelup.py)**: Loads a character JSON, computes options, validates TP/AP spending and ability increases, applies level changes, and saves back.
- **PDF Export (tools/pdf_generator.py + assets/)**: Uses HTML/CSS templates (`assets/blank_sheet.html`, `assets/character_sheet.html`) to render PDFs into `exports/`.
- **Data Packs (data/)**: Editable JSON that define all game content. Adding a new race/ancestry/path/background/talent is a data-only change.
- **Tests (tests/)**: Pytest coverage for builder/core/player flows; fixture JSON lives alongside tests.

## Data Loading Order
To satisfy references: races → ancestries → professions → paths → talents → backgrounds. CLIs use `ROOT_DIR/data` so they work from any working directory.

## Validation Strategy
- Ability scores: validate per method (point draw, standard array, roll, quick test) before applying.
- Character: check required fields, ID existence, path prerequisites, ability scores, HP sanity, etc.
- Level-up: verify TP/AP totals, primary-path minimum spend, talent rank progression, ability-increase legality, and advancement choices (skills/languages/proficiencies).
- Warnings are surfaced but do not block saves unless errors exist.

## Character Creation Flow
1) Load game data from `data/`.
2) Choose ability score method; validate.
3) Select race and ancestry (filters ancestries by race).
4) Pick profession (and duty where applicable) and resolve skill/language/tool choices.
5) Pick primary path; show prerequisites and availability; resolve pending choices.
6) Select background; resolve remaining choices.
7) Recalculate derived stats; validate full character; export to JSON (default under `characters/`).

## Level-Up Flow
1) Load existing character JSON (CLI lists options from cwd, script dir, and `characters/`).
2) Compute level-up options (TP, AP, ASI availability, extra attack, spellcrafting gains).
3) Collect choices: ability increase (if granted), talent spending (with primary-path floor), advancement purchases, HP roll/average.
4) Validate choices; block on errors, surface warnings.
5) Apply level, recalc derived stats, and save to the chosen path.

## PDF Generation Flow
- Uses `template_model.dump_character_template` to produce data for HTML templates.
- Templates in `assets/` drive layout; adjust CSS/HTML to change visual design.
- Outputs go to `exports/`; ensure directories exist (script creates as needed).

## Persistence & Files
- **Input data**: `data/` JSON files (authoritative content).
- **User saves**: `characters/*.json` (CLI defaults here; names sanitized).
- **Exports**: `exports/*.pdf` for rendered sheets.
- **Fixtures**: `tests/*.json` are test-only and should not be edited for gameplay.

## Testing
- From repo root: `python -m pytest tests`.
- Scope covers builder/core/player; extend with cases for new validation rules and data regressions.

## Near-Term Enhancements
- Expand validation coverage for equipment and spellcrafting once those systems land.
- Add richer talent/path data (general talents JSON) and hook into LevelUpManager options display.
- Add CLI ergonomics: redo prompts for mass choice resolution and better error display.