# Realm of Warriors - Character Creation System Guide

## Overview

This document describes the character creation process for Realm of Warriors (RoW) v2.0.1, structured for programmatic implementation.

### Tooling Updates (2026-01-03)
- `template_model.py` now maps JSON to a single `CharacterTemplate` root with nested dataclasses; it auto-uses `ROW_constants` enums when possible and round-trips to the same JSON shape.
- `interactive_builder.py` now shows which Paths are unlocked immediately after setting ability scores (primary needs 15+ in primary stat and 13+ in a secondary); default export filename is `name_player.json` when saving.
- `interactive_levelup.py` lists available character `.json` files from the current working directory and the script directory; you can pick by number or type a path.
- CLIs now validate ability scores and final characters with `CharacterValidator`, enforce level-up prerequisites, and load data relative to the project root (`data/`).

### Project Layout (2026-01-03)
- `assets/`: HTML/CSS templates and `charactertemplate.json` samples
- `tools/`: CLIs (`interactive_builder.py`, `interactive_levelup.py`, `pdf_generator.py`)
- `tests/`: Python tests plus their JSON artifacts
- `exports/`: Generated PDFs (e.g., `blank_sheet.pdf`, `character_sheet.pdf`)
- `characters/`: Saved character sheets
- `data/`: Game data JSON (races, ancestries, paths, etc.)
- `core/`: Core domain models and loaders
- `docs/`: Planning notes (`plans.md`)
- Run the CLIs from the project root: `python tools/interactive_builder.py` or `python tools/interactive_levelup.py`

### Product Features (what ships in this repo)
- Interactive Builder CLI (`tools/interactive_builder.py`): guided character creation with race, ancestry, profession, path, background, pending choice resolution, and integrated validation of ability scores and the finished character.
- Interactive Level Up CLI (`tools/interactive_levelup.py`): loads an existing character JSON, walks through level-up options, validates talent/AP spend and ability bumps, and reports warnings before applying changes.
- PDF Generator (`tools/pdf_generator.py`): renders HTML templates from `assets/` (blank sheet and character sheet) into PDFs saved under `exports/`.
- Validation layer (`validation.py`): `CharacterValidator` checks ability score methods, race/path IDs, talent ranks, advancement spends, and full character JSONs; CLIs call this automatically.
- Core models (`core/`): domain objects and loaders for races, ancestries, professions, paths, backgrounds, and talents sourced from `data/`.
- Data packs (`data/`): JSON definitions for game content; add or adjust records here to extend the system.
- Tests (`tests/`): regression coverage for builder/core/player flows; run with `python -m pytest tests` from the project root.
- Assets (`assets/`): HTML/CSS and example templates for PDF output and UI shaping; customize to change sheet look and feel.

---

## Character Creation Steps (in order)

1. **Race & Ancestry Selection**
2. **Profession Selection** 
3. **Ability Score Generation**
4. **Primary Path Selection** (must meet prerequisites)
5. **Background Selection**
6. **Calculate Derived Stats**
7. **Purchase Talents with Talent Points**
8. **Record Equipment**

---

## 1. Ability Scores

### Core Abilities (6 total)
| Ability | Abbreviation | Description |
|---------|--------------|-------------|
| Might | Mgt | Physical strength, heavy weapons, grappling |
| Agility | Agl | Reflexes, speed, ranged attacks, dodging |
| Endurance | End | Toughness, stamina, poison/disease resistance |
| Wisdom | Wis | Awareness, perception, judgment, intuition |
| Intellect | Int | Knowledge, memory, reasoning, problem-solving |
| Charisma | Cha | Personality, persuasion, deception, leadership |

### Ability Score Modifiers & Life Points
| Score | Modifier | Life Points |
|-------|----------|-------------|
| 1 | -5 | 1 |
| 2-3 | -4 | 2 |
| 4-5 | -3 | 4 |
| 6-7 | -2 | 6 |
| 8-9 | -1 | 8 |
| 10-11 | 0 | 10 |
| 12-13 | +1 | 12 |
| 14-15 | +2 | 14 |
| 16-17 | +3 | 16 |
| 18-19 | +4 | 18 |
| 20-21 | +5 | 20 |
| 22-23 | +6 | 22 |
| 24-25 | +7 | 24 |

### Generation Methods

**Standard Array:** 8, 10, 11, 12, 13, 14, 15

**Random Generation:** Roll 4d6, keep highest 3 dice. Repeat 6 times.

