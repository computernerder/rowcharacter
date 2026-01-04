"""
Interactive Character Builder CLI

Run from the FightingSystem directory:
    python interactive_builder.py
"""

import json
import os
import textwrap
import random
from typing import List, Optional, Set

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


def wrap_text(text: str, width: int = 55, indent: str = "       ") -> str:
    """Wrap text to specified width with indent for continuation lines."""
    lines = textwrap.wrap(text, width=width)
    if not lines:
        return ""
    return "\n".join([lines[0]] + [indent + line for line in lines[1:]])


def get_choice(prompt: str, options: List[str], disabled: Set[str] = None, 
               allow_back: bool = True) -> Optional[str]:
    """
    Present options and get user choice.
    Disabled options are shown but not selectable.
    
    Returns None if user chooses to go back.
    """
    disabled = disabled or set()
    
    print()
    for i, opt in enumerate(options, 1):
        if opt in disabled:
            print(f"  {i}. {opt} [already selected]")
        else:
            print(f"  {i}. {opt}")
    
    if allow_back:
        print(f"  0. Go back")
    
    # Build list of valid indices
    valid_indices = [i for i, opt in enumerate(options) if opt not in disabled]
    
    while True:
        try:
            choice = input(f"\n{prompt} > ").strip()
            
            if choice == "0" and allow_back:
                return None
            
            idx = int(choice) - 1
            if idx in valid_indices:
                return options[idx]
            elif 0 <= idx < len(options):
                print(f"  That option is already selected")
            else:
                print(f"  Please enter 1-{len(options)}")
        except ValueError:
            # Maybe they typed the option name directly
            if choice in options and choice not in disabled:
                return choice
            # Check if it's a partial match
            matches = [o for o in options if choice.lower() in o.lower() and o not in disabled]
            if len(matches) == 1:
                return matches[0]
            print(f"  Please enter a number 1-{len(options)}")


def get_multiple_choices(prompt: str, options: List[str], count: int, 
                         disabled: Set[str] = None) -> Optional[List[str]]:
    """
    Get multiple selections from options.
    Disabled options are shown but not selectable.
    
    Returns None if user chooses to go back.
    """
    disabled = disabled or set()
    
    print()
    for i, opt in enumerate(options, 1):
        if opt in disabled:
            print(f"  {i}. {opt} [already selected]")
        else:
            print(f"  {i}. {opt}")
    
    # Count available options
    available = [i for i, opt in enumerate(options) if opt not in disabled]
    if len(available) < count:
        print(f"\n  Warning: Only {len(available)} options available, need {count}")
        count = len(available)
    
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
            
            # Check if any selected options are disabled
            selected = [options[i] for i in indices]
            disabled_selected = [s for s in selected if s in disabled]
            if disabled_selected:
                print(f"  Cannot select already-chosen options: {', '.join(disabled_selected)}")
                continue
            
            return selected
            
        except ValueError:
            print(f"  Enter {count} comma-separated numbers (e.g., 1,3)")


def get_trained_skills(builder: CharacterBuilder) -> Set[str]:
    """Get set of already-trained skill names."""
    return {name for name, entry in builder.character.skills.items() if entry.trained}


def get_known_languages(builder: CharacterBuilder) -> Set[str]:
    """Get set of already-known languages."""
    return set(builder.character.languages)


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


def show_path_availability(builder: CharacterBuilder):
    """Display which primary paths the current ability scores qualify for."""
    if not builder.paths:
        return

    print("\n  Path availability (primary requires 15+ in primary and 13+ in a secondary):")
    for path, meets in builder.get_available_paths():
        prereq = path.prerequisites
        if prereq:
            req_primary = f"{prereq.primary_attribute} {prereq.primary_minimum}+"
            if prereq.secondary_attributes:
                secondary_list = ", ".join(prereq.secondary_attributes)
                req_text = f"{req_primary}; one of [{secondary_list}] {prereq.secondary_minimum}+"
            else:
                req_text = req_primary
        else:
            req_text = "No prerequisites"

        status_icon = "✓" if meets else "✗"
        status_text = "Available" if meets else "Locked"
        print(f"    {status_icon} {path.name}: {req_text} ({status_text})")

    input("\n  Press Enter to continue...")


def roll_4d6_drop_lowest() -> int:
    """Roll 4d6 and drop the lowest die."""
    rolls = [random.randint(1, 6) for _ in range(4)]
    rolls.sort(reverse=True)
    return sum(rolls[:3])


