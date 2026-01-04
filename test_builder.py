"""
Test script for the CharacterBuilder.

Run from the FightingSystem directory:
    python test_builder.py
"""

import json

print("=" * 60)
print("CHARACTER BUILDER TEST")
print("=" * 60)

# Import the builder
from character_builder import CharacterBuilder, BuilderStep

# Create a new builder
builder = CharacterBuilder()

# Load game data
print("\n1. Loading game data...")
builder.load_game_data("data")
print(f"   Loaded {len(builder.races)} races")
print(f"   Loaded {len(builder.ancestries)} ancestries")
print(f"   Loaded {len(builder.professions)} professions")
print(f"   Loaded {len(builder.paths)} paths")
print(f"   Loaded {len(builder.backgrounds)} backgrounds")

# Set ability scores (standard array: 15, 14, 13, 12, 10, 8)
print("\n2. Setting ability scores...")
builder.set_ability_scores({
    "Might": 10,
    "Agility": 14,
    "Endurance": 13,
    "Intellect": 15,
    "Wisdom": 12,
    "Charisma": 8,
})
print(f"   Current step: {builder.current_step.name}")

# Show available races
print("\n3. Available races:")
for race in builder.get_available_races():
    print(f"   - {race.id}: {race.name} (Speed {race.speed}, Darkvision {race.darkvision})")

# Choose elf
print("\n4. Choosing Elf race...")
builder.set_race("elf")
print(f"   Current step: {builder.current_step.name}")
print(f"   Pending choices: {len(builder.pending_choices)}")
for choice in builder.pending_choices:
    print(f"     - {choice.source}: {choice.count} {choice.choice_type}")

# Show available ancestries for elf
print("\n5. Available ancestries for Elf:")
for ancestry in builder.get_available_ancestries():
    print(f"   - {ancestry.id}: {ancestry.name} ({ancestry.ability_modifiers})")

# Choose sylari
print("\n6. Choosing Sylari ancestry...")
builder.set_ancestry("sylari")
print(f"   Current step: {builder.current_step.name}")

# Show available professions
print("\n7. Available professions:")
for prof in builder.get_available_professions():
    duties = f" (Duties: {[d.name for d in prof.duties]})" if prof.duties else ""
    print(f"   - {prof.id}: {prof.name} (HP {prof.base_hp}){duties}")

# Choose scholar (no duties)
print("\n8. Choosing Scholar profession...")
builder.set_profession("scholar")
print(f"   Current step: {builder.current_step.name}")
print(f"   Pending choices: {len(builder.pending_choices)}")
for choice in builder.pending_choices:
    print(f"     - {choice.source}: Choose {choice.count} from {choice.options}")

# Resolve skill choices for scholar
print("\n9. Resolving profession skill choices (Arcana, History)...")
builder.resolve_choice("skill", ["Arcana", "History"], source="Scholar Profession")
print(f"   Pending choices remaining: {len(builder.pending_choices)}")

# Show available paths
print("\n10. Available paths:")
for path, meets_prereq in builder.get_available_paths():
    status = "✓" if meets_prereq else "✗"
    print(f"   {status} {path.id}: {path.name} (requires {path.prerequisites.primary_attribute} 15+)")

# Choose mystic (INT-based, should meet prereqs with INT 15)
print("\n11. Choosing Mystic path...")
builder.set_path("mystic")
print(f"   Current step: {builder.current_step.name}")

# Show available backgrounds
print("\n12. Available backgrounds:")
for bg in builder.get_available_backgrounds():
    print(f"   - {bg.id}: {bg.name} (Skills: {bg.skill_proficiencies})")

# Choose scholar background
print("\n13. Choosing Scholar background...")
builder.set_background("scholar")
print(f"   Current step: {builder.current_step.name}")
print(f"   Pending choices: {len(builder.pending_choices)}")

# Resolve pending choices
print("\n14. Resolving pending choices...")
for choice in list(builder.pending_choices):
    print(f"   Resolving {choice.choice_type} from {choice.source}...")
    
    if choice.choice_type == "language":
        # Pick first available options
        selections = choice.options[:choice.count]
        builder.resolve_choice("language", selections, source=choice.source)
        print(f"     Selected: {selections}")
    
    elif choice.choice_type.startswith("personality_"):
        # Pick first option
        builder.resolve_choice(choice.choice_type, [choice.options[0]], source=choice.source)
        print(f"     Selected: {choice.options[0][:50]}...")

print(f"\n   Remaining pending choices: {len(builder.pending_choices)}")

# Check completion
print("\n15. Checking completion...")
print(f"   Is complete: {builder.is_complete()}")

# Get the finished character
print("\n16. Getting finished character...")
character = builder.get_character()

# Print summary
print("\n" + "=" * 60)
print("CHARACTER SUMMARY")
print("=" * 60)
print(builder.get_summary())

# Print some stats
print("\n" + "-" * 40)
print("ABILITY SCORES:")
for name, score in character.ability_scores.items():
    print(f"  {name}: {score.total} (mod {score.mod:+d}, race {score.race:+d}, misc {score.misc:+d})")

print("\nDERIVED STATS:")
print(f"  Speed: {character.speed}")
print(f"  Defense: {character.defense.total}")
print(f"  Initiative: {character.initiative}")
print(f"  HP: {character.health.max}")
print(f"  Life Points: {character.life_points.max}")

print("\nSKILLS (trained):")
for name, entry in character.skills.items():
    if entry.trained:
        print(f"  {name}: {entry.total:+d} (mod {entry.mod:+d}, rank {entry.rank})")

print("\nLANGUAGES:", character.languages)
print("PROFICIENCIES:", character.proficiencies)

print("\nFEATURES:")
for f in character.features:
    name = f.get("name", f.name if hasattr(f, "name") else "?")
    print(f"  - {name}")

# Export to JSON
print("\n17. Exporting to JSON...")
from template_model import dump_character_template
output = dump_character_template(character)
with open("test_built_character.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)
print("   Wrote test_built_character.json")

print("\n" + "=" * 60)
print("ALL TESTS COMPLETE")
print("=" * 60)