**Point Buy:** 30 points to spend:
| Score | Cost |
|-------|------|
| 8 | 0 |
| 9 | 1 |
| 10 | 2 |
| 11 | 3 |
| 12 | 4 |
| 13 | 5 |
| 14 | 7 |
| 15 | 9 |

---

## 2. Races & Ancestries

### Human
- **Creature Type:** Humanoid
- **Size:** Medium
- **Speed:** 30 ft
- **Languages:** Common + one choice
- **Special:** Adaptability (2 additional skill proficiencies)
- **Core Ability Adjustment:** +1 to one OR +2/-1 to two abilities (not already granted by ancestry)

#### Human Ancestries
| Ancestry | Core Adjustment | Special Ability | Languages | Rep Modifier |
|----------|-----------------|-----------------|-----------|--------------|
| Velari | +1 Intellect | Keen Mind (History prof, advantage on lore recall) | Elvish or Dwarvish | +1 Aetherwood |
| Thalven | +1 Might | Waveborn (swim speed = walk, water vehicle prof) | Aquan or Orcish | +1 Sunforge Coast |
| Hrothkari | +1 Endurance | Winterborn (cold resistance, Survival advantage) | One choice | +1 Frostmere Isles |

### Elf
- **Creature Type:** Humanoid (Elf)
- **Size:** Medium
- **Speed:** 30 ft
- **Languages:** Common, Elvish
- **Special:** Darkvision 60 ft, Fey Ancestry (advantage vs charm, immune to magical sleep)
- **Core Ability Adjustment:** +1 Intellect

#### Elf Ancestries
| Ancestry | Core Adjustment | Special Ability | Languages | Rep Modifier |
|----------|-----------------|-----------------|-----------|--------------|
| Sylari | +1 Wisdom | Life Bond (1/long rest heal 2d6) | Sylvan | +1 Aetherwood |
| Vaelorin | +1 Intellect | Astral Memory (Arcana prof, advantage on celestial/ancient magic) | One choice | +1 Highmarch |
| Thornkin | +1 Agl, +1 Int, -1 Cha | Bramble Step (ignore ruin/overgrowth terrain) | Thornspeech | +1 Verdant Vale |

### Dwarf
- **Creature Type:** Humanoid (Dwarf)
- **Size:** Medium
- **Speed:** 25 ft
- **Languages:** Common, Dwarvish
- **Special:** Darkvision 60 ft, Stonecunning (History prof, advantage on stonework), Iron Stomach (poison resistance)
- **Core Ability Adjustment:** +1 Endurance

#### Dwarf Ancestries
| Ancestry | Core Adjustment | Special Ability | Languages | Rep Modifier |
|----------|-----------------|-----------------|-----------|--------------|
| Grundari | +1 Might | Forged (Blacksmith & Leatherworker tools, 2x repair) | Orcish or Goblin | +1 Emberfall |
| Ironhills | +1 Intellect | Mountain Resolve (cold resistance, Survival advantage) | One choice | +1 Highmarch |
| Molvryn | +1 Wisdom | Rune Sense (advantage on magical inscriptions/runes) | Ancient Dwarvish | +1 Emberfall |

### Halffolk
- **Creature Type:** Humanoid (Halffolk)
- **Size:** Small
- **Speed:** 25 ft
- **Languages:** Common, Halffolk
- **Special:** Lucky (1) - gain Lucky talent tier 1
- **Core Ability Adjustment:** +1 Agility

#### Halffolk Ancestries
| Ancestry | Core Adjustment | Special Ability | Languages | Rep Modifier |
|----------|-----------------|-----------------|-----------|--------------|
| Nimrell | +1 Charisma | Resilient Spirit (1/long rest, turn failed save to success) | One choice | +1 Verdant Vale |
| Brindleford | +1 Intellect | Herbal Touch (Herbalism prof, half foraging time) | Sylvan | +1 Verdant Vale |
| Tavari | +1 Endurance | River Runner (swim speed = walk) | One choice | +1 Sunforge Coast |

### Goblin
- **Creature Type:** Humanoid (Goblin)
- **Size:** Small
- **Speed:** 30 ft
- **Languages:** Common, Goblin
- **Special:** Darkvision 60 ft, Nimble Escape (Disengage/Hide as bonus action)
- **Core Ability Adjustment:** +1 Agility