def step_ability_scores(builder: CharacterBuilder) -> bool:
    """Handle ability score assignment."""
    print_header("STEP 1: ABILITY SCORES")
    
    print("\n  Choose a method:")
    print("  1. Point Draw (27 points to distribute)")
    print("  2. Standard Array (15, 14, 13, 12, 10, 8)")
    print("  3. Roll (4d6 drop lowest, assign as you wish)")
    print("  4. Quick Test (all 12s)")
    
    method = input("\n  Method > ").strip()
    attributes = ["Might", "Agility", "Endurance", "Intellect", "Wisdom", "Charisma"]
    
    if method == "1":
        # Point Draw system
        print("\n  POINT DRAW")
        print("  You have 27 points to spend. All abilities start at 8.")
        print("  Cost: 8=0, 9=1, 10=2, 11=3, 12=4, 13=5, 14=7, 15=9")
        print()
        
        # Point costs for each score
        point_costs = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
        scores = {attr: 8 for attr in attributes}
        points_remaining = 27
        
        while True:
            # Show current allocation
            print(f"\n  Points remaining: {points_remaining}")
            print("  Current scores:")
            for i, attr in enumerate(attributes, 1):
                cost = point_costs[scores[attr]]
                print(f"    {i}. {attr}: {scores[attr]} (cost: {cost})")
            print(f"    7. Done (confirm and continue)")
            print(f"    0. Start over")
            
            choice = input("\n  Select ability to adjust (1-6), 7 to finish, 0 to reset > ").strip()
            
            if choice == "0":
                scores = {attr: 8 for attr in attributes}
                points_remaining = 27
                continue
            
            if choice == "7":
                if points_remaining >= 0:
                    builder.set_ability_scores(scores)
                    show_path_availability(builder)
                    return True
                else:
                    print("  You've spent too many points!")
                    continue
            
            try:
                idx = int(choice) - 1
                if 0 <= idx < 6:
                    attr = attributes[idx]
                    current = scores[attr]
                    
                    print(f"\n  {attr} is currently {current}")
                    print(f"  Enter new value (8-15), or press Enter to cancel: ")
                    new_val = input("  > ").strip()
                    
                    if new_val == "":
                        continue
                    
                    new_val = int(new_val)
                    if 8 <= new_val <= 15:
                        old_cost = point_costs[current]
                        new_cost = point_costs[new_val]
                        cost_diff = new_cost - old_cost
                        
                        if points_remaining - cost_diff >= 0:
                            scores[attr] = new_val
                            points_remaining -= cost_diff
                        else:
                            print(f"  Not enough points! Need {cost_diff}, have {points_remaining}")
                    else:
                        print("  Value must be 8-15")
            except ValueError:
                print("  Invalid input")
    
    elif method == "2":
        # Standard array assignment
        array = [15, 14, 13, 12, 10, 8]
        scores = {}
        
        print("\n  STANDARD ARRAY: 15, 14, 13, 12, 10, 8")
        print("  Assign each score to an ability:")
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
        show_path_availability(builder)
        return True
    
    elif method == "3":
        # Roll 4d6 drop lowest
        print("\n  ROLLING 4d6 DROP LOWEST...")
        print()
        
        rolls = []
        for i in range(6):
            dice = [random.randint(1, 6) for _ in range(4)]
            dice_sorted = sorted(dice, reverse=True)
            total = sum(dice_sorted[:3])
            rolls.append(total)
            print(f"  Roll {i+1}: {dice} -> drop {min(dice)} = {total}")
        
        rolls.sort(reverse=True)
        print(f"\n  Your rolls (sorted): {rolls}")
        print("  Assign each roll to an ability:")
        
        scores = {}
        remaining = rolls.copy()
        
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
        show_path_availability(builder)
        return True
    
    elif method == "4":
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
        show_path_availability(builder)
        return True
    
    return False


def is_feature_obvious(feature_name: str) -> bool:
    """Check if a feature name is self-explanatory."""
    obvious_features = {
        "darkvision", "fey ancestry", "lucky", "horn attack", 
        "primal senses", "prehensile tail", "immovable"
    }
    return feature_name.lower() in obvious_features


