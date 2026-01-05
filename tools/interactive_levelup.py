"""
Interactive Level Up CLI

Run from the FightingSystem directory:
    python interactive_levelup.py character.json
    
Or without arguments to be prompted for the file.
"""

import json
import sys
import os
import random
from pathlib import Path
from typing import List, Optional, Dict, Any

# Make project root importable when running from tools/
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from levelup_manager import (
    LevelUpManager, 
    LevelUpOptions, 
    TalentChoice,
    AdvancementChoice,
    ABILITY_INCREASE_LEVELS,
    EXTRA_ATTACK_LEVELS,
    AP_COSTS,
)


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


def show_character_summary(manager: LevelUpManager):
    """Display current character state."""
    char = manager.character
    summary = manager.get_level_summary()
    
    print_subheader("Character Summary")
    print(f"  Name: {char.character_name or '(unnamed)'}")
    print(f"  Race: {char.race} / {char.ancestry}")
    print(f"  Profession: {char.profession}")
    print(f"  Path: {char.primary_path}")
    print(f"  Level: {summary['level']}")
    print(f"  XP: {summary['xp']:,} / {summary['xp_for_next_level']:,} (need {summary['xp_needed']:,} more)")
    print(f"  TP per level: {summary['talent_points_per_level']}")
    
    print("\n  Ability Scores:")
    for name, score in char.ability_scores.items():
        print(f"    {name:12} {score.total:2d} (mod {score.mod:+d})")
    
    print(f"\n  HP: {char.health.max}")
    print(f"  Defense: {char.defense.total}")
    
    if char.talents:
        print("\n  Talents:")
        for t in char.talents[:5]:
            name = t.get("name", "?") if isinstance(t, dict) else t.name
            rank = t.get("rank", 1) if isinstance(t, dict) else getattr(t, "rank", 1)
            print(f"    - {name} (Rank {rank})")
        if len(char.talents) > 5:
            print(f"    ... and {len(char.talents) - 5} more")


def show_level_up_options(manager: LevelUpManager, options: LevelUpOptions):
    """Display what's available at this level up."""
    print_subheader(f"Level Up: {options.current_level} → {options.new_level}")
    
    print(f"\n  Talent Points to spend: {options.talent_points}")
    print(f"  Minimum in primary path: {options.min_primary_path_points}")
    
    print(f"\n  Advancement Points to spend: {options.advancement_points}")
    print("    Costs: Skill rank +1 = 1 AP | Train new skill = 4 AP")
    print("           Proficiency = 10 AP | Language = 10 AP")
    
    if options.grants_ability_increase:
        print("\n  ★ This level grants an Ability Score Increase!")
        print("    Choose: +2 to one ability OR +1 to two abilities")
    
    if options.grants_extra_attack:
        print("\n  ★ This level grants Extra Attack!")
    
    if options.spellcrafting_points > 0:
        print(f"\n  ★ Spellcrafting Points gained: {options.spellcrafting_points}")
        print(f"  ★ Max Casting Points: {options.casting_points_increase}")
    
    if options.current_talents:
        print("\n  Current Talents:")
        for talent_id, rank in options.current_talents.items():
            tdef = getattr(manager, "talents_flat", {}).get(talent_id)
            label = f"{tdef.name} ({talent_id})" if tdef else talent_id
            print(f"    - {label}: Rank {rank}")
    
    if options.trained_skills:
        print(f"\n  Trained Skills: {', '.join(options.trained_skills)}")


def choose_ability_increase(manager: LevelUpManager) -> Dict[str, int]:
    """Let user choose ability score increase."""
    print_subheader("Ability Score Increase")
    print("\n  Choose one:")
    print("  1. +2 to one ability")
    print("  2. +1 to two abilities")
    
    choice = input("\n  > ").strip()
    
    abilities = list(manager.character.ability_scores.keys())
    
    if choice == "1":
        print("\n  Which ability gets +2?")
        for i, ability in enumerate(abilities, 1):
            score = manager.character.ability_scores[ability]
            print(f"    {i}. {ability}: {score.total} → {score.total + 2}")
        
        while True:
            try:
                idx = int(input("\n  > ").strip()) - 1
                if 0 <= idx < len(abilities):
                    return {abilities[idx]: 2}
                print("  Invalid choice")
            except ValueError:
                print("  Enter a number")
    
    elif choice == "2":
        print("\n  Which two abilities get +1 each?")
        for i, ability in enumerate(abilities, 1):
            score = manager.character.ability_scores[ability]
            print(f"    {i}. {ability}: {score.total} → {score.total + 1}")
        
        print("\n  Enter two numbers separated by comma (e.g., 1,4):")
        while True:
            try:
                parts = input("  > ").strip().split(",")
                if len(parts) != 2:
                    print("  Enter exactly two numbers")
                    continue
                
                idx1 = int(parts[0].strip()) - 1
                idx2 = int(parts[1].strip()) - 1
                
                if idx1 == idx2:
                    print("  Choose two different abilities")
                    continue
                
                if 0 <= idx1 < len(abilities) and 0 <= idx2 < len(abilities):
                    return {abilities[idx1]: 1, abilities[idx2]: 1}
                print("  Invalid choices")
            except ValueError:
                print("  Enter two numbers separated by comma")
    
    return {}