#### Goblin Ancestries
| Ancestry | Core Adjustment | Special Ability | Languages | Rep Modifier |
|----------|-----------------|-----------------|-----------|--------------|
| Mirekin | +1 Endurance | Bog Strider (ignore mud/marsh terrain) | Draconic or Elvish | +1 Stormreach |
| Citykin | +1 Charisma | Silver Tongue (Persuasion prof + advantage) | One choice | +1 Sunforge Coast |
| Ruinborn | +1 Intellect | Scrap Expertise (use any tool at disadvantage) | One choice | +1 Stormreach |

### Simari
- **Creature Type:** Humanoid
- **Size:** Medium
- **Speed:** 30 ft
- **Languages:** Common, Simarru
- **Special:** Primal Senses (Perception prof), Prehensile Tail (grasp objects, assist climbing)
- **Core Ability Adjustment:** +1 Agility

#### Simari Ancestries
| Ancestry | Core Adjustment | Special Ability | Languages | Rep Modifier |
|----------|-----------------|-----------------|-----------|--------------|
| Saraku | +1 Agility | Skybound (Acrobatics prof + advantage) | Simarru | +1 Aetherwood |
| Jinroku | +1 Might | River Pulse (swim speed = walk) | Simarru | +1 Stormreach |
| Tesharai | +1 Charisma | Negotiator (Persuasion prof + advantage) | Simarru, Common | +1 Sunforge Coast |

### Velkarr
- **Creature Type:** Humanoid
- **Size:** Medium
- **Speed:** 35 ft
- **Languages:** Common, Velkarran
- **Special:** Primal Senses (Perception prof +2 misc)
- **Core Ability Adjustment:** +2 Agility, -1 Endurance

#### Velkarr Ancestries
| Ancestry | Core Adjustment | Special Ability | Languages | Rep Modifier |
|----------|-----------------|-----------------|-----------|--------------|
| Shadowfen | +1 Intellect | Murkstep (Stealth prof, advantage in dim/dark) | Velkarran | +1 Stormreach |
| Nightspire | +1 Might | Pounce Strike (+1d4 on 10ft+ fall attack) | Velkarran | +1 Highmarch |
| Umbravale | +1 Wisdom | Silent Step (Stealth advantage at half speed) | Velkarran | +1 Aetherwood |

### Taurin
- **Creature Type:** Humanoid
- **Size:** Medium (imposing)
- **Speed:** 30 ft
- **Languages:** Common, Tauric
- **Special:** Primal Senses (Perception advantage), Horn Attack (1d6+Mgt piercing unarmed), Immovable (advantage vs shove/prone)
- **Core Ability Adjustment:** +1 Might, +1 Endurance, -1 Charisma

#### Taurin Ancestries
| Ancestry | Core Adjustment | Special Ability | Languages | Rep Modifier |
|----------|-----------------|-----------------|-----------|--------------|
| Stonegrave | +1 Endurance | Stonehide (temp HP = End mod, short rest) | One choice | +1 Emberfall |
| Gorath Plains | +1 Wisdom | Charging Step (20ft charge = +1d6 horn damage) | One choice | +1 Verdant Vale |
| Labrynthos | +1 Intellect | Maze Mind (Survival advantage) | One choice | +1 Highmarch |

---

## 3. Professions

Professions determine starting HP, proficiencies, skills, and equipment.

### Warrior
- **Base HP:** 10
- **Feature:** Soldier's Network
- **Armor:** Light, Medium
- **Weapons:** Simple
- **Tools:** One artisan tool or gaming set
- **Skills (choose 2):** Athletics, Intimidation, Perception, Insight, Streetwise, Nature

#### Fighter Duty
- **Suggested Paths:** Defense or Power
- **Additional Armor:** Heavy
- **Additional Weapons:** Martial
- **Additional Skills (choose 1):** Athletics, Intimidation, Appraisal
- **Pack:** Heavy Warrior Pack or 65 gold

#### Ranger Duty
- **Suggested Paths:** Defense or Survival
- **Additional Armor:** Medium
- **Additional Weapons:** Finesse, Ranged
- **Additional Skills (choose 1):** Perception, Animal Handling, Nature
- **Pack:** Wilderness Pack or 65 gold

### Criminal
- **Base HP:** 8
- **Suggested Paths:** Exploitation or Martial
- **Feature:** Underworld Contact
- **Armor:** Light
- **Weapons:** Simple, Light
- **Tools:** Thieves' tools
- **Skills (choose 2):** Stealth, Sleight of Hand, Deception, Insight, Streetwise, Perception
- **Pack:** Criminal's Pack or 40 gold