def step_race(builder: CharacterBuilder) -> bool:
    """Handle race selection."""
    print_header("STEP 2: CHOOSE RACE")
    
    races = builder.get_available_races()
    
    print("\n  Available Races:")
    for i, race in enumerate(races, 1):
        mods = ", ".join(f"{k} {v:+d}" for k, v in race.ability_modifiers.items()) or "flexible"
        print(f"\n  {i}. {race.name}")
        print(f"     Size: {race.size}, Speed: {race.speed} ft")
        if race.darkvision:
            print(f"     Darkvision: {race.darkvision} ft")
        print(f"     Abilities: {mods}")
        print(f"     Languages: {', '.join(race.languages)}")
        
        # Show features with descriptions for non-obvious ones
        if race.features:
            print("     Features:")
            for f in race.features:
                if is_feature_obvious(f.name):
                    print(f"       - {f.name}")
                else:
                    desc = wrap_text(f.description, width=50, indent="           ")
                    print(f"       - {f.name}: {desc}")
    
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
        print(f"\n  {i}. {anc.name}")
        print(f"     Region: {anc.region}")
        print(f"     Abilities: {mods}")
        if anc.languages:
            print(f"     Languages: {', '.join(anc.languages)}")
        if anc.reputation_modifier:
            print(f"     Reputation: +{anc.reputation_modifier.value} in {anc.reputation_modifier.region}")
        
        # Show features with descriptions for non-obvious ones
        if anc.features:
            print("     Features:")
            for f in anc.features:
                if is_feature_obvious(f.name):
                    print(f"       - {f.name}")
                else:
                    desc = wrap_text(f.description, width=50, indent="           ")
                    print(f"       - {f.name}: {desc}")
        
        # Show personality
        if anc.personality:
            print(f"     Personality: {anc.personality}")
    
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
        desc = wrap_text(prof.description, width=50, indent="     ")
        print(f"     {desc}")
        print(f"     Base HP: {prof.base_hp}")
        if prof.feature:
            if is_feature_obvious(prof.feature.name):
                print(f"     Feature: {prof.feature.name}")
            else:
                feat_desc = wrap_text(prof.feature.description, width=45, indent="              ")
                print(f"     Feature: {prof.feature.name}")
                print(f"              {feat_desc}")
        print(f"     Armor: {', '.join(prof.armor_proficiencies) or 'None'}")
        print(f"     Weapons: {', '.join(prof.weapon_proficiencies) or 'None'}")
        if prof.skill_choices:
            print(f"     Skills: Choose {prof.skill_choices['count']} from {', '.join(prof.skill_choices['options'])}")
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
            desc = wrap_text(duty.description, width=50, indent="     ")
            print(f"     {desc}")
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
        print(f"     Primary Bonus: {', '.join(f'{k} {v:+d}' for k, v in path.primary_bonus.items())}")
        print(f"     Attack Bonus: Melee +{path.attack_bonus_melee}, Ranged +{path.attack_bonus_ranged}")
        
        # Show features with descriptions
        if path.features:
            print("     Features:")
            for f in path.features:
                if is_feature_obvious(f.name):
                    print(f"       - {f.name}")
                else:
                    desc = wrap_text(f.description, width=45, indent="           ")
                    print(f"       - {f.name}: {desc}")
    
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
        # Wrap the description
        desc = wrap_text(bg.description, width=52, indent="     ")
        print(f"     {desc}")
        print(f"     Skills: {', '.join(bg.skill_proficiencies)}")
        if bg.languages_granted:
            print(f"     Languages: Choose {bg.languages_granted}")
        if bg.tool_proficiencies:
            print(f"     Tools: {', '.join(bg.tool_proficiencies)}")
        if bg.feature:
            if is_feature_obvious(bg.feature.name):
                print(f"     Feature: {bg.feature.name}")
            else:
                feat_desc = wrap_text(bg.feature.description, width=45, indent="              ")
                print(f"     Feature: {bg.feature.name}")
                print(f"              {feat_desc}")
    
    choice = get_choice("Select background", [b.id for b in backgrounds])
    
    if choice is None:
        return False
    
    builder.set_background(choice)
    print(f"\n  ✓ Selected {builder.chosen_background.name}")
    return True


def resolve_pending_choices(builder: CharacterBuilder):
    """Handle all pending choices with proper filtering."""
    while builder.pending_choices:
        print_header("PENDING CHOICES")
        
        choice = builder.pending_choices[0]
        
        print(f"\n  From: {choice.source}")
        print(f"  Type: {choice.choice_type}")
        print(f"  Choose {choice.count}:")
        
        # Determine what's already selected based on choice type
        disabled = set()
        if choice.choice_type == "skill":
            disabled = get_trained_skills(builder)
        elif choice.choice_type == "language":
            disabled = get_known_languages(builder)
        
        # Filter options to only show valid ones
        available_options = [o for o in choice.options if o not in disabled]
        
        if len(available_options) == 0:
            print(f"\n  All options already selected! Skipping...")
            builder.pending_choices.pop(0)
            input("\n  Press Enter to continue...")
            continue
        
        if len(available_options) < choice.count:
            print(f"\n  Only {len(available_options)} options available (need {choice.count})")
            actual_count = len(available_options)
        else:
            actual_count = choice.count
        
        if actual_count == 1:
            selection = get_choice("Select", choice.options, disabled=disabled, allow_back=False)
            if selection:
                builder.resolve_choice(choice.choice_type, [selection], source=choice.source)
                print(f"\n  ✓ Selected: {selection}")
        else:
            selections = get_multiple_choices("Select", choice.options, actual_count, disabled=disabled)
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
        def _safe_slug(text: str, fallback: str) -> str:
            cleaned = "".join(ch for ch in text if ch.isalnum() or ch in "-_ ").strip().replace(" ", "_")
            return cleaned or fallback

        default_name = _safe_slug(builder.character.character_name, "character")
        default_player = _safe_slug(builder.character.player, "player")
        default_filename = f"{default_name}_{default_player}.json"

        filename = input(f"  Filename (default: {default_filename}) > ").strip()
        if not filename:
            filename = default_filename
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