def choose_talents(manager: LevelUpManager, options: LevelUpOptions) -> List[TalentChoice]:
    """Let user choose talents to purchase/upgrade."""
    print_subheader("Talent Point Allocation")
    
    choices = []
    remaining_tp = options.talent_points
    primary_tp_spent = 0
    
    print(f"\n  You have {remaining_tp} TP to spend.")
    if options.min_primary_path_points:
        print(f"  At least {options.min_primary_path_points} must go to primary path talents.")
    print("\n  Choose talents from the available list.")
    print("  Type the number to buy the next rank, 'done' when finished, or 'skip' to skip.")
    
    while remaining_tp > 0:
        available = [t for t in (options.available_talents or []) if t.get("tp_cost", 0) <= remaining_tp]
        if not available:
            print("\n  No available talents you can afford with remaining TP.")
            break

        print(f"\n  Remaining TP: {remaining_tp}")
        for i, t in enumerate(available, 1):
            name = t.get("name", "?")
            talent_id = t.get("talent_id", "")
            cur = t.get("current_rank", 0)
            nxt = t.get("next_rank", cur + 1)
            cost = t.get("tp_cost", nxt)
            path_id = t.get("path_id", "general")
            suffix = ""
            if t.get("requires_choice"):
                suffix = " (requires choice)"
            print(f"    {i}. {name} [{talent_id}]  Rank {cur} → {nxt}  Cost {cost}  ({path_id}){suffix}")

        entry = input("  > ").strip().lower()
        if entry == "done":
            break
        if entry == "skip":
            return []

        try:
            idx = int(entry) - 1
        except ValueError:
            print("  Enter a number, 'done', or 'skip'.")
            continue

        if idx < 0 or idx >= len(available):
            print("  Invalid selection.")
            continue

        t = available[idx]
        talent_id = t.get("talent_id", "")
        name = t.get("name", talent_id)
        new_rank = int(t.get("next_rank", 1))
        cost = int(t.get("tp_cost", new_rank))
        path_id = t.get("path_id", "general")
        choice_data: Dict[str, Any] = {}

        if t.get("requires_choice"):
            opts = list(t.get("choice_options", []) or [])
            if not opts:
                print("  This talent requires a choice but has no options listed.")
                continue
            print("\n  Choose an option:")
            for j, opt in enumerate(opts, 1):
                print(f"    {j}. {opt}")
            while True:
                sel = input("  > ").strip()
                try:
                    j = int(sel) - 1
                except ValueError:
                    print("  Enter a number.")
                    continue
                if 0 <= j < len(opts):
                    choice_key = t.get("choice_type") or "choice"
                    choice_data = {choice_key: opts[j]}
                    break
                print("  Invalid choice.")

        choices.append(TalentChoice(
            talent_id=talent_id,
            talent_name=name,
            new_rank=new_rank,
            points_spent=cost,
            path_id=path_id,
            choice_data=choice_data,
        ))
        remaining_tp -= cost
        if path_id == "primary":
            primary_tp_spent += cost

        print(f"  ✓ Added {name} (Rank {new_rank}) for {cost} TP")
    
    # Validate minimum primary path spending
    if primary_tp_spent < options.min_primary_path_points and choices:
        print(f"\n  Warning: Only spent {primary_tp_spent} TP in primary path")
        print(f"  (minimum is {options.min_primary_path_points})")
    
    return choices