### Priest
- **Base HP:** 6
- **Suggested Paths:** Divine or Martial
- **Feature:** Diocese Ties
- **Armor:** None
- **Weapons:** Simple
- **Skills (choose 2):** Religion, Insight, Medicine, Diplomacy, History, Perception
- **Pack:** Priest's Pack or 45 gold

### Blacksmith
- **Base HP:** 10
- **Suggested Paths:** Defense or Power
- **Feature:** Smith's Guild Bond
- **Armor:** Light, Medium, Heavy
- **Weapons:** Simple, Two-Handed
- **Tools:** Smithing tools
- **Skills (choose 2):** Crafting, Athletics, Appraisal, History, Insight, Streetwise
- **Pack:** Smith's Pack or 55 gold

### Leatherworker
- **Base HP:** 8
- **Suggested Paths:** Defense or Survival
- **Feature:** Leather Guild Access
- **Armor:** Light, Medium
- **Weapons:** Simple, Light
- **Tools:** Leatherworking tools
- **Skills (choose 2):** Crafting, Nature, Appraisal, Sleight of Hand, Animal Handling, Stealth
- **Pack:** Leatherworker's Pack or 45 gold

### Artisan
- **Base HP:** 6
- **Suggested Paths:** Mystic or Survival
- **Feature:** Guild Membership
- **Armor:** Light
- **Weapons:** Simple, Light
- **Tools:** One artisan tool
- **Skills (choose 2):** Crafting, History, Insight, Appraisal, Diplomacy, Performance
- **Pack:** Artisan's Pack or 40 gold

### Warden of the Wild
- **Base HP:** 8
- **Suggested Paths:** Divine or Survival
- **Feature:** Natural Steward
- **Armor:** Light, Medium
- **Weapons:** Simple, Melee
- **Tools:** Herbal kit or hunting tools
- **Skills (choose 2):** Nature, Perception, Animal Handling, Medicine, Stealth, Athletics
- **Pack:** Warden's Pack or 50 gold

### Scholar
- **Base HP:** 8
- **Suggested Paths:** Martial or Mystic
- **Feature:** Academic Circles
- **Armor:** None
- **Weapons:** Simple
- **Skills (choose 2):** History, Religion, Arcana, Investigation, Insight, Appraisal
- **Pack:** Scholar's Pack or 35 gold

### Free Agent
- **Base HP:** 6-10 (RM approval)
- **Suggested Paths:** Match skills to path's primary ability
- **Feature:** Self-Made (Persuasion prof + rep bonus as misc)
- **Proficiencies:** Choose any 6 (armor, weapon, or tool)
- **Skills (choose 2):** Any from full skill list
- **Pack:** Any armory pack or 1d10×4 gold

---

## 4. Primary Paths

At level 1, you must spend at least 4 Talent Points on your Primary Path.

### Path Prerequisites & Bonuses

| Path | Prerequisites | Primary Bonus | TP Formula | Base Attack |
|------|---------------|---------------|------------|-------------|
| Defense | End 15+, Mgt or Int 13+ | +2 End, +2 Wis | End Mod + 5 | +1 Melee, +1 Ranged |
| Divine | Wis 15+, End or Int 13+ | +3 Wis, +3 Cha | Wis Mod + 5 | None |
| Exploitation | Agl 15+, Int or Cha 13+ | +2 Agl, +2 Int | Agl Mod + 5 | +1 Melee, +1 Ranged |
| Martial | Agl 15+, Int or Wis 13+ | +2 Agl, +2 Wis | Agl Mod + 5 | +1 Melee, +1 Ranged |
| Mystic | Int 15+, Wis or Cha 13+ | +2 Int, +2 Wis | Int Mod + 5 | +2 Ranged |
| Power | Mgt 15+, Agl or End 13+ | +2 Mgt, +2 End | Mgt Mod + 5 | +2 Melee |
| Survival | Wis 15+, Agl or End 13+ | +2 Agl, +2 Wis | Wis Mod + 5 | +2 Ranged |

### Secondary Path Rules
- Only need 15+ in ONE of the listed core abilities
- Do NOT gain primary ability bonuses
- Only gain initial abilities and proficiencies

---

## 5. Talents

### Talent Point Cost
Cost = Talent Rank (e.g., Rank 3 talent costs 3 TP)

### General Talents (available to all)

