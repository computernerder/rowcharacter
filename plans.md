# Realm of Warriors - Character Generator Architecture

## Project Goals

- Generate PDF character sheets for tabletop play
- Portable core logic usable in CLI, Django web server, or desktop GUI
- Data-driven design allowing users to edit/add races, professions, etc. via JSON files
- Permissive validation (allow out-of-bounds values, flag as non-compliant)

---

## Project Structure

```
row/
├── core/
│   ├── constants.py        # Enums (Skill, Attribute, Race, Path, etc.)
│   ├── player.py           # Player class (no I/O)
│   ├── skill.py            # SkillEntry dataclass
│   ├── race.py             # Race, Ancestry dataclasses
│   ├── profession.py       # Profession, Duty dataclasses
│   ├── path.py             # Path, Talent dataclasses
│   ├── background.py       # Background, Personality dataclasses
│   └── validation.py       # Validation rules, returns list of errors
│
├── loaders/
│   ├── base.py             # Generic Registry base class
│   ├── races.py            # RaceRegistry, AncestryRegistry
│   ├── professions.py      # ProfessionRegistry
│   ├── paths.py            # PathRegistry, TalentRegistry
│   └── backgrounds.py      # BackgroundRegistry
│
├── builders/
│   └── character_builder.py  # Orchestrates creation flow (no I/O)
│
├── cli/
│   └── prompts.py          # Interactive CLI frontend
│
├── export/
│   ├── pdf_sheet.py        # PDF generation
│   └── json_export.py      # Save/load characters
│
└── data/
    ├── races/
    │   ├── human.json
    │   ├── elf.json
    │   ├── dwarf.json
    │   ├── halffolk.json
    │   ├── goblin.json
    │   ├── simari.json
    │   ├── velkarr.json
    │   └── taurin.json
    │
    ├── ancestries/
    │   ├── human_velari.json
    │   ├── human_thalven.json
    │   ├── human_hrothkari.json
    │   ├── elf_sylari.json
    │   ├── elf_vaelorin.json
    │   ├── elf_thornkin.json
    │   └── ...
    │
    ├── professions/
    │   ├── warrior.json
    │   ├── criminal.json
    │   ├── priest.json
    │   ├── blacksmith.json
    │   ├── leatherworker.json
    │   ├── artisan.json
    │   ├── warden_of_the_wild.json
    │   ├── scholar.json
    │   └── free_agent.json
    │
    ├── paths/
    │   ├── defense.json
    │   ├── divine.json
    │   ├── exploitation.json
    │   ├── martial.json
    │   ├── mystic.json
    │   ├── power.json
    │   └── survival.json
    │
    ├── talents/
    │   ├── general_alertness.json
    │   ├── general_lucky.json
    │   ├── defense_protector.json
    │   ├── defense_guard.json
    │   └── ...
    │
    └── backgrounds/
        ├── devotee.json
        ├── outcast.json
        ├── village_champion.json
        ├── scholar.json
        ├── artisan.json
        ├── wanderer.json
        ├── noble_heir.json
        ├── mercenary.json
        ├── seafarer.json
        ├── shadow.json
        ├── nomad.json
        └── soldier.json
```

---

## Design Principles

### Separation of Concerns

| Layer | Responsibility | I/O Allowed |
|-------|----------------|-------------|
| `core/` | Game logic, data structures, calculations | No |
| `loaders/` | Read JSON, validate, build registries | File read only |
| `builders/` | Orchestrate character creation flow | No |
| `cli/` | User prompts, display | Yes |
| `export/` | Generate output files | File write only |

### Layered Application Pattern

Each character creation step is a "layer" applied to the Player object:

1. Race → `race.apply(player)`
2. Ancestry → `ancestry.apply(player)`
3. Profession → `profession.apply(player)`
4. Path → `path.apply(player)`
5. Background → `background.apply(player)`
6. Talents → `talent.apply(player)` (repeated per talent)

Each `apply()` method modifies the player's attributes, skills, proficiencies, etc.

### Data Loading Order

Due to references between types, load in this order:

1. Races
2. Ancestries (references Race)
3. Professions
4. Paths
5. Talents (references Path, Attributes)
6. Backgrounds

---

## Quantitative vs Narrative Effects

### Quantitative (program applies automatically)

These fields are processed by the `apply()` methods:

