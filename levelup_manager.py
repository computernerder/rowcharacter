"""
Level Up Manager - Core logic for character advancement.

This class handles all leveling calculations and can be used by any interface
(CLI, GUI, web, etc.)

Usage:
    from levelup_manager import LevelUpManager
    
    manager = LevelUpManager()
    manager.load_character("character.json")
    
    # Get what's available at next level
    options = manager.get_level_up_options()
    
    # Apply level up with choices
    manager.level_up(
        talent_choices=[("rage", 2), ("brutal_strike", 1)],
        ability_increase={"Might": 2},  # At levels 4, 8, 12, 16
        new_skills=["Athletics"]  # If applicable
    )
    
    # Save
    manager.save_character("character.json")
"""

import json
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from template_model import CharacterTemplate, load_character_template, dump_character_template
from core import Path as CharacterPath, load_all_paths
from validation import CharacterValidator, ValidationResult


# XP thresholds for each level (cumulative XP needed)
XP_TABLE = {
    1: 0,
    2: 300,
    3: 900,
    4: 3000,
    5: 7000,
    6: 13000,
    7: 22000,
    8: 34000,
    9: 49000,
    10: 67000,
    11: 88000,
    12: 112000,
    13: 139000,
    14: 169000,
    15: 202000,
    16: 238000,
    17: 277000,
    18: 317000,
    19: 358000,
    20: 400000,
}

# XP needed to go FROM level N to level N+1
XP_TO_NEXT = {
    1: 300,
    2: 600,
    3: 2100,
    4: 4000,
    5: 6000,
    6: 9000,
    7: 12000,
    8: 15000,
    9: 18000,
    10: 21000,
    11: 24000,
    12: 27000,
    13: 30000,
    14: 33000,
    15: 36000,
    16: 39000,
    17: 40000,
    18: 41000,
    19: 42000,
    20: 43000,  # And 43000 for each level above 20
}

# Levels that grant ability score increases
ABILITY_INCREASE_LEVELS = {4, 8, 12, 16}

# Levels that grant extra attack
EXTRA_ATTACK_LEVELS = {3, 9}


# Advancement Point costs
AP_COSTS = {
    "skill_rank": 1,        # +1 rank in trained skill
    "train_skill": 4,       # Train one new skill with +1 rank
    "inherit_gold": 5,      # Inherit 50 GP
    "ability_increase": 7,  # +2 in one or +1 in two core abilities
    "proficiency": 10,      # Learn one new proficiency (tool/armor/weapon)
    "language": 10,         # Learn one new language
}


@dataclass
class LevelUpOptions:
    """Options available when leveling up."""
    current_level: int
    new_level: int
    
    # Talent points to spend this level (Primary Path Core Ability mod + 5)
    talent_points: int
    
    # Minimum points that must be spent in primary path
    min_primary_path_points: int
    
    # Advancement points to spend (Intellect mod, minimum 2)
    advancement_points: int
    
    # Whether this level grants ability increase (+2 to one or +1 to two)
    grants_ability_increase: bool
    
    # Whether this level grants extra attack
    grants_extra_attack: bool
    
    # Available talents (from primary path, secondary paths, and general)
    available_talents: List[Dict[str, Any]] = field(default_factory=list)
    
    # Current talent ranks (to show what can be upgraded)
    current_talents: Dict[str, int] = field(default_factory=dict)
    
    # Trained skills (for skill rank upgrades)
    trained_skills: List[str] = field(default_factory=list)
    
    # Spellcrafting points gained (for Mystics)
    spellcrafting_points: int = 0
    
    # Casting points max increase (for Mystics)
    casting_points_increase: int = 0


@dataclass
class TalentChoice:
    """Represents a talent choice during level up."""
    talent_id: str
    talent_name: str
    new_rank: int
    points_spent: int
    path_id: str  # "general", "primary", or secondary path id


@dataclass
class AdvancementChoice:
    """Represents an advancement point purchase during level up."""
    choice_type: str  # "skill_rank", "train_skill", "proficiency", "language", "inherit_gold"
    target: str       # skill name, proficiency name, language name, etc.
    points_spent: int