| Talent | Ranks | Prerequisite | Description |
|--------|-------|--------------|-------------|
| Alertness | 1-3 | Wis 11+ | Initiative, perception bonuses |
| Archery Focus | 1-3 | Agl 12+ | Ranged combat bonuses |
| Armor Training | 1-3 | Mgt 12+ | Armor proficiencies |
| Athlete | 1-3 | Mgt 10+ or Agl 10+ | Physical feat bonuses |
| Book Smart | 1-3 | Int 12+ | Knowledge skill bonuses |
| Common Sense | 1-3 | Wis 12+ | Perception, insight bonuses |
| Defensive Training | 1-3 | Agl 11+ or Mgt 11+ | Attack bonus, reactions |
| Dual Wielding | 1-3 | Agl 12+ | Two-weapon fighting |
| Experienced | 1-3 | Level 5/10/15 | Saving throw bonuses |
| Fighting Style | 1-3 | Mgt 12+ or Agl 12+ | Combat style choice |
| Lucky | 1-3 | None | Reroll mechanics |
| Mobile | 1-3 | Agl 12+ | Movement bonuses |
| Natural Leader | 1-3 | Cha 12+ | Ally support abilities |
| Observant | 1-3 | Int 11+ or Wis 11+ | Investigation, perception |
| Persuasive | 1-3 | Cha 12+ | Social skill bonuses |
| Quick Learner | 1-3 | Int 12+ | XP and learning bonuses |
| Quickness | 1-3 | Agl 12+ | Speed and initiative |
| Resilient | 1-3 | End 12+ | Saving throw bonuses |
| Resourceful | 1-3 | Int 12+ or Wis 12+ | Crafting, survival |
| Skill Focus | 1-3 | None | Single skill mastery |
| Tinkerer | 1-3 | Int 12+ or Artisan Tools | Crafting speed/efficiency |
| Toughness | 1-3 | End 12+ | HP and exhaustion |
| Weapon Mastery | 1-3 | Mgt 12+ or Agl 12+ | Extra attacks, reactions |

### Path-Specific Talents

Each path has:
- One core scaling talent (ranks 1-10)
- Several supporting talents (ranks 1-3 or 1-4)
- One capstone talent (requires all other path talents)

---

## 6. Backgrounds

Backgrounds provide: 2 skill proficiencies, languages or tools, equipment, a feature, and personality traits.

### Available Backgrounds
| Background | Skills | Feature |
|------------|--------|---------|
| Devotee | Insight, History | Shelter of the Faithful |
| Outcast | Stealth, Survival | Wanderer's Memory |
| Village Champion | Athletics, Persuasion | Rustic Respect |
| Scholar | Arcana, History | Researcher |
| Artisan | Investigation, Insight | Guild Bonds |
| Wanderer | Survival, Performance | Wayfarer's Lore |
| Noble Heir | Persuasion, History | Noble Privilege |
| Mercenary | Athletics, Intimidation | Mercenary Company |
| Seafarer | Athletics, Nature | Ship Passage |
| Shadow | Stealth, Investigation | Silent Network |
| Nomad | Animal Handling, Survival | Tribal Hospitality |
| Soldier | Athletics, Perception | Military Rank |

### Personality Components
Each background has tables for:
- **Traits** (d8): Quirks, habits, attitudes
- **Ideals** (d6): Core beliefs (includes Morality Points: +1/0/-1 and Rep Modifier)
- **Bonds** (d6): Ties to people/places (includes Morality Points and Rep Modifier)
- **Flaws** (d6): Weaknesses, vices (includes Morality Points and Rep Modifier)

---

## 7. Derived Statistics

### Defense
```
Defense = 9 + Agility Modifier + Shield Bonus + Misc Modifiers
```

### Health Points
```
HP = Profession Base HP + Endurance Modifier
```

### Life Points
```
LP = Value from Endurance score table
```

### Talent Points (per level)
```
TP = Primary Path Core Ability Modifier + 5
```

### Advancement Points (per level)
```
AP = Intellect Modifier (minimum 2)
```

### Morality Score
Sum of:
- Ideal Morality Value
- Bond Morality Value
- Flaw Morality Value

### Reputation Score
Sum of:
- Ideal Rep Modifier
- Bond Rep Modifier
- Flaw Rep Modifier
- Ancestry Rep Modifier (regional)

---

## 8. Morality & Alignment

| Alignment | Code | Score Range |
|-----------|------|-------------|
| Enlightened | EL | +12 or higher |
| Righteous | RI | +9 to +11 |
| Good | GD | +6 to +8 |
| Neutral Good | NG | +3 to +5 |
| True Neutral | TN | -2 to +2 |
| Neutral Bad | NB | -3 to -5 |
| Bad | BD | -6 to -8 |
| Evil | EV | -9 to -11 |
| Vile | VL | -12 or lower |

