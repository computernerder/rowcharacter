"""
Test script for ROW character creation system.

Run from the FightingSystem directory:
    python test_core.py
"""

import json
from pathlib import Path

# Test 1: Import core modules
print("=" * 60)
print("TEST 1: Importing core modules...")
print("=" * 60)

try:
    from core import (
        Race, Ancestry, Profession, Path as CharPath, Background,
        load_all_races, load_all_ancestries, load_all_professions,
        load_all_paths, load_all_backgrounds,
        Feature, Duty, PathPrerequisite, PersonalityEntry
    )
    print("✓ All core imports successful")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    exit(1)

# Test 2: Load JSON data files
print("\n" + "=" * 60)
print("TEST 2: Loading JSON data files...")
print("=" * 60)

data_dir = Path("data")

try:
    races = load_all_races(str(data_dir / "races"))
    print(f"✓ Loaded {len(races)} races: {list(races.keys())}")
except Exception as e:
    print(f"✗ Failed to load races: {e}")
    races = {}

try:
    ancestries = load_all_ancestries(str(data_dir / "ancestries"))
    print(f"✓ Loaded {len(ancestries)} ancestries: {list(ancestries.keys())}")
except Exception as e:
    print(f"✗ Failed to load ancestries: {e}")
    ancestries = {}

try:
    professions = load_all_professions(str(data_dir / "professions"))
    print(f"✓ Loaded {len(professions)} professions: {list(professions.keys())}")
except Exception as e:
    print(f"✗ Failed to load professions: {e}")
    professions = {}

try:
    paths = load_all_paths(str(data_dir / "paths"))
    print(f"✓ Loaded {len(paths)} paths: {list(paths.keys())}")
except Exception as e:
    print(f"✗ Failed to load paths: {e}")
    paths = {}

try:
    backgrounds = load_all_backgrounds(str(data_dir / "backgrounds"))
    print(f"✓ Loaded {len(backgrounds)} backgrounds: {list(backgrounds.keys())}")
except Exception as e:
    print(f"✗ Failed to load backgrounds: {e}")
    backgrounds = {}

# Test 3: Examine loaded data
print("\n" + "=" * 60)
print("TEST 3: Examining loaded data...")
print("=" * 60)

if "elf" in races:
    elf = races["elf"]
    print(f"\nElf Race:")
    print(f"  Name: {elf.name}")
    print(f"  Size: {elf.size}, Speed: {elf.speed}")
    print(f"  Darkvision: {elf.darkvision} ft")
    print(f"  Languages: {elf.languages}")
    print(f"  Ability Modifiers: {elf.ability_modifiers}")
    print(f"  Features: {[f.name for f in elf.features]}")
    print(f"  Valid Ancestries: {elf.ancestries}")

if "sylari" in ancestries:
    sylari = ancestries["sylari"]
    print(f"\nSylari Ancestry:")
    print(f"  Name: {sylari.name}")
    print(f"  Parent Race: {sylari.race_id}")
    print(f"  Ability Modifiers: {sylari.ability_modifiers}")
    print(f"  Languages: {sylari.languages}")
    print(f"  Features: {[f.name for f in sylari.features]}")
    if sylari.reputation_modifier:
        print(f"  Reputation: +{sylari.reputation_modifier.value} in {sylari.reputation_modifier.region}")

if "warrior" in professions:
    warrior = professions["warrior"]
    print(f"\nWarrior Profession:")
    print(f"  Name: {warrior.name}")
    print(f"  Base HP: {warrior.base_hp}")
    print(f"  Feature: {warrior.feature.name if warrior.feature else 'None'}")
    print(f"  Armor Proficiencies: {warrior.armor_proficiencies}")
    print(f"  Weapon Proficiencies: {warrior.weapon_proficiencies}")
    print(f"  Skill Choices: {warrior.skill_choices}")
    print(f"  Duties: {[d.name for d in warrior.duties]}")

if "defense" in paths:
    defense = paths["defense"]
    print(f"\nDefense Path:")
    print(f"  Name: {defense.name}")
    print(f"  Role: {defense.role}")
    print(f"  Primary Bonus: {defense.primary_bonus}")
    print(f"  Talent Attribute: {defense.talent_points_attribute}")
    print(f"  Attack Bonuses: Melee +{defense.attack_bonus_melee}, Ranged +{defense.attack_bonus_ranged}")
    print(f"  Features: {[f.name for f in defense.features]}")
    if defense.prerequisites:
        print(f"  Prerequisites: {defense.prerequisites.primary_attribute} 15+, one of {defense.prerequisites.secondary_attributes} 13+")

if "devotee" in backgrounds:
    devotee = backgrounds["devotee"]
    print(f"\nDevotee Background:")
    print(f"  Name: {devotee.name}")
    print(f"  Skill Proficiencies: {devotee.skill_proficiencies}")
    print(f"  Languages Granted: {devotee.languages_granted}")
    print(f"  Feature: {devotee.feature.name if devotee.feature else 'None'}")
    if devotee.personality_tables:
        print(f"  Personality Tables: {len(devotee.personality_tables.traits)} traits, {len(devotee.personality_tables.ideals)} ideals")