| Field | Type | Example |
|-------|------|---------|
| `ability_modifiers` | Dict[Attribute, int] | `{"Wisdom": 1}` |
| `speed` | int | `35` |
| `speed_modifier` | int | `10` |
| `darkvision` | int | `60` |
| `size` | str | `"Small"` |
| `languages` | List[str] | `["Common", "Elvish"]` |
| `skill_proficiencies` | List[Skill] | `["Stealth", "Perception"]` |
| `skill_bonuses` | Dict[Skill, int] | `{"Perception": 2}` |
| `tool_proficiencies` | List[str] | `["Thieves' tools"]` |
| `armor_proficiencies` | List[str] | `["Light", "Medium"]` |
| `weapon_proficiencies` | List[str] | `["Simple", "Martial"]` |
| `defense_bonus` | int | `1` |
| `base_hp` | int | `10` |
| `hp_bonus` | int | `5` |
| `attack_bonus_melee` | int | `1` |
| `attack_bonus_ranged` | int | `1` |
| `resistances` | List[str] | `["cold", "poison"]` |
| `reputation_modifier` | Dict | `{"region": "Aetherwood", "value": 1}` |

### Narrative (displayed on character sheet only)

Stored in `features` list, read by player during gameplay:

- "Once per long rest, heal yourself or an ally for 2d6"
- "Advantage on saving throws against being charmed"
- "Ignore difficult terrain caused by mud or marsh"
- "+1 Defense while wielding a shield"

The program does **not** track:
- Current equipment worn
- Abilities used this rest
- Temporary HP remaining
- Conditional bonuses based on game state

---

## JSON Schema Examples

### Race

```json
{
  "id": "elf",
  "name": "Elf",
  "creature_type": "Humanoid (Elf)",
  "size": "Medium",
  "speed": 30,
  "languages": ["Common", "Elvish"],
  "darkvision": 60,
  "ability_modifiers": {
    "Intellect": 1
  },
  "features": [
    {
      "name": "Fey Ancestry",
      "description": "Advantage on saving throws against being charmed; immune to magical sleep."
    }
  ]
}
```

### Ancestry

```json
{
  "id": "sylari",
  "name": "Sylari",
  "race": "elf",
  "region": "Forest Realms of Sylvarren",
  "ability_modifiers": {
    "Wisdom": 1
  },
  "languages": ["Sylvan"],
  "reputation_modifier": {
    "region": "Aetherwood",
    "value": 1
  },
  "personality": "Gentle, observant, spiritually attuned.",
  "features": [
    {
      "name": "Life Bond",
      "description": "Once per long rest, heal yourself or an ally for 2d6."
    }
  ]
}
```

### Profession

```json
{
  "id": "warrior",
  "name": "Warrior",
  "base_hp": 10,
  "feature": {
    "name": "Soldier's Network",
    "description": "You have ties to local fighters, guards, and mercenaries who can offer basic shelter, news, or introductions."
  },
  "armor_proficiencies": ["Light", "Medium"],
  "weapon_proficiencies": ["Simple"],
  "tool_proficiency_choices": {
    "count": 1,
    "options": ["artisan_tool", "gaming_set"]
  },
  "skill_choices": {
    "count": 2,
    "options": ["Athletics", "Intimidation", "Perception", "Insight", "Streetwise", "Nature"]
  },
  "suggested_paths": ["Defense", "Power"],
  "duties": ["fighter", "ranger"]
}
```

### Path

```json
{
  "id": "defense",
  "name": "Defense",
  "prerequisites": {
    "primary": {"attribute": "Endurance", "minimum": 15},
    "secondary": {
      "minimum": 13,
      "options": ["Might", "Intellect"]
    }
  },
  "primary_bonus": {
    "Endurance": 2,
    "Wisdom": 2
  },
  "talent_points_attribute": "Endurance",
  "attack_bonus_melee": 1,
  "attack_bonus_ranged": 1,
  "role": "Defender",
  "features": [
    {
      "name": "Hold the Line",
      "description": "When a hostile creature you can see moves within 5 ft of you, you may use your Reaction to make a melee attack. On a hit, the creature's speed becomes 0 until the end of your next turn."
    },
    {
      "name": "Read the Threat",
      "description": "At the start of combat, you may make an Insight check with advantage to identify the most dangerous visible enemy, TN 8+DR. On a success, your first attack against that enemy has advantage."
    },
    {
      "name": "Unyielding Focus",
      "description": "You have advantage on saves made to resist being knocked prone, disarmed, or shoved."
    }
  ],
  "talents": ["protector", "guard", "adrenal_push", "tactics", "keen_mind", "last_stand", "master_of_defense"]
}
```

### Background