---

## 9. Reputation Scale

| Reputation | Score | Description |
|------------|-------|-------------|
| Famous | +9+ | Many regions know your generosity |
| Renowned | +6 to +8 | Known for aiding in several regions |
| Respected | +3 to +5 | Known in certain regions |
| Unknown | -2 to +2 | No impactful deeds |
| Notorious | -3 to -5 | Single region knows negative deeds |
| Infamous | -6 to -8 | Known in several regions negatively |
| Revealed | -9 or lower | Known in many regions, has bounty |

---

## 10. Skills List

| Skill | Ability |
|-------|---------|
| Acrobatics | Agility |
| Animal Handling | Wisdom |
| Appraisal | Intellect |
| Arcana | Intellect |
| Athletics | Might |
| Crafting | Intellect |
| Deception | Charisma |
| Diplomacy | Charisma |
| History | Intellect |
| Insight | Intellect |
| Intimidation | Charisma |
| Investigation | Intellect |
| Medicine | Intellect |
| Nature | Intellect |
| Perception | Wisdom |
| Performance | Charisma |
| Persuasion | Charisma |
| Religion | Intellect |
| Sleight of Hand | Agility |
| Stealth | Agility |
| Streetwise | Intellect |
| Survival | Wisdom |
| Taming | Wisdom |

---

## 11. Experience & Leveling

| XP | Level | Next Level XP | Benefit |
|----|-------|---------------|---------|
| 0 | 1 | 300 | Starting |
| 300 | 2 | 600 | — |
| 900 | 3 | 2,100 | Extra Attack |
| 3,000 | 4 | 4,000 | +2 to one or +1 to two abilities |
| 7,000 | 5 | 6,000 | — |
| 13,000 | 6 | 9,000 | — |
| 22,000 | 7 | 12,000 | — |
| 34,000 | 8 | 15,000 | +2 to one or +1 to two abilities |

---

## 12. Advancement Point Costs

| Feature | AP Cost |
|---------|---------|
| +1 rank in trained skill | 1 |
| Train new skill (+1 rank) | 4 |
| Inherit 50 GP | 5 |
| +2/+1 ability score boost | 7 |
| Learn new proficiency | 10 |
| Learn new language | 10 |

---

## 13. Mystic Spellcasting (Path-specific)

### Spellcrafting Points (SP)
```
SP per level = Intellect Modifier + Character Level
```
Used to learn new spells.

### Casting Points (CP)
```
Max CP = Intellect Modifier + Character Level
```
Expended when casting; regained on long rest.

---

## Data Structures for Programming

### Character Object
```
{
  name: string,
  race: Race,
  ancestry: Ancestry,
  profession: Profession,
  duty?: Duty,  // for Warrior profession
  primaryPath: Path,
  secondaryPaths: Path[],
  background: Background,
  
  abilityScores: {
    might: number,
    agility: number,
    endurance: number,
    wisdom: number,
    intellect: number,
    charisma: number
  },
  
  abilityModifiers: { /* calculated */ },
  
  skills: Skill[],
  trainedSkills: string[],
  
  talents: {
    general: Talent[],
    path: Talent[]
  },
  
  proficiencies: {
    armor: string[],
    weapons: string[],
    tools: string[],
    languages: string[]
  },
  
  derivedStats: {
    defense: number,
    healthPoints: number,
    lifePoints: number,
    talentPoints: number,
    advancementPoints: number,
    meleeAttackBonus: number,
    rangedAttackBonus: number
  },
  
  morality: {
    score: number,
    alignment: string
  },
  
  reputation: {
    score: number,
    level: string
  },
  
  personality: {
    traits: string[],
    ideals: { text: string, moralityValue: number, repModifier: number }[],
    bonds: { text: string, moralityValue: number, repModifier: number }[],
    flaws: { text: string, moralityValue: number, repModifier: number }[]
  },
  
  equipment: Item[],
  gold: number,
  
  level: number,
  experiencePoints: number
}
```

---

## Validation Rules

1. **Path Prerequisites:** Must have 15+ in BOTH core abilities for Primary Path
2. **Talent Prerequisites:** Check ability score and level requirements
3. **Level 1 TP Spending:** Must spend at least 4 TP on Primary Path
4. **Point Buy:** Must spend exactly 30 points, scores 8-15
5. **Ability Score Adjustments:** Apply race, ancestry, then path bonuses (Primary only)
6. **Small Races:** (Halffolk, Goblin) have disadvantage with Heavy weapons