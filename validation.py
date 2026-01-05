"""
Validation Classes for Realm of Warriors Character System

Provides validation for all character creation and level-up inputs.
Each validator returns a ValidationResult with success status and error messages.

Usage:
    from validation import CharacterValidator, ValidationResult
    
    validator = CharacterValidator(data_dir="data")
    
    # Validate ability scores
    result = validator.validate_ability_scores(scores, method="point_buy")
    if not result.valid:
        print(result.errors)
    
    # Validate a complete character
    result = validator.validate_character(character_dict)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Tuple
from enum import Enum
import json
from pathlib import Path


@dataclass
class ValidationResult:
    """Result of a validation check."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, message: str):
        """Add an error and mark as invalid."""
        self.errors.append(message)
        self.valid = False
    
    def add_warning(self, message: str):
        """Add a warning (doesn't affect validity)."""
        self.warnings.append(message)
    
    def merge(self, other: "ValidationResult"):
        """Merge another result into this one."""
        if not other.valid:
            self.valid = False
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
    
    def __bool__(self) -> bool:
        return self.valid


class AbilityScoreMethod(Enum):
    """Methods for generating ability scores."""
    POINT_BUY = "point_buy"  # preferred naming (rulebook)
    POINT_DRAW = "point_draw"  # backward-compat alias
    STANDARD_ARRAY = "standard_array"
    ROLL = "roll"
    QUICK_TEST = "quick_test"
    MANUAL = "manual"


# Constants for validation
ABILITY_NAMES = {"Might", "Agility", "Endurance", "Intellect", "Wisdom", "Charisma"}

# Rulebook standard array (7 numbers, choose any 6)
STANDARD_ARRAY = [15, 14, 13, 12, 11, 10, 8]

# Point buy/draw (rulebook): 30 points, allow up to 16 with cost 11
POINT_BUY_COSTS = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9, 16: 11}
POINT_BUY_TOTAL = 30

SKILLS = {
    # Might-based
    "Athletics",
    # Agility-based
    "Acrobatics", "Sleight of Hand", "Stealth",
    # Endurance-based (none standard)
    # Intellect-based
    "Arcana", "History", "Investigation", "Nature", "Religion",
    # Wisdom-based
    "Animal Handling", "Insight", "Medicine", "Perception", "Survival", "Taming",
    # Charisma-based
    "Deception", "Intimidation", "Performance", "Persuasion",
}

LANGUAGES = {
    # Common
    "Common", "Elvish", "Dwarvish", "Orcish", "Goblin", "Halffolk",
    # Exotic
    "Draconic", "Celestial", "Infernal", "Sylvan", "Aquan",
    # Racial
    "Tauric", "Simarru", "Velkarran",
    # Ancient
    "Ancient Dwarvish",
}

ARMOR_PROFICIENCIES = {"None", "Light", "Medium", "Heavy"}

WEAPON_PROFICIENCIES = {
    "Simple", "Martial", "Light", "Finesse", "Ranged", "Two-Handed", "Melee"
}

SIZES = {"Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan"}

PATH_ROLES = {"Defender", "Striker", "Support", "Specialist"}


