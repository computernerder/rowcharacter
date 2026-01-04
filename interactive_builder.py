"""
Interactive Character Builder CLI

Run from the FightingSystem directory:
    python interactive_builder.py
"""

import json
import os
from typing import List, Optional

from character_builder import CharacterBuilder, BuilderStep, PendingChoice
from template_model import dump_character_template


def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(title: str):
    """Print a section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_subheader(title: str):
    """Print a subsection header."""
    print("\n" + "-" * 40)
    print(f"  {title}")
    print("-" * 40)


def get_choice(prompt: str, options: List[str], allow_back: bool = True) -> Optional[str]:
    """
    Present options and get user choice.
    
    Returns None if user chooses to go back.
    """
    print()
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    
    if allow_back:
        print(f"  0. Go back")
    
    while True:
        try:
            choice = input(f"\n{prompt} > ").strip()
            
            if choice == "0" and allow_back:
                return None
            
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx]
            else:
                print(f"  Please enter 1-{len(options)}")
        except ValueError:
            # Maybe they typed the option name directly
            if choice in options:
                return choice
            # Check if it's a partial match
            matches = [o for o in options if choice.lower() in o.lower()]
            if len(matches) == 1:
                return matches[0]
            print(f"  Please enter a number 1-{len(options)}")


def get_multiple_choices(prompt: str, options: List[str], count: int) -> Optional[List[str]]:
    """
    Get multiple selections from options.
    
    Returns None if user chooses to go back.
    """
    print()
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    
    print(f"\n  Select {count} options (comma-separated numbers, or 0 to go back)")
    
    while True:
        choice = input(f"\n{prompt} > ").strip()
        
        if choice == "0":
            return None
        
        try:
            indices = [int(x.strip()) - 1 for x in choice.split(",")]
            
            if len(indices) != count:
                print(f"  Please select exactly {count} options")
                continue
            
            if any(i < 0 or i >= len(options) for i in indices):
                print(f"  Invalid selection. Use numbers 1-{len(options)}")
                continue
            
            if len(set(indices)) != len(indices):
                print("  Please select different options (no duplicates)")
                continue
            
            return [options[i] for i in indices]
            
        except ValueError:
            print(f"  Enter {count} comma-separated numbers (e.g., 1,3)")


def show_current_character(builder: CharacterBuilder):
    """Display current character state."""
    print_subheader("Current Character")
    
    char = builder.character
    
    # Basic info
    if builder.chosen_race:
        print(f"  Race: {builder.chosen_race.name}", end="")
        if builder.chosen_ancestry:
            print(f" / {builder.chosen_ancestry.name}")
        else:
            print()
    
    if builder.chosen_profession:
        print(f"  Profession: {builder.chosen_profession.name}", end="")
        if builder.chosen_duty:
            print(f" ({builder.chosen_duty.name})")
        else:
            print()
    
    if builder.chosen_path:
        print(f"  Path: {builder.chosen_path.name}")
    
    if builder.chosen_background:
        print(f"  Background: {builder.chosen_background.name}")
    
    # Ability scores
    print("\n  Ability Scores:")
    for name, score in char.ability_scores.items():
        parts = [f"{score.total}"]
        if score.race != 0:
            parts.append(f"race {score.race:+d}")
        if score.misc != 0:
            parts.append(f"misc {score.misc:+d}")
        print(f"    {name:12} {score.total:2d} (mod {score.mod:+d}) [{', '.join(parts[1:]) if len(parts) > 1 else 'base'}]")
    
    # Languages
    if char.languages:
        print(f"\n  Languages: {', '.join(char.languages)}")
    
    # Proficiencies
    if char.proficiencies:
        print(f"  Proficiencies: {', '.join(char.proficiencies)}")
    
    # Trained skills
    trained = [name for name, entry in char.skills.items() if entry.trained]
    if trained:
        print(f"  Trained Skills: {', '.join(trained)}")
    
    # Features
    if char.features:
        print(f"\n  Features ({len(char.features)}):")
        for f in char.features[:5]:  # Show first 5
            name = f.get("name", f.name if hasattr(f, "name") else "?")
            print(f"    - {name}")
        if len(char.features) > 5:
            print(f"    ... and {len(char.features) - 5} more")


def step_ability_scores(builder: CharacterBuilder) -> bool:
    """Handle ability score assignment."""
    print_header("STEP 1: ABILITY SCORES")
    
    print("\n  Choose a method:")
    print("  1. Standard Array (15, 14, 13, 12, 10, 8)")
    print("  2. Manual Entry")
    print("  3. Quick Test (all 12s)")
    
    method = input("\n  Method > ").strip()
    
    if method == "1":
        # Standard array assignment
        array = [15, 14, 13, 12, 10, 8]
        attributes = ["Might", "Agility", "Endurance", "Intellect", "Wisdom", "Charisma"]
        scores = {}
        
        print("\n  Assign scores to abilities:")
        remaining = array.copy()
        
        for attr in attributes:
            print(f"\n  {attr} - Available: {remaining}")
            while True:
                try:
                    val = int(input(f"  {attr} > ").strip())
                    if val in remaining:
                        scores[attr] = val
                        remaining.remove(val)
                        break
                    else:
                        print(f"    Choose from: {remaining}")
                except ValueError:
                    print(f"    Enter a number from: {remaining}")
        
        builder.set_ability_scores(scores)
        return True
    
    elif method == "2":
        # Manual entry
        scores = {}
        attributes = ["Might", "Agility", "Endurance", "Intellect", "Wisdom", "Charisma"]
        
        print("\n  Enter score for each ability (8-18):")
        for attr in attributes:
            while True:
                try:
                    val = int(input(f"  {attr} > ").strip())
                    if 3 <= val <= 20:
                        scores[attr] = val
                        break
                    else:
                        print("    Enter a value between 3 and 20")
                except ValueError:
                    print("    Enter a number")
        
        builder.set_ability_scores(scores)
        return True
    
    elif method == "3":
        # Quick test - all 12s
        builder.set_ability_scores({
            "Might": 12,
            "Agility": 12,
            "Endurance": 12,
            "Intellect": 12,
            "Wisdom": 12,
            "Charisma": 12,
        })
        print("\n  Set all abilities to 12")
        return True
    
    return False


def step_race(builder: CharacterBuilder) -> bool:
    """Handle race selection."""
    print_header("STEP 2: CHOOSE RACE")
    
    races = builder.get_available_races()
    
    print("\n  Available Races:")
    for i, race in enumerate(races, 1):
        mods = ", ".join(f"{k} {v:+d}" for k, v in race.ability_modifiers.items()) or "flexible"
        features = ", ".join(f.name for f in race.features[:2])
        print(f"\n  {i}. {race.name}")
        print(f"     Size: {race.size}, Speed: {race.speed} ft")
        if race.darkvision:
            print(f"     Darkvision: {race.darkvision} ft")
        print(f"     Abilities: {mods}")
        print(f"     Features: {features}")
        print(f"     Languages: {', '.join(race.languages)}")
    
    choice = get_choice("Select race", [r.id for r in races], allow_back=False)
    
    if choice:
        builder.set_race(choice)
        print(f"\n  ✓ Selected {builder.chosen_race.name}")
        return True
    
    return False


def step_ancestry(builder: CharacterBuilder) -> bool:
    """Handle ancestry selection."""
    print_header("STEP 3: CHOOSE ANCESTRY")
    
    ancestries = builder.get_available_ancestries()
    
    if not ancestries:
        print("\n  No ancestries available for this race.")
        print("  (You may need to add ancestry JSON files)")
        input("\n  Press Enter to continue...")
        builder.current_step = BuilderStep.PROFESSION
        return True
    
    print(f"\n  Available Ancestries for {builder.chosen_race.name}:")
    for i, anc in enumerate(ancestries, 1):
        mods = ", ".join(f"{k} {v:+d}" for k, v in anc.ability_modifiers.items()) or "none"
        features = ", ".join(f.name for f in anc.features)
        print(f"\n  {i}. {anc.name}")
        print(f"     Region: {anc.region}")
        print(f"     Abilities: {mods}")
        if anc.languages:
            print(f"     Languages: {', '.join(anc.languages)}")
        if features:
            print(f"     Features: {features}")
        if anc.reputation_modifier:
            print(f"     Reputation: +{anc.reputation_modifier.value} in {anc.reputation_modifier.region}")
    
    choice = get_choice("Select ancestry", [a.id for a in ancestries])
    
    if choice:
        builder.set_ancestry(choice)
        print(f"\n  ✓ Selected {builder.chosen_ancestry.name}")
        return True
    
    return False


def step_profession(builder: CharacterBuilder) -> bool:
    """Handle profession selection."""
    print_header("STEP 4: CHOOSE PROFESSION")
    
    professions = builder.get_available_professions()
    
    print("\n  Available Professions:")
    for i, prof in enumerate(professions, 1):
        print(f"\n  {i}. {prof.name}")
        print(f"     Base HP: {prof.base_hp}")
        if prof.feature:
            print(f"     Feature: {prof.feature.name}")
        print(f"     Armor: {', '.join(prof.armor_proficiencies) or 'None'}")
        print(f"     Weapons: {', '.join(prof.weapon_proficiencies) or 'None'}")
        if prof.skill_choices:
            print(f"     Skills: Choose {prof.skill_choices['count']} from {prof.skill_choices['options']}")
        if prof.duties:
            print(f"     Duties: {', '.join(d.name for d in prof.duties)}")
    
    choice = get_choice("Select profession", [p.id for p in professions])
    
    if choice is None:
        return False
    
    prof = builder.professions[choice]
    
    # Handle duty selection if needed
    duty_id = None
    if prof.duties:
        print(f"\n  {prof.name} requires choosing a Duty:")
        for i, duty in enumerate(prof.duties, 1):
            print(f"\n  {i}. {duty.name}")
            print(f"     {duty.description}")
            print(f"     Suggested Paths: {', '.join(duty.suggested_paths)}")
            if duty.armor_proficiencies:
                print(f"     Extra Armor: {', '.join(duty.armor_proficiencies)}")
            if duty.weapon_proficiencies:
                print(f"     Extra Weapons: {', '.join(duty.weapon_proficiencies)}")
        
        duty_choice = get_choice("Select duty", [d.id for d in prof.duties])
        if duty_choice is None:
            return False
        duty_id = duty_choice
    
    builder.set_profession(choice, duty_id=duty_id)
    print(f"\n  ✓ Selected {builder.chosen_profession.name}")
    if builder.chosen_duty:
        print(f"    Duty: {builder.chosen_duty.name}")
    
    return True


def step_path(builder: CharacterBuilder) -> bool:
    """Handle path selection."""
    print_header("STEP 5: CHOOSE PATH")
    
    paths_with_prereqs = builder.get_available_paths()
    
    print("\n  Available Paths:")
    for i, (path, meets) in enumerate(paths_with_prereqs, 1):
        status = "✓" if meets else "✗"
        prereq = path.prerequisites
        print(f"\n  {i}. [{status}] {path.name}")
        print(f"     Role: {path.role}")
        if prereq:
            print(f"     Requires: {prereq.primary_attribute} {prereq.primary_minimum}+, one of {prereq.secondary_attributes} {prereq.secondary_minimum}+")
        print(f"     Primary Bonus: {path.primary_bonus}")
        print(f"     Attack Bonus: Melee +{path.attack_bonus_melee}, Ranged +{path.attack_bonus_ranged}")
        features = ", ".join(f.name for f in path.features[:2])
        if features:
            print(f"     Features: {features}")
    
    # Show current ability scores for reference
    print("\n  Your Ability Scores:")
    for name, score in builder.character.ability_scores.items():
        print(f"    {name}: {score.total}")
    
    choice = get_choice("Select path", [p.id for p, _ in paths_with_prereqs])
    
    if choice is None:
        return False
    
    # Check if they picked one they don't qualify for
    path = builder.paths[choice]
    meets = path.check_prerequisites(builder.character.ability_scores, is_primary=True)
    
    if not meets:
        print(f"\n  ⚠ You don't meet the prerequisites for {path.name}!")
        print("  1. Choose anyway (ignore prerequisites)")
        print("  2. Pick a different path")
        
        override = input("\n  > ").strip()
        if override != "1":
            return False
        
        builder.set_path(choice, ignore_prerequisites=True)
    else:
        builder.set_path(choice)
    
    print(f"\n  ✓ Selected {builder.chosen_path.name}")
    return True


def step_background(builder: CharacterBuilder) -> bool:
    """Handle background selection."""
    print_header("STEP 6: CHOOSE BACKGROUND")
    
    backgrounds = builder.get_available_backgrounds()
    
    print("\n  Available Backgrounds:")
    for i, bg in enumerate(backgrounds, 1):
        print(f"\n  {i}. {bg.name}")
        print(f"     {bg.description[:80]}...")
        print(f"     Skills: {', '.join(bg.skill_proficiencies)}")
        if bg.languages_granted:
            print(f"     Languages: Choose {bg.languages_granted}")
        if bg.feature:
            print(f"     Feature: {bg.feature.name}")
    
    choice = get_choice("Select background", [b.id for b in backgrounds])
    
    if choice is None:
        return False
    
    builder.set_background(choice)
    print(f"\n  ✓ Selected {builder.chosen_background.name}")
    return True


def resolve_pending_choices(builder: CharacterBuilder):
    """Handle all pending choices."""
    while builder.pending_choices:
        print_header("PENDING CHOICES")
        
        choice = builder.pending_choices[0]
        
        print(f"\n  From: {choice.source}")
        print(f"  Type: {choice.choice_type}")
        print(f"  Choose {choice.count}:")
        
        if choice.count == 1:
            selection = get_choice("Select", choice.options, allow_back=False)
            if selection:
                builder.resolve_choice(choice.choice_type, [selection], source=choice.source)
                print(f"\n  ✓ Selected: {selection}")
        else:
            selections = get_multiple_choices("Select", choice.options, choice.count)
            if selections:
                builder.resolve_choice(choice.choice_type, selections, source=choice.source)
                print(f"\n  ✓ Selected: {', '.join(selections)}")
        
        input("\n  Press Enter to continue...")


def finalize_character(builder: CharacterBuilder):
    """Finalize and export the character."""
    print_header("FINALIZE CHARACTER")
    
    # Set character name
    name = input("\n  Character Name > ").strip()
    if name:
        builder.character.character_name = name
    
    player = input("  Player Name > ").strip()
    if player:
        builder.character.player = player
    
    # Recalculate everything
    builder.recalculate_all()
    
    # Show final character
    show_current_character(builder)
    
    # Show derived stats
    char = builder.character
    print_subheader("Derived Stats")
    print(f"  Speed: {char.speed} ft")
    print(f"  Defense: {char.defense.total} (Base {char.defense.base} + Agi {char.defense.agility})")
    print(f"  Initiative: {char.initiative:+d}")
    print(f"  HP: {char.health.max}")
    print(f"  Life Points: {char.life_points.max}")
    print(f"  Passive Perception: {char.passive_perception.total}")
    print(f"  Passive Insight: {char.passive_insight.total}")
    print(f"  Melee Attack: {char.attack_mods_melee.total:+d}")
    print(f"  Ranged Attack: {char.attack_mods_ranged.total:+d}")
    
    # Export options
    print_subheader("Export")
    print("  1. Save to JSON file")
    print("  2. Print JSON to screen")
    print("  3. Done (exit)")
    
    export = input("\n  > ").strip()
    
    if export == "1":
        filename = input("  Filename (default: character.json) > ").strip()
        if not filename:
            filename = "character.json"
        if not filename.endswith(".json"):
            filename += ".json"
        
        output = dump_character_template(char)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
        print(f"\n  ✓ Saved to {filename}")
    
    elif export == "2":
        output = dump_character_template(char)
        print("\n" + json.dumps(output, indent=2))
    
    input("\n  Press Enter to exit...")


def main():
    """Main interactive builder loop."""
    clear_screen()
    print_header("REALM OF WARRIORS - CHARACTER BUILDER")
    print("\n  Interactive character creation wizard")
    print("  Type numbers to select options, or 0 to go back")
    
    input("\n  Press Enter to begin...")
    
    # Create builder and load data
    builder = CharacterBuilder()
    
    print("\n  Loading game data...")
    try:
        builder.load_game_data("data")
        print(f"  ✓ Loaded {len(builder.races)} races, {len(builder.ancestries)} ancestries")
        print(f"  ✓ Loaded {len(builder.professions)} professions, {len(builder.paths)} paths")
        print(f"  ✓ Loaded {len(builder.backgrounds)} backgrounds")
    except Exception as e:
        print(f"  ✗ Error loading data: {e}")
        print("\n  Make sure the 'data' folder exists with JSON files.")
        input("\n  Press Enter to exit...")
        return
    
    input("\n  Press Enter to continue...")
    
    # Step through character creation
    steps = [
        (BuilderStep.ABILITY_SCORES, step_ability_scores),
        (BuilderStep.RACE, step_race),
        (BuilderStep.ANCESTRY, step_ancestry),
        (BuilderStep.PROFESSION, step_profession),
        (BuilderStep.PATH, step_path),
        (BuilderStep.BACKGROUND, step_background),
    ]
    
    current_step_idx = 0
    
    while current_step_idx < len(steps):
        clear_screen()
        
        # Show current character state
        if current_step_idx > 0:
            show_current_character(builder)
        
        # Run current step
        step_enum, step_func = steps[current_step_idx]
        
        if step_func(builder):
            # Resolve any pending choices before moving on
            if builder.pending_choices:
                resolve_pending_choices(builder)
            current_step_idx += 1
        else:
            # Go back
            if current_step_idx > 0:
                current_step_idx -= 1
                print("\n  (Going back - note: previous choices are still applied)")
                input("  Press Enter...")
    
    # Finalize
    clear_screen()
    finalize_character(builder)


if __name__ == "__main__":
    main()