def choose_advancements(manager: LevelUpManager, options: LevelUpOptions) -> List[AdvancementChoice]:
    """Let user choose advancement point purchases."""
    print_subheader("Advancement Point Allocation")
    
    choices = []
    remaining_ap = options.advancement_points
    
    print(f"\n  You have {remaining_ap} AP to spend.")
    print()
    print("  Options:")
    print("    1. +1 rank to trained skill (1 AP)")
    print("    2. Train new skill (4 AP)")
    print("    3. New proficiency (10 AP)")
    print("    4. New language (10 AP)")
    print("    5. Done / Skip")
    
    while remaining_ap > 0:
        print(f"\n  Remaining AP: {remaining_ap}")
        choice = input("  Option > ").strip()
        
        if choice == "5" or choice.lower() in ["done", "skip"]:
            break
        
        if choice == "1":
            # +1 rank to trained skill
            if remaining_ap < AP_COSTS["skill_rank"]:
                print(f"  Not enough AP (need {AP_COSTS['skill_rank']})")
                continue
            
            print(f"\n  Trained skills: {', '.join(options.trained_skills)}")
            skill = input("  Skill name > ").strip()
            
            if skill and skill in options.trained_skills:
                choices.append(AdvancementChoice(
                    choice_type="skill_rank",
                    target=skill,
                    points_spent=AP_COSTS["skill_rank"]
                ))
                remaining_ap -= AP_COSTS["skill_rank"]
                print(f"  ✓ +1 rank to {skill}")
            else:
                print("  Invalid or untrained skill")
        
        elif choice == "2":
            # Train new skill
            if remaining_ap < AP_COSTS["train_skill"]:
                print(f"  Not enough AP (need {AP_COSTS['train_skill']})")
                continue
            
            skill = input("  New skill name > ").strip()
            
            if skill and skill not in options.trained_skills:
                choices.append(AdvancementChoice(
                    choice_type="train_skill",
                    target=skill,
                    points_spent=AP_COSTS["train_skill"]
                ))
                remaining_ap -= AP_COSTS["train_skill"]
                options.trained_skills.append(skill)  # Add to list for further ranks
                print(f"  ✓ Trained {skill}")
            else:
                print("  Invalid skill or already trained")
        
        elif choice == "3":
            # New proficiency
            if remaining_ap < AP_COSTS["proficiency"]:
                print(f"  Not enough AP (need {AP_COSTS['proficiency']})")
                continue
            
            prof = input("  Proficiency name > ").strip()
            
            if prof:
                choices.append(AdvancementChoice(
                    choice_type="proficiency",
                    target=prof,
                    points_spent=AP_COSTS["proficiency"]
                ))
                remaining_ap -= AP_COSTS["proficiency"]
                print(f"  ✓ Learned {prof}")
        
        elif choice == "4":
            # New language
            if remaining_ap < AP_COSTS["language"]:
                print(f"  Not enough AP (need {AP_COSTS['language']})")
                continue
            
            lang = input("  Language name > ").strip()
            
            if lang:
                choices.append(AdvancementChoice(
                    choice_type="language",
                    target=lang,
                    points_spent=AP_COSTS["language"]
                ))
                remaining_ap -= AP_COSTS["language"]
                print(f"  ✓ Learned {lang}")
    
    return choices


def roll_hp(manager: LevelUpManager) -> int:
    """Roll or choose HP for level up."""
    print_subheader("Hit Point Increase")
    
    # Get END modifier
    end_mod = 0
    if "Endurance" in manager.character.ability_scores:
        end_mod = manager.character.ability_scores["Endurance"].mod
    
    print("\n  Choose HP method:")
    print("  1. Roll (d8 + END modifier)")
    print("  2. Take average (5 + END modifier)")
    print(f"\n  Your END modifier: {end_mod:+d}")
    
    choice = input("\n  > ").strip()
    
    if choice == "1":
        roll = random.randint(1, 8)
        total = max(1, roll + end_mod)
        print(f"\n  Rolled: {roll} + {end_mod} = {total} HP")
        return roll
    else:
        print(f"\n  Taking average: 5 + {end_mod} = {max(1, 5 + end_mod)} HP")
        return 5


def do_level_up(manager: LevelUpManager, target_level: int = None):
    """Perform a single level up."""
    options = manager.get_level_up_options(target_level)
    
    show_level_up_options(manager, options)
    
    # Handle ability increase if applicable
    ability_increase = None
    if options.grants_ability_increase:
        ability_increase = choose_ability_increase(manager)
    
    # Handle talent choices
    talent_choices = choose_talents(manager, options)
    
    # Handle advancement choices
    advancement_choices = choose_advancements(manager, options)
    
    # Handle HP
    hp_roll = roll_hp(manager)
    
    # Apply the level up
    print_subheader("Applying Level Up")
    
    success = manager.level_up(
        talent_choices=talent_choices,
        advancement_choices=advancement_choices,
        ability_increase=ability_increase,
        hp_roll=hp_roll,
    )
    validation = getattr(manager, "last_validation", None)

    if success:
        print(f"\n  ✓ Advanced to Level {options.new_level}!")
        if ability_increase:
            for ability, bonus in ability_increase.items():
                print(f"    {ability} +{bonus}")
        if talent_choices:
            for tc in talent_choices:
                print(f"    Talent: {tc.talent_name} (Rank {tc.new_rank})")
        if advancement_choices:
            for ac in advancement_choices:
                print(f"    {ac.choice_type}: {ac.target}")
        print(f"    HP: {manager.character.health.max}")
        if validation and validation.warnings:
            print("\n  ⚠ Warnings:")
            for warn in validation.warnings:
                print(f"    - {warn}")
    else:
        print("\n  ✗ Level up failed!")
        if validation:
            if validation.errors:
                print("\n  Errors:")
                for err in validation.errors:
                    print(f"    - {err}")
            if validation.warnings:
                print("\n  Warnings:")
                for warn in validation.warnings:
                    print(f"    - {warn}")
    
    return success