```json
{
  "id": "devotee",
  "name": "Devotee",
  "description": "You served in a temple, shrine, or faith community, dedicating yourself to the service of gods or cosmic truths.",
  "skill_proficiencies": ["Insight", "History"],
  "languages_granted": 2,
  "equipment": ["Symbol of faith", "ritual book or prayer beads", "common clothes", "10 bronze"],
  "feature": {
    "name": "Shelter of the Faithful",
    "description": "You command the respect of those who share your faith, and you can perform the religious ceremonies of your deity."
  },
  "personality_tables": {
    "traits": [
      {"roll": 1, "text": "I speak in parables and symbols.", "morality": 0, "reputation": 0},
      {"roll": 2, "text": "I see omens in every event.", "morality": 0, "reputation": 0},
      {"roll": 3, "text": "I am patient and calm even in chaos.", "morality": 1, "reputation": 1}
    ],
    "ideals": [
      {"roll": 1, "text": "Faith. My devotion guides every step.", "morality": 1, "reputation": 1},
      {"roll": 2, "text": "Charity. I must help those in need.", "morality": 1, "reputation": 2}
    ],
    "bonds": [
      {"roll": 1, "text": "My temple is my family.", "morality": 1, "reputation": 1},
      {"roll": 2, "text": "I protect a sacred relic.", "morality": 0, "reputation": 1}
    ],
    "flaws": [
      {"roll": 1, "text": "I am intolerant of other faiths.", "morality": -1, "reputation": -1},
      {"roll": 2, "text": "I put faith above compassion.", "morality": -1, "reputation": -1}
    ]
  }
}
```

---

## Key Data Structures

### Player Skills Storage

Skills stored as list with four elements:

```python
self.skills[skill.value] = [attr_mod, rank, misc, trained]
# Index 0: attr_mod (int) - modifier from linked attribute
# Index 1: rank (int) - trained ranks in skill
# Index 2: misc (int) - miscellaneous bonuses
# Index 3: trained (bool) - whether skill is trained

self.skill_totals[skill.value] = attr_mod + rank + misc
```

Using `skill.value` (string) as key for consistency with current implementation.

### Feature (used by multiple types)

```python
@dataclass
class Feature:
    name: str
    description: str
```

### Race

```python
@dataclass
class Race:
    id: str
    name: str
    creature_type: str
    size: str
    speed: int
    languages: List[str]
    ability_modifiers: Dict[Attribute, int]
    features: List[Feature]
    darkvision: int = 0

    def apply(self, player: Player) -> None:
        # Add languages, set speed, apply ability mods, etc.
```

### Ancestry

```python
@dataclass
class Ancestry:
    id: str
    name: str
    race: Race  # Reference to parent race (resolved by loader)
    region: str
    ability_modifiers: Dict[Attribute, int]
    languages: List[str]
    reputation_modifier: Dict[str, Any]  # {"region": str, "value": int}
    personality: str
    features: List[Feature]

    def apply(self, player: Player) -> None:
        # Apply ability mods, add languages, set reputation, etc.
```

### Profession

```python
@dataclass
class Profession:
    id: str
    name: str
    base_hp: int
    feature: Feature
    armor_proficiencies: List[str]
    weapon_proficiencies: List[str]
    tool_proficiency_choices: Dict[str, Any]  # {"count": int, "options": List[str]}
    skill_choices: Dict[str, Any]  # {"count": int, "options": List[Skill]}
    suggested_paths: List[Path]
    duties: List[str] = None  # Only for Warrior

    def apply(self, player: Player, chosen_skills: List[Skill], chosen_tools: List[str]) -> None:
        # Set base HP, add proficiencies, train chosen skills
```

### Duty (sub-option for Warrior profession)

```python
@dataclass
class Duty:
    id: str
    name: str
    suggested_paths: List[Path]
    armor_proficiencies: List[str]
    weapon_proficiencies: List[str]
    tool_choices: Dict[str, Any]
    skill_choices: Dict[str, Any]
    armory_pack: str
    gold_alternative: int

    def apply(self, player: Player, chosen_skills: List[Skill], chosen_tools: List[str]) -> None:
        # Add additional proficiencies from duty
```

### Path

```python
@dataclass
class PathPrerequisite:
    primary_attribute: Attribute
    primary_minimum: int  # 15
    secondary_options: List[Attribute]
    secondary_minimum: int  # 13

@dataclass
class Path:
    id: str
    name: str
    prerequisites: PathPrerequisite
    primary_bonus: Dict[Attribute, int]  # Only applied if Primary Path
    talent_points_attribute: Attribute
    attack_bonus_melee: int
    attack_bonus_ranged: int
    role: str
    features: List[Feature]
    talents: List[str]  # Talent IDs available in this path

    def apply(self, player: Player, is_primary: bool = True) -> None:
        # Apply ability bonuses (if primary), attack bonuses, add features

    def check_prerequisites(self, player: Player, is_primary: bool = True) -> bool:
        # Return True if player meets requirements
```