class LevelUpManager:
    """
    Manages character level advancement.
    
    This class is designed to be interface-agnostic - it handles all the
    logic and calculations, while the actual UI is handled elsewhere.
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize the level up manager.
        
        Args:
            data_dir: Path to the data directory containing paths, talents, etc.
        """
        self.data_path = Path(data_dir)
        self.data_dir = str(self.data_path)
        self.character: Optional[CharacterTemplate] = None
        self.character_data: Optional[Dict[str, Any]] = None
        self.paths: Dict[str, CharacterPath] = {}
        self.general_talents: List[Dict[str, Any]] = []
        self.validator = CharacterValidator(data_dir=self.data_dir)
        self.last_validation: Optional[ValidationResult] = None
        
        self._load_game_data()
    
    def _load_game_data(self):
        """Load paths and talents from data files."""
        data_path = self.data_path
        try:
            self.paths = load_all_paths(str(data_path / "paths"))
        except Exception as e:
            print(f"Warning: Could not load paths: {e}")
            self.paths = {}
        
        # Load general talents if available
        talents_file = data_path / "talents" / "general.json"
        if talents_file.exists():
            with open(talents_file, "r", encoding="utf-8") as f:
                self.general_talents = json.load(f)
    
    def load_character(self, filepath: str) -> bool:
        """
        Load a character from a JSON file.
        
        Args:
            filepath: Path to the character JSON file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                self.character_data = json.load(f)
            self.character = load_character_template(self.character_data)
            return True
        except Exception as e:
            print(f"Error loading character: {e}")
            return False
    
    def load_character_from_dict(self, data: Dict[str, Any]) -> bool:
        """
        Load a character from a dictionary.
        
        Args:
            data: Character data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.character_data = data
            self.character = load_character_template(data)
            return True
        except Exception as e:
            print(f"Error loading character: {e}")
            return False
    
    def save_character(self, filepath: str) -> bool:
        """
        Save the character to a JSON file.
        
        Args:
            filepath: Path to save the character JSON file
            
        Returns:
            True if successful, False otherwise
        """
        if not self.character:
            return False
        
        try:
            output = dump_character_template(self.character)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving character: {e}")
            return False
    
    def get_character_dict(self) -> Optional[Dict[str, Any]]:
        """Get the character as a dictionary."""
        if not self.character:
            return None
        return dump_character_template(self.character)
    
    @property
    def current_level(self) -> int:
        """Get the character's current level."""
        if not self.character:
            return 0
        return self.character.level
    
    @property
    def current_xp(self) -> int:
        """Get the character's current XP."""
        if not self.character:
            return 0
        return self.character.total_experience
    
    def get_xp_for_level(self, level: int) -> int:
        """Get the cumulative XP required for a given level."""
        if level <= 0:
            return 0
        if level <= 20:
            return XP_TABLE.get(level, 0)
        # Beyond level 20: 400,000 + 43,000 per level above 20
        return 400000 + (level - 20) * 43000
    
    def get_xp_to_next_level(self, level: int) -> int:
        """Get the XP needed to advance from level to level+1."""
        if level < 1:
            return XP_TO_NEXT[1]
        if level <= 19:
            return XP_TO_NEXT.get(level, 43000)
        return 43000  # 43,000 for each level above 20
    
    def get_level_for_xp(self, xp: int) -> int:
        """Calculate what level a character should be at given XP."""
        level = 1
        for lvl in range(1, 21):
            if xp >= XP_TABLE[lvl]:
                level = lvl
            else:
                break
        
        # Check for levels beyond 20
        if xp >= 400000:
            extra_levels = (xp - 400000) // 43000
            level = 20 + extra_levels
        
        return level
    
    def get_primary_path(self) -> Optional[CharacterPath]:
        """Get the character's primary path."""
        if not self.character:
            return None
        
        path_name = self.character.primary_path
        if not path_name:
            return None
        
        # Find path by name
        for path_id, path in self.paths.items():
            if path.name == path_name:
                return path
        
        return None
    
    def calculate_talent_points(self, level: int = None) -> int:
        """
        Calculate talent points gained at a level.
        
        TP = Primary Path's Core Ability modifier + 5
        """
        if not self.character:
            return 0
        
        path = self.get_primary_path()
        if not path:
            return 5  # Default if no path
        
        # Get the talent points attribute from the path
        attr_name = path.talent_points_attribute
        if attr_name and attr_name in self.character.ability_scores:
            modifier = self.character.ability_scores[attr_name].mod
            return modifier + 5
        
        return 5
    
    def calculate_advancement_points(self) -> int:
        """
        Calculate advancement points gained at a level.
        
        AP = Intellect modifier (minimum 2)
        """
        if not self.character:
            return 2
        
        if "Intellect" in self.character.ability_scores:
            modifier = self.character.ability_scores["Intellect"].mod
            return max(2, modifier)
        
        return 2
    
    def get_trained_skills(self) -> List[str]:
        """Get list of trained skill names."""
        if not self.character:
            return []
        
        return [name for name, entry in self.character.skills.items() if entry.trained]
    
    def get_level_up_options(self, target_level: int = None) -> LevelUpOptions:
        """
        Get the options available when leveling up.
        
        Args:
            target_level: The level to advance to (default: current + 1)
            
        Returns:
            LevelUpOptions with all available choices
        """
        if not self.character:
            raise ValueError("No character loaded")
        
        current = self.current_level
        target = target_level or (current + 1)
        
        if target <= current:
            raise ValueError(f"Target level {target} must be higher than current level {current}")
        
        tp = self.calculate_talent_points()
        ap = self.calculate_advancement_points()
        
        # At least 4 points must go to primary path talents
        min_primary = min(4, tp)
        
        # Check for special level benefits
        grants_ability = target in ABILITY_INCREASE_LEVELS
        grants_extra_attack = target in EXTRA_ATTACK_LEVELS
        
        # Calculate spellcrafting points for Mystics
        sp_gain = 0
        cp_gain = 0
        path = self.get_primary_path()
        if path and path.spellcasting:
            int_mod = self.character.ability_scores.get("Intellect", {})
            if hasattr(int_mod, "mod"):
                int_mod = int_mod.mod
            else:
                int_mod = 0
            sp_gain = int_mod + target
            cp_gain = int_mod + target
        
        # Get current talents
        current_talents = {}
        for talent in self.character.talents:
            name = talent.get("name", "") if isinstance(talent, dict) else talent.name
            rank = talent.get("rank", 1) if isinstance(talent, dict) else getattr(talent, "rank", 1)
            current_talents[name] = rank
        
        # Get trained skills
        trained_skills = self.get_trained_skills()
        
        return LevelUpOptions(
            current_level=current,
            new_level=target,
            talent_points=tp,
            min_primary_path_points=min_primary,
            advancement_points=ap,
            grants_ability_increase=grants_ability,
            grants_extra_attack=grants_extra_attack,
            current_talents=current_talents,
            trained_skills=trained_skills,
            spellcrafting_points=sp_gain,
            casting_points_increase=cp_gain,
        )

    def _validate_level_up_inputs(
        self,
        options: LevelUpOptions,
        talent_choices: List[TalentChoice],
        advancement_choices: List[AdvancementChoice],
        ability_increase: Optional[Dict[str, int]],
    ) -> ValidationResult:
        """Validate choices for a pending level up."""
        ability_payload = ability_increase or {}
        talent_payload = []
        advancement_payload = []

        current_talents = options.current_talents or {}
        for choice in talent_choices:
            current_rank = current_talents.get(choice.talent_name, 0)
            talent_payload.append({
                "talent_id": choice.talent_id,
                "new_rank": choice.new_rank,
                "current_rank": current_rank,
                "points_spent": choice.points_spent,
                "path_id": choice.path_id,
            })

        for choice in advancement_choices:
            advancement_payload.append({
                "choice_type": choice.choice_type,
                "target": choice.target,
                "points_spent": choice.points_spent,
            })

        result = self.validator.validate_level_up(
            current_level=options.current_level,
            target_level=options.new_level,
            talent_choices=talent_payload,
            advancement_choices=advancement_payload,
            ability_increase=None,
            available_tp=options.talent_points,
            available_ap=options.advancement_points,
        )

        # Ensure ability increases are handled even when empty
        result.merge(self.validator.validate_ability_increase(
            ability_payload, options.new_level
        ))

        trained_skills = set(self.get_trained_skills())
        known_languages = set(self.character.languages if self.character else [])
        known_proficiencies = set(self.character.proficiencies if self.character else [])

        for choice in advancement_choices:
            result.merge(self.validator.validate_advancement_choice(
                choice.choice_type,
                choice.target,
                choice.points_spent,
                trained_skills=trained_skills,
                known_languages=known_languages,
                known_proficiencies=known_proficiencies,
            ))

        return result
    
    def level_up(self, 
                 talent_choices: List[TalentChoice] = None,
                 advancement_choices: List[AdvancementChoice] = None,
                 ability_increase: Dict[str, int] = None,
                 hp_roll: int = None) -> bool:
        """
        Apply a level up to the character.
        
        Args:
            talent_choices: List of TalentChoice objects for talents to add/upgrade
            advancement_choices: List of AdvancementChoice for AP purchases
            ability_increase: Dict of ability name to bonus (for levels 4, 8, 12, 16)
            hp_roll: The HP roll result (or None to use average)
            
        Returns:
            True if successful
        """
        if not self.character:
            return False
        
        options = self.get_level_up_options()

        talent_choices = talent_choices or []
        advancement_choices = advancement_choices or []
        self.last_validation = self._validate_level_up_inputs(
            options,
            talent_choices,
            advancement_choices,
            ability_increase,
        )
        if not self.last_validation.valid:
            return False
        
        # Increment level
        self.character.level = options.new_level
        
        # Apply ability increase if this level grants it
        if options.grants_ability_increase and ability_increase:
            for ability, bonus in ability_increase.items():
                if ability in self.character.ability_scores:
                    score = self.character.ability_scores[ability]
                    score.misc += bonus
                    score.total = score.roll + score.race + score.misc
                    score.mod = (score.total - 10) // 2
                    score.saving_throw = score.mod
        
        # Apply talent choices
        if talent_choices:
            for choice in talent_choices:
                self._apply_talent_choice(choice)
        
        # Apply advancement choices
        if advancement_choices:
            for choice in advancement_choices:
                self._apply_advancement_choice(choice)
        
        # Apply HP increase
        self._apply_hp_increase(hp_roll)
        
        # Apply spellcrafting points for Mystics
        if options.spellcrafting_points > 0:
            if hasattr(self.character.spellcrafting, "crafting_points"):
                if hasattr(self.character.spellcrafting.crafting_points, "max"):
                    # This would need to be cumulative, but for now just set it
                    pass
        
        # Apply extra attack if granted
        if options.grants_extra_attack:
            # Add extra attack feature
            extra_attack_feature = {
                "name": f"Extra Attack ({options.new_level})",
                "text": f"You can attack twice when you take the Attack action (gained at level {options.new_level})."
            }
            self.character.features.append(extra_attack_feature)
        
        # Recalculate derived stats
        self._recalculate_stats()
        
        return True
    
    def level_up_multiple(self, 
                          levels: int,
                          choices_per_level: List[Dict[str, Any]] = None) -> bool:
        """
        Level up multiple times.
        
        Args:
            levels: Number of levels to gain
            choices_per_level: List of choice dictionaries for each level
            
        Returns:
            True if successful
        """
        if not self.character:
            return False
        
        for i in range(levels):
            choices = choices_per_level[i] if choices_per_level and i < len(choices_per_level) else {}
            
            success = self.level_up(
                talent_choices=choices.get("talents"),
                advancement_choices=choices.get("advancements"),
                ability_increase=choices.get("abilities"),
                hp_roll=choices.get("hp_roll"),
            )
            
            if not success:
                return False
        
        return True
    
    def _apply_talent_choice(self, choice: TalentChoice):
        """Apply a single talent choice."""
        # Find existing talent
        existing = None
        for i, talent in enumerate(self.character.talents):
            name = talent.get("name", "") if isinstance(talent, dict) else talent.name
            if name == choice.talent_name:
                existing = (i, talent)
                break
        
        if existing:
            # Upgrade existing talent
            idx, talent = existing
            if isinstance(talent, dict):
                talent["rank"] = choice.new_rank
            else:
                talent.rank = choice.new_rank
        else:
            # Add new talent
            new_talent = {
                "name": choice.talent_name,
                "rank": choice.new_rank,
                "path": choice.path_id,
                "text": f"{choice.talent_name} (Rank {choice.new_rank})"
            }
            self.character.talents.append(new_talent)
    
    def _apply_advancement_choice(self, choice: AdvancementChoice):
        """Apply a single advancement point purchase."""
        if choice.choice_type == "skill_rank":
            # Increase rank of a trained skill by 1
            if choice.target in self.character.skills:
                skill = self.character.skills[choice.target]
                if skill.trained:
                    skill.rank += 1
                    skill.total = skill.mod + skill.rank + skill.misc
        
        elif choice.choice_type == "train_skill":
            # Train a new skill with +1 rank
            if choice.target in self.character.skills:
                skill = self.character.skills[choice.target]
                skill.trained = True
                skill.rank = 1
                skill.total = skill.mod + skill.rank + skill.misc
        
        elif choice.choice_type == "proficiency":
            # Learn a new tool, armor, or weapon proficiency
            if choice.target not in self.character.proficiencies:
                self.character.proficiencies.append(choice.target)
        
        elif choice.choice_type == "language":
            # Learn a new language
            if choice.target not in self.character.languages:
                self.character.languages.append(choice.target)
        
        elif choice.choice_type == "inherit_gold":
            # Gain 50 gold (tracked in notes or wealth)
            # This would typically be tracked elsewhere
            pass
        
        elif choice.choice_type == "ability_increase":
            # +2 to one or +1 to two abilities (costs 7 AP)
            # This is handled separately via ability_increase parameter
            pass
    
    def _apply_hp_increase(self, hp_roll: int = None):
        """Apply HP increase for level up."""
        # Get profession base HP die (simplified - would need profession data)
        # For now, use a default or the roll provided
        if hp_roll is None:
            # Use average (assuming d8 for most professions)
            hp_roll = 5
        
        # Add END modifier
        end_mod = 0
        if "Endurance" in self.character.ability_scores:
            end_mod = self.character.ability_scores["Endurance"].mod
        
        hp_gain = max(1, hp_roll + end_mod)
        self.character.health.max += hp_gain
        self.character.health.current = self.character.health.max
    
    def _recalculate_stats(self):
        """Recalculate all derived statistics."""
        char = self.character
        
        # Recalculate ability modifiers
        for name, score in char.ability_scores.items():
            score.total = score.roll + score.race + score.misc
            score.mod = (score.total - 10) // 2
            score.saving_throw = score.mod
        
        # Recalculate skill totals
        for skill_name, entry in char.skills.items():
            # Would need skill->attribute mapping here
            entry.total = entry.mod + entry.rank + entry.misc
        
        # Recalculate attack modifiers
        if "Might" in char.ability_scores:
            char.attack_mods_melee.attr = char.ability_scores["Might"].mod
        if "Agility" in char.ability_scores:
            char.attack_mods_ranged.attr = char.ability_scores["Agility"].mod
        
        char.attack_mods_melee.total = char.attack_mods_melee.attr + char.attack_mods_melee.misc
        char.attack_mods_ranged.total = char.attack_mods_ranged.attr + char.attack_mods_ranged.misc
        
        # Recalculate defense
        if "Agility" in char.ability_scores:
            char.defense.agility = char.ability_scores["Agility"].mod
        shield = char.defense.shield if isinstance(char.defense.shield, int) else 0
        char.defense.total = char.defense.base + char.defense.agility + shield + char.defense.misc
        
        # Recalculate initiative
        if "Agility" in char.ability_scores:
            char.initiative = char.ability_scores["Agility"].mod
        
        # Recalculate life points
        if "Endurance" in char.ability_scores:
            char.life_points.max = max(1, char.ability_scores["Endurance"].total)
            char.life_points.current = char.life_points.max
    
    def get_level_summary(self) -> Dict[str, Any]:
        """Get a summary of the character's current level state."""
        if not self.character:
            return {}
        
        current = self.current_level
        xp = self.current_xp
        xp_for_current = self.get_xp_for_level(current)
        xp_for_next = self.get_xp_for_level(current + 1)
        xp_needed = xp_for_next - xp
        
        return {
            "level": current,
            "xp": xp,
            "xp_for_current_level": xp_for_current,
            "xp_for_next_level": xp_for_next,
            "xp_needed": max(0, xp_needed),
            "xp_progress": xp - xp_for_current,
            "xp_required": xp_for_next - xp_for_current,
            "talent_points_per_level": self.calculate_talent_points(),
            "primary_path": self.character.primary_path,
        }
    
    def validate_talent_choices(self, 
                                choices: List[TalentChoice], 
                                options: LevelUpOptions) -> Tuple[bool, List[str]]:
        """
        Validate talent choices against available points and requirements.
        
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        total_points = 0
        primary_points = 0
        
        for choice in choices:
            total_points += choice.points_spent
            if choice.path_id == "primary":
                primary_points += choice.points_spent
        
        if total_points > options.talent_points:
            errors.append(f"Spent {total_points} TP but only have {options.talent_points}")
        
        if primary_points < options.min_primary_path_points:
            errors.append(f"Must spend at least {options.min_primary_path_points} TP in primary path")
        
        return (len(errors) == 0, errors)
    
    def validate_ability_increase(self, 
                                  increase: Dict[str, int], 
                                  options: LevelUpOptions) -> Tuple[bool, List[str]]:
        """
        Validate ability score increase choices.
        
        Valid options: +2 to one ability OR +1 to two abilities
        
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        if not options.grants_ability_increase:
            if increase:
                errors.append(f"Level {options.new_level} does not grant ability increase")
            return (len(errors) == 0, errors)
        
        if not increase:
            errors.append("Must choose ability increase at this level")
            return (False, errors)
        
        total_bonus = sum(increase.values())
        num_abilities = len(increase)
        
        if total_bonus != 2:
            errors.append("Ability increase must total +2")
        
        if num_abilities == 1:
            if list(increase.values())[0] != 2:
                errors.append("Single ability increase must be +2")
        elif num_abilities == 2:
            if not all(v == 1 for v in increase.values()):
                errors.append("Two ability increases must each be +1")
        else:
            errors.append("Can only increase 1 ability by +2 or 2 abilities by +1 each")
        
        return (len(errors) == 0, errors)