def main():
    """Main interactive level up loop."""
    clear_screen()
    print_header("REALM OF WARRIORS - LEVEL UP")
    
    # Get character file
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        # Look for JSON character files in cwd, script dir, and ./characters
        script_dir = os.path.dirname(os.path.abspath(__file__))
        search_dirs = [
            os.getcwd(),
            script_dir,
            os.path.join(os.getcwd(), "characters"),
            os.path.join(script_dir, "characters"),
        ]
        seen = set()
        json_files = []
        for d in search_dirs:
            try:
                for f in os.listdir(d):
                    if f.lower().endswith('.json'):
                        full = os.path.join(d, f)
                        if full not in seen:
                            seen.add(full)
                            json_files.append(full)
            except OSError:
                continue

        json_files = sorted(json_files)
        filepath = ""

        if json_files:
            print("\n  Available character files:")
            for i, full in enumerate(json_files, 1):
                name = os.path.relpath(full, os.getcwd())
                print(f"    {i}. {name}")
            choice = input("\n  Enter number to select, or type a path > ").strip()
            if choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(json_files):
                    filepath = json_files[idx - 1]
            if not filepath:
                filepath = choice
        else:
            filepath = input("\n  Character file path: ").strip()
    
    if not os.path.exists(filepath):
        print(f"\n  Error: File not found: {filepath}")
        return
    
    # Create manager and load character
    manager = LevelUpManager(data_dir=str(ROOT_DIR / "data"))
    
    print(f"\n  Loading {filepath}...")
    if not manager.load_character(filepath):
        print("  Failed to load character!")
        return
    
    print("  ✓ Character loaded")
    
    # Main loop
    while True:
        clear_screen()
        show_character_summary(manager)
        
        print_subheader("Options")
        print("  1. Level up once")
        print("  2. Level up multiple times")
        print("  3. Level up to specific level")
        print("  4. Save character")
        print("  5. Save and exit")
        print("  0. Exit without saving")

        choice = input("\n  > ").strip()
        
        if choice == "0":
            print("\n  Exiting without saving...")
            break
        
        elif choice == "1":
            do_level_up(manager)
            input("\n  Press Enter to continue...")
        
        elif choice == "2":
            try:
                levels = int(input("\n  How many levels? > ").strip())
                for i in range(levels):
                    print(f"\n  === Level Up {i+1} of {levels} ===")
                    if not do_level_up(manager):
                        break
                input("\n  Press Enter to continue...")
            except ValueError:
                print("  Invalid number")
        
        elif choice == "3":
            try:
                target = int(input("\n  Target level? > ").strip())
                current = manager.current_level
                if target <= current:
                    print(f"  Must be higher than current level ({current})")
                else:
                    levels_to_gain = target - current
                    print(f"\n  Gaining {levels_to_gain} levels...")
                    for i in range(levels_to_gain):
                        print(f"\n  === Level {current + i + 1} ===")
                        if not do_level_up(manager):
                            break
                input("\n  Press Enter to continue...")
            except ValueError:
                print("  Invalid number")
        
        elif choice == "4":
            save_path = input(f"\n  Save path [{filepath}]: ").strip()
            if not save_path:
                save_path = filepath
            if manager.save_character(save_path):
                print(f"  ✓ Saved to {save_path}")
            else:
                print("  ✗ Save failed!")
            input("\n  Press Enter to continue...")
        
        elif choice == "5":
            save_path = input(f"\n  Save path [{filepath}]: ").strip()
            if not save_path:
                save_path = filepath
            if manager.save_character(save_path):
                print(f"  ✓ Saved to {save_path}")
            else:
                print("  ✗ Save failed!")
            break
    
    print("\n  Goodbye!")


if __name__ == "__main__":
    main()