### Talent

```python
@dataclass
class TalentRank:
    rank: int
    description: str
    # Quantitative effects at this rank
    defense_bonus: int = 0
    attack_bonus_melee: int = 0
    attack_bonus_ranged: int = 0
    hp_bonus: int = 0
    speed_modifier: int = 0
    skill_bonuses: Dict[Skill, int] = None

@dataclass
class TalentPrerequisite:
    attributes: Dict[Attribute, int] = None  # {"Wisdom": 11}
    level: int = None
    talents: List[str] = None  # Required talent IDs

@dataclass
class Talent:
    id: str
    name: str
    path: str = None  # None for general talents, path ID for path-specific
    max_rank: int
    prerequisites: TalentPrerequisite
    ranks: List[TalentRank]

    def apply(self, player: Player, rank: int) -> None:
        # Apply effects for the given rank

    def get_cost(self, rank: int) -> int:
        # Cost = rank number
        return rank

    def check_prerequisites(self, player: Player) -> bool:
        # Return True if player meets requirements
```

### Background

```python
@dataclass
class PersonalityEntry:
    roll: int
    text: str
    morality: int
    reputation: int

@dataclass
class PersonalityTables:
    traits: List[PersonalityEntry]  # d8
    ideals: List[PersonalityEntry]  # d6
    bonds: List[PersonalityEntry]   # d6
    flaws: List[PersonalityEntry]   # d6

@dataclass
class Background:
    id: str
    name: str
    description: str
    skill_proficiencies: List[Skill]
    languages_granted: int
    tool_proficiencies: List[str] = None
    equipment: List[str]
    feature: Feature
    personality_tables: PersonalityTables

    def apply(self, player: Player, chosen_languages: List[str]) -> None:
        # Train skills, add languages, add equipment

    def calculate_morality(self, ideal: PersonalityEntry, bond: PersonalityEntry, flaw: PersonalityEntry) -> int:
        return ideal.morality + bond.morality + flaw.morality

    def calculate_reputation(self, ideal: PersonalityEntry, bond: PersonalityEntry, flaw: PersonalityEntry) -> int:
        return ideal.reputation + bond.reputation + flaw.reputation
```

---

## Validation Strategy

- Permissive creation: allow invalid combinations
- `player.validate() -> List[ValidationError]` returns all issues
- Character sheet export checks validation and stamps non-compliant sheets
- Loader validates JSON on load, collects all errors before failing

### Example Validation Rules

- Path prerequisites met (15+ primary, 13+ secondary)
- At least 4 TP spent on Primary Path at level 1
- Point buy totals exactly 30 points
- Ancestry references valid race
- Enum values in JSON match defined enums

---

## Implementation Order

1. **Fix constants.py** - Correct skill mappings, add missing skills/enums, fix Path prerequisites
2. **Update Player skill structure** - Add trained flag as fourth element to skill lists
3. **Write sample JSON files** - One race + ancestries to validate schema
4. **Build loader/registry** - Generic base, then RaceRegistry
5. **Create Race/Ancestry dataclasses** - With `apply(player)` methods
6. **Repeat for Profession, Path, Background**
7. **Build character_builder.py** - Orchestrate the full flow
8. **Add CLI frontend** - Interactive prompts
9. **Add export** - PDF generation

---

## Enums Reference

All JSON files use string values that map to these enums:

### Attributes
`Might`, `Agility`, `Endurance`, `Wisdom`, `Intellect`, `Charisma`

### Skills
`Acrobatics`, `Animal Handling`, `Appraisal`, `Arcana`, `Athletics`, `Crafting`, `Deception`, `Diplomacy`, `History`, `Insight`, `Intimidation`, `Investigation`, `Medicine`, `Nature`, `Perception`, `Performance`, `Persuasion`, `Religion`, `Sleight of Hand`, `Stealth`, `Streetwise`, `Survival`, `Taming`

### Races
`human`, `elf`, `dwarf`, `halffolk`, `goblin`, `simari`, `velkarr`, `taurin`

### Paths
`Defense`, `Divine`, `Exploitation`, `Martial`, `Mystic`, `Power`, `Survival`

### Professions
`warrior`, `criminal`, `priest`, `blacksmith`, `leatherworker`, `artisan`, `warden_of_the_wild`, `scholar`, `free_agent`