class CharacterValidator:
    """
    Validates character data for creation and level-up.
    
    Loads reference data from JSON files to validate against.
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize validator with data directory.
        
        Args:
            data_dir: Path to directory containing game data JSON files
        """
        self.data_dir = Path(data_dir)
        
        # Load valid IDs from data files
        self.valid_race_ids: Set[str] = set()
        self.valid_ancestry_ids: Set[str] = set()
        self.valid_profession_ids: Set[str] = set()
        self.valid_path_ids: Set[str] = set()
        self.valid_background_ids: Set[str] = set()
        self.valid_talent_ids: Set[str] = set()
        
        # Talent max ranks
        self.talent_max_ranks: Dict[str, int] = {}
        
        # Path prerequisites
        self.path_prerequisites: Dict[str, Dict] = {}
        
        self._load_valid_ids()
    
    def _load_valid_ids(self):
        """Load valid IDs from data files."""
        # Races
        races_dir = self.data_dir / "races"
        if races_dir.exists():
            for f in races_dir.glob("*.json"):
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        self.valid_race_ids.add(data.get("id", f.stem))
                except:
                    pass
        
        # Ancestries
        ancestries_dir = self.data_dir / "ancestries"
        if ancestries_dir.exists():
            for f in ancestries_dir.glob("*.json"):
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        self.valid_ancestry_ids.add(data.get("id", f.stem))
                except:
                    pass
        
        # Professions
        professions_dir = self.data_dir / "professions"
        if professions_dir.exists():
            for f in professions_dir.glob("*.json"):
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        self.valid_profession_ids.add(data.get("id", f.stem))
                except:
                    pass
        
        # Paths
        paths_dir = self.data_dir / "paths"
        if paths_dir.exists():
            for f in paths_dir.glob("*.json"):
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        path_id = data.get("id", f.stem)
                        self.valid_path_ids.add(path_id)
                        if "prerequisites" in data:
                            self.path_prerequisites[path_id] = data["prerequisites"]
                except:
                    pass
        
        # Backgrounds
        backgrounds_dir = self.data_dir / "backgrounds"
        if backgrounds_dir.exists():
            for f in backgrounds_dir.glob("*.json"):
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        self.valid_background_ids.add(data.get("id", f.stem))
                except:
                    pass
        
        # Talents
        talents_dir = self.data_dir / "talents"
        if talents_dir.exists():
            for f in talents_dir.glob("*.json"):
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        for talent in data.get("talents", []):
                            talent_id = talent.get("id", "")
                            self.valid_talent_ids.add(talent_id)
                            self.talent_max_ranks[talent_id] = talent.get("max_rank", 3)
                except:
                    pass
    
    # =========================================================================
    # ABILITY SCORE VALIDATION
    # =========================================================================
    
    def validate_ability_scores(
        self, 
        scores: Dict[str, int], 
        method: str = "manual"
    ) -> ValidationResult:
        """
        Validate ability scores.
        
        Args:
            scores: Dict mapping ability name to score value
            method: Generation method (point_buy/point_draw, standard_array, roll, manual)
        
        Returns:
            ValidationResult
        """
        result = ValidationResult(valid=True)
        
        # Check all abilities are present
        missing = ABILITY_NAMES - set(scores.keys())
        if missing:
            result.add_error(f"Missing ability scores: {', '.join(missing)}")
        
        extra = set(scores.keys()) - ABILITY_NAMES
        if extra:
            result.add_error(f"Unknown ability scores: {', '.join(extra)}")
        
        # Check value ranges
        for name, value in scores.items():
            if not isinstance(value, int):
                result.add_error(f"{name} must be an integer, got {type(value).__name__}")
                continue
            
            if value < 1:
                result.add_error(f"{name} cannot be less than 1 (got {value})")
            elif value > 20:
                result.add_error(f"{name} cannot exceed 20 (got {value})")
            elif value < 3:
                result.add_warning(f"{name} is unusually low ({value})")
        
        # Method-specific validation
        if method in ("point_buy", "point_draw"):
            result.merge(self._validate_point_draw(scores))
        elif method == "standard_array":
            result.merge(self._validate_standard_array(scores))
        elif method == "quick_test":
            if not all(v == 12 for v in scores.values()):
                result.add_warning("Quick test should have all 12s")
        
        return result
    
    def _validate_point_draw(self, scores: Dict[str, int]) -> ValidationResult:
        """Validate point buy/draw method (rulebook)."""
        result = ValidationResult(valid=True)
        
        total_cost = 0
        for name, value in scores.items():
            if value < 8:
                result.add_error(f"Point buy: {name} cannot be below 8 (got {value})")
            elif value > 16:
                result.add_error(f"Point buy: {name} cannot exceed 16 (got {value})")
            elif value in POINT_BUY_COSTS:
                total_cost += POINT_BUY_COSTS[value]
        
        if total_cost > POINT_BUY_TOTAL:
            result.add_error(f"Point buy: spent {total_cost} points (max {POINT_BUY_TOTAL})")
        elif total_cost < POINT_BUY_TOTAL:
            result.add_warning(f"Point buy: only spent {total_cost} of {POINT_BUY_TOTAL} points")
        
        return result
    
    def _validate_standard_array(self, scores: Dict[str, int]) -> ValidationResult:
        """Validate standard array method."""
        result = ValidationResult(valid=True)
        
        values = sorted(scores.values(), reverse=True)
        # Rulebook lists 7 numbers; allow any 6 without reuse.
        allowed = sorted(STANDARD_ARRAY, reverse=True)
        if len(values) != 6:
            result.add_error(f"Standard array must assign exactly 6 scores, got {len(values)}")
            return result
        remaining = allowed.copy()
        for v in values:
            if v in remaining:
                remaining.remove(v)
            else:
                result.add_error(
                    f"Standard array values must be chosen from {STANDARD_ARRAY} without reuse; got {list(scores.values())}"
                )
                break
        
        return result
    
    # =========================================================================
    # RACE/ANCESTRY VALIDATION
    # =========================================================================
    
    def validate_race(self, race_id: str) -> ValidationResult:
        """Validate race selection."""
        result = ValidationResult(valid=True)
        
        if not race_id:
            result.add_error("Race is required")
        elif race_id not in self.valid_race_ids:
            result.add_error(f"Unknown race: {race_id}")
            if self.valid_race_ids:
                result.add_warning(f"Valid races: {', '.join(sorted(self.valid_race_ids))}")
        
        return result
    
    def validate_ancestry(
        self, 
        ancestry_id: str, 
        race_id: str = None
    ) -> ValidationResult:
        """Validate ancestry selection."""
        result = ValidationResult(valid=True)
        
        if not ancestry_id:
            result.add_error("Ancestry is required")
        elif ancestry_id not in self.valid_ancestry_ids:
            result.add_error(f"Unknown ancestry: {ancestry_id}")
        
        # Check ancestry matches race (if we have that data)
        if race_id and ancestry_id:
            # Would need to load ancestry data to check parent_race
            pass
        
        return result
    
    # =========================================================================
    # PROFESSION VALIDATION
    # =========================================================================
    
    def validate_profession(
        self, 
        profession_id: str, 
        duty_id: str = None
    ) -> ValidationResult:
        """Validate profession selection."""
        result = ValidationResult(valid=True)
        
        if not profession_id:
            result.add_error("Profession is required")
        elif profession_id not in self.valid_profession_ids:
            result.add_error(f"Unknown profession: {profession_id}")
        
        # Duty validation would require loading profession data
        
        return result
    
    # =========================================================================
    # PATH VALIDATION
    # =========================================================================
    
    def validate_path(
        self, 
        path_id: str, 
        ability_scores: Dict[str, int] = None,
        is_primary: bool = True
    ) -> ValidationResult:
        """Validate path selection and prerequisites."""
        result = ValidationResult(valid=True)
        
        if not path_id:
            result.add_error("Path is required")
            return result
        
        if path_id not in self.valid_path_ids:
            result.add_error(f"Unknown path: {path_id}")
            return result
        
        # Check prerequisites if ability scores provided
        if ability_scores and path_id in self.path_prerequisites:
            prereq = self.path_prerequisites[path_id]
            
            primary_attr = prereq.get("primary_attribute")
            primary_min = prereq.get("primary_minimum", 15)
            secondary_attrs = prereq.get("secondary_attributes", [])
            secondary_min = prereq.get("secondary_minimum", 13)
            
            # For primary path, need 15+ in primary attribute
            if is_primary and primary_attr:
                score = self._get_ability_total(ability_scores, primary_attr)
                if score < primary_min:
                    result.add_error(
                        f"Path {path_id} requires {primary_attr} {primary_min}+, you have {score}"
                    )
            
            # Need 13+ in one of the secondary attributes
            if secondary_attrs:
                secondary_min_req = secondary_min if is_primary else secondary_min
                meets_secondary = False
                for attr in secondary_attrs:
                    score = self._get_ability_total(ability_scores, attr)
                    if score >= secondary_min_req:
                        meets_secondary = True
                        break
                
                if not meets_secondary:
                    result.add_error(
                        f"Path {path_id} requires {secondary_min_req}+ in one of: {', '.join(secondary_attrs)}"
                    )
        
        return result
    
    def _get_ability_total(self, scores: Dict[str, Any], ability: str) -> int:
        """Get total ability score, handling both dict and object formats."""
        if ability not in scores:
            return 0
        
        val = scores[ability]
        if isinstance(val, dict):
            return val.get("total", val.get("roll", 0))
        elif hasattr(val, "total"):
            return val.total
        elif isinstance(val, int):
            return val
        return 0
    
    # =========================================================================
    # BACKGROUND VALIDATION
    # =========================================================================
    
    def validate_background(self, background_id: str) -> ValidationResult:
        """Validate background selection."""
        result = ValidationResult(valid=True)
        
        if not background_id:
            result.add_error("Background is required")
        elif background_id not in self.valid_background_ids:
            result.add_error(f"Unknown background: {background_id}")
        
        return result
    
    # =========================================================================
    # SKILL VALIDATION
    # =========================================================================
    
    def validate_skill(self, skill_name: str) -> ValidationResult:
        """Validate a skill name."""
        result = ValidationResult(valid=True)
        
        if not skill_name:
            result.add_error("Skill name is required")
        elif skill_name not in SKILLS:
            result.add_error(f"Unknown skill: {skill_name}")
            # Suggest similar skills
            similar = [s for s in SKILLS if skill_name.lower() in s.lower()]
            if similar:
                result.add_warning(f"Did you mean: {', '.join(similar)}?")
        
        return result
    
    def validate_skill_choices(
        self, 
        chosen: List[str], 
        options: List[str], 
        count: int,
        already_trained: Set[str] = None
    ) -> ValidationResult:
        """Validate skill choices from a list of options."""
        result = ValidationResult(valid=True)
        already_trained = already_trained or set()
        
        if len(chosen) != count:
            result.add_error(f"Must choose exactly {count} skills, got {len(chosen)}")
        
        if len(set(chosen)) != len(chosen):
            result.add_error("Cannot choose the same skill twice")
        
        for skill in chosen:
            if skill not in options:
                result.add_error(f"'{skill}' is not a valid option (choose from: {', '.join(options)})")
            elif skill in already_trained:
                result.add_error(f"'{skill}' is already trained")
        
        return result
    
    # =========================================================================
    # LANGUAGE VALIDATION
    # =========================================================================
    
    def validate_language(self, language: str) -> ValidationResult:
        """Validate a language name."""
        result = ValidationResult(valid=True)
        
        if not language:
            result.add_error("Language name is required")
        elif language not in LANGUAGES:
            result.add_warning(f"Unknown language: {language} (may be valid)")
        
        return result
    
    def validate_language_choices(
        self, 
        chosen: List[str], 
        count: int,
        already_known: Set[str] = None
    ) -> ValidationResult:
        """Validate language choices."""
        result = ValidationResult(valid=True)
        already_known = already_known or set()
        
        if len(chosen) != count:
            result.add_error(f"Must choose exactly {count} languages, got {len(chosen)}")
        
        if len(set(chosen)) != len(chosen):
            result.add_error("Cannot choose the same language twice")
        
        for lang in chosen:
            if lang in already_known:
                result.add_error(f"Already know {lang}")
            result.merge(self.validate_language(lang))
        
        return result
    
    # =========================================================================
    # TALENT VALIDATION
    # =========================================================================
    
    def validate_talent_choice(
        self,
        talent_id: str,
        new_rank: int,
        current_rank: int = 0,
        points_spent: int = None
    ) -> ValidationResult:
        """Validate a talent choice."""
        result = ValidationResult(valid=True)
        
        if not talent_id:
            result.add_error("Talent ID is required")
            return result
        
        if talent_id not in self.valid_talent_ids:
            result.add_warning(f"Unknown talent: {talent_id} (may be valid)")
        
        # Check rank progression
        if new_rank <= current_rank:
            result.add_error(f"New rank ({new_rank}) must be higher than current ({current_rank})")
        
        if new_rank < 1:
            result.add_error(f"Rank must be at least 1 (got {new_rank})")
        
        # Check max rank
        max_rank = self.talent_max_ranks.get(talent_id, 10)
        if new_rank > max_rank:
            result.add_error(f"Talent {talent_id} max rank is {max_rank} (got {new_rank})")
        
        # Check points spent matches rank
        if points_spent is not None and points_spent != new_rank:
            result.add_warning(f"Talent rank {new_rank} typically costs {new_rank} TP (spent {points_spent})")
        
        return result
    
    def validate_talent_points_allocation(
        self,
        choices: List[Dict],
        available_tp: int,
        min_primary_path: int = 4,
        primary_path_id: str = ""
    ) -> ValidationResult:
        """Validate total talent point allocation."""
        result = ValidationResult(valid=True)
        
        total_spent = 0
        primary_spent = 0
        
        for choice in choices:
            points = choice.get("points_spent", choice.get("new_rank", 0))
            total_spent += points
            
            path_id = choice.get("path_id") or ""
            is_primary = (
                choice.get("is_primary_path") is True
                or path_id == "primary"
                or (primary_path_id and path_id == primary_path_id)
            )
            if is_primary:
                primary_spent += points
        
        if total_spent > available_tp:
            result.add_error(f"Spent {total_spent} TP but only have {available_tp}")
        
        if primary_spent < min_primary_path:
            result.add_error(
                f"Must spend at least {min_primary_path} TP in primary path (spent {primary_spent})"
            )
        
        return result
    
    # =========================================================================
    # ADVANCEMENT POINT VALIDATION
    # =========================================================================
    
    def validate_advancement_choice(
        self,
        choice_type: str,
        target: str,
        points_spent: int,
        trained_skills: Set[str] = None,
        known_languages: Set[str] = None,
        known_proficiencies: Set[str] = None
    ) -> ValidationResult:
        """Validate an advancement point purchase."""
        result = ValidationResult(valid=True)
        trained_skills = trained_skills or set()
        known_languages = known_languages or set()
        known_proficiencies = known_proficiencies or set()
        
        valid_types = {"skill_rank", "train_skill", "proficiency", "language", "inherit_gold"}
        
        if choice_type not in valid_types:
            result.add_error(f"Unknown advancement type: {choice_type}")
            return result
        
        # Validate based on type
        if choice_type == "skill_rank":
            if target not in trained_skills:
                result.add_error(f"Cannot increase rank of untrained skill: {target}")
            if points_spent != 1:
                result.add_error(f"Skill rank costs 1 AP (spent {points_spent})")
        
        elif choice_type == "train_skill":
            if target in trained_skills:
                result.add_error(f"Already trained in {target}")
            result.merge(self.validate_skill(target))
            if points_spent != 4:
                result.add_error(f"Training skill costs 4 AP (spent {points_spent})")
        
        elif choice_type == "proficiency":
            if target in known_proficiencies:
                result.add_warning(f"Already have proficiency: {target}")
            if points_spent != 10:
                result.add_error(f"Proficiency costs 10 AP (spent {points_spent})")
        
        elif choice_type == "language":
            if target in known_languages:
                result.add_error(f"Already know language: {target}")
            result.merge(self.validate_language(target))
            if points_spent != 10:
                result.add_error(f"Language costs 10 AP (spent {points_spent})")
        
        return result
    
    # =========================================================================
    # ABILITY INCREASE VALIDATION
    # =========================================================================
    
    def validate_ability_increase(
        self,
        increases: Dict[str, int],
        level: int
    ) -> ValidationResult:
        """Validate ability score increase choice."""
        result = ValidationResult(valid=True)
        
        # Check if level grants ability increase
        ability_levels = {4, 8, 12, 16}
        if level not in ability_levels:
            if increases:
                result.add_error(f"Level {level} does not grant ability increase")
            return result
        
        if not increases:
            result.add_error(f"Level {level} requires an ability increase choice")
            return result
        
        # Validate the increase pattern
        total = sum(increases.values())
        count = len(increases)
        
        if total != 2:
            result.add_error(f"Ability increase must total +2 (got {total})")
        
        if count == 1:
            if list(increases.values())[0] != 2:
                result.add_error("Single ability increase must be +2")
        elif count == 2:
            if not all(v == 1 for v in increases.values()):
                result.add_error("Two ability increases must each be +1")
        else:
            result.add_error(f"Can increase 1 or 2 abilities, not {count}")
        
        # Check ability names
        for ability in increases:
            if ability not in ABILITY_NAMES:
                result.add_error(f"Unknown ability: {ability}")
        
        return result
    
    # =========================================================================
    # COMPLETE CHARACTER VALIDATION
    # =========================================================================
    
    def validate_character(self, character: Dict[str, Any]) -> ValidationResult:
        """Validate a complete character."""
        result = ValidationResult(valid=True)
        
        def _enum_to_value(value):
            return value.value if hasattr(value, "value") else value

        # Basic required fields (accept enums or strings)
        required = ["race", "ancestry", "profession", "primary_path", "background"]
        for field in required:
            if field not in character or character.get(field) in (None, ""):
                result.add_error(f"Missing required field: {field}")
            else:
                character[field] = _enum_to_value(character[field])
        
        # Validate ability scores
        if "ability_scores" in character:
            scores = {}
            for name, data in character["ability_scores"].items():
                if isinstance(data, dict):
                    scores[name] = data.get("total", data.get("roll", 0))
                else:
                    scores[name] = data
            result.merge(self.validate_ability_scores(scores))
        else:
            result.add_error("Missing ability_scores")
        
        # Validate individual selections
        if character.get("race"):
            race_val = _enum_to_value(character["race"])
            race_id = str(race_val).lower().replace(" ", "_")
            result.merge(self.validate_race(race_id))
        
        if character.get("primary_path"):
            path_val = _enum_to_value(character["primary_path"])
            path_id = str(path_val).lower().replace(" ", "_")
            result.merge(self.validate_path(
                path_id, 
                character.get("ability_scores"),
                is_primary=True
            ))
        
        # Validate level
        level = character.get("level", 1)
        if not isinstance(level, int) or level < 1:
            result.add_error(f"Invalid level: {level}")
        elif level > 20:
            result.add_warning(f"Level {level} is above standard max (20)")
        
        # Validate HP
        hp = character.get("health", {})
        if isinstance(hp, dict):
            max_hp = hp.get("max", 0)
            if max_hp < 1:
                result.add_error(f"Max HP must be at least 1 (got {max_hp})")
        
        return result
    
    def validate_level_up(
        self,
        current_level: int,
        target_level: int,
        talent_choices: List[Dict] = None,
        advancement_choices: List[Dict] = None,
        ability_increase: Dict[str, int] = None,
        available_tp: int = 0,
        available_ap: int = 0,
        min_primary_path_points: int = 0,
        primary_path_id: str = ""
    ) -> ValidationResult:
        """Validate a level up operation."""
        result = ValidationResult(valid=True)
        
        if target_level <= current_level:
            result.add_error(f"Target level ({target_level}) must exceed current ({current_level})")
        
        # Validate talent choices
        if talent_choices:
            result.merge(self.validate_talent_points_allocation(
                talent_choices,
                available_tp,
                min_primary_path=min_primary_path_points,
                primary_path_id=primary_path_id,
            ))
            for choice in talent_choices:
                result.merge(self.validate_talent_choice(
                    choice.get("talent_id", ""),
                    choice.get("new_rank", 0),
                    choice.get("current_rank", 0),
                    choice.get("points_spent")
                ))
        
        # Validate advancement choices
        if advancement_choices:
            total_ap = sum(c.get("points_spent", 0) for c in advancement_choices)
            if total_ap > available_ap:
                result.add_error(f"Spent {total_ap} AP but only have {available_ap}")
        
        # Validate ability increase
        if ability_increase:
            result.merge(self.validate_ability_increase(ability_increase, target_level))
        
        return result