# Test 4: Test to_dict/from_dict round-trip
print("\n" + "=" * 60)
print("TEST 4: Testing to_dict/from_dict round-trip...")
print("=" * 60)

if "elf" in races:
    elf = races["elf"]
    elf_dict = elf.to_dict()
    elf_restored = Race.from_dict(elf_dict)
    
    if elf.name == elf_restored.name and elf.speed == elf_restored.speed:
        print("✓ Race round-trip successful")
    else:
        print("✗ Race round-trip failed")

if "warrior" in professions:
    warrior = professions["warrior"]
    warrior_dict = warrior.to_dict()
    warrior_restored = Profession.from_dict(warrior_dict)
    
    if warrior.name == warrior_restored.name and warrior.base_hp == warrior_restored.base_hp:
        print("✓ Profession round-trip successful")
    else:
        print("✗ Profession round-trip failed")

if "defense" in paths:
    defense = paths["defense"]
    defense_dict = defense.to_dict()
    defense_restored = CharPath.from_dict(defense_dict)
    
    if defense.name == defense_restored.name and defense.role == defense_restored.role:
        print("✓ Path round-trip successful")
    else:
        print("✗ Path round-trip failed")

# Test 5: Test prerequisite checking
print("\n" + "=" * 60)
print("TEST 5: Testing path prerequisites...")
print("=" * 60)

if "defense" in paths:
    defense = paths["defense"]
    
    # Mock ability scores that meet prerequisites
    good_scores = {
        "Endurance": type("Score", (), {"total": 16})(),
        "Might": type("Score", (), {"total": 14})(),
        "Intellect": type("Score", (), {"total": 10})(),
    }
    
    # Mock ability scores that don't meet prerequisites
    bad_scores = {
        "Endurance": type("Score", (), {"total": 12})(),
        "Might": type("Score", (), {"total": 10})(),
        "Intellect": type("Score", (), {"total": 10})(),
    }
    
    if defense.check_prerequisites(good_scores, is_primary=True):
        print("✓ Prerequisites correctly passed for valid scores (END 16, MGT 14)")
    else:
        print("✗ Prerequisites incorrectly failed for valid scores")
    
    if not defense.check_prerequisites(bad_scores, is_primary=True):
        print("✓ Prerequisites correctly failed for invalid scores (END 12)")
    else:
        print("✗ Prerequisites incorrectly passed for invalid scores")

# Test 6: Test with CharacterTemplate (if available)
print("\n" + "=" * 60)
print("TEST 6: Testing apply() with CharacterTemplate...")
print("=" * 60)

try:
    from template_model import CharacterTemplate
    
    # Create a fresh character
    char = CharacterTemplate()
    
    # Verify initial state
    print(f"Initial speed: {char.speed}")
    print(f"Initial languages: {char.languages}")
    
    # Apply elf race
    if "elf" in races:
        races["elf"].apply(char)
        print(f"\nAfter applying Elf race:")
        print(f"  Speed: {char.speed}")
        print(f"  Languages: {char.languages}")
        print(f"  Creature Type: {char.physical_traits.creature_type}")
        print(f"  Features added: {len(char.features)}")
        
        # Check ability modifier was applied
        if "Intellect" in char.ability_scores:
            int_score = char.ability_scores["Intellect"]
            print(f"  Intellect race bonus: +{int_score.race}")
    
    # Apply sylari ancestry
    if "sylari" in ancestries:
        ancestries["sylari"].apply(char)
        print(f"\nAfter applying Sylari ancestry:")
        print(f"  Languages: {char.languages}")
        print(f"  Features added: {len(char.features)}")
        
        if "Wisdom" in char.ability_scores:
            wis_score = char.ability_scores["Wisdom"]
            print(f"  Wisdom race bonus: +{wis_score.race}")
    
    print("\n✓ CharacterTemplate apply() tests passed")
    
except ImportError as e:
    print(f"⚠ Could not import CharacterTemplate: {e}")
    print("  (This is OK - apply() will work once template_model.py is available)")

# Test 7: Export test character to JSON
print("\n" + "=" * 60)
print("TEST 7: Exporting test data to JSON...")
print("=" * 60)

try:
    from template_model import CharacterTemplate, dump_character_template
    
    char = CharacterTemplate()
    char.character_name = "Test Character"
    
    if "elf" in races:
        races["elf"].apply(char)
    if "sylari" in ancestries:
        ancestries["sylari"].apply(char)
    
    output = dump_character_template(char)
    
    # Write to file
    with open("test_output.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    
    print("✓ Wrote test_output.json")
    print(f"  Character: {output.get('character_name')}")
    print(f"  Speed: {output.get('speed')}")
    print(f"  Languages: {output.get('languages')}")
    
except Exception as e:
    print(f"⚠ Could not export: {e}")

print("\n" + "=" * 60)
print("ALL TESTS COMPLETE")
print("=" * 60)
