"""
Path dataclass - represents path traits loaded from JSON.

Paths provide:
- Prerequisites (primary ability 15+, secondary 13+)
- Primary bonus (ability adjustments when this is Primary Path)
- Talent points attribute
- Attack bonuses (melee/ranged)
- Role
- Features (narrative abilities)
- Available talents (list of talent IDs)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, TYPE_CHECKING
import json
from pathlib import Path as FilePath

from .common import Feature

if TYPE_CHECKING:
    from template_model import CharacterTemplate


@dataclass
class PathPrerequisite:
    """Prerequisites for taking a path."""
    
    # Primary attribute must be 15+ for primary path
    primary_attribute: str
    primary_minimum: int = 15
    
    # Must have 13+ in ONE of these for primary path
    secondary_attributes: List[str] = field(default_factory=list)
    secondary_minimum: int = 13

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PathPrerequisite":
        primary = data.get("primary", {})
        secondary = data.get("secondary", {})
        
        return cls(
            primary_attribute=primary.get("attribute", ""),
            primary_minimum=primary.get("minimum", 15),
            secondary_attributes=secondary.get("options", []),
            secondary_minimum=secondary.get("minimum", 13),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary": {
                "attribute": self.primary_attribute,
                "minimum": self.primary_minimum,
            },
            "secondary": {
                "options": self.secondary_attributes,
                "minimum": self.secondary_minimum,
            },
        }

    def check(self, ability_scores: Dict[str, Any], is_primary: bool = True) -> bool:
        """
        Check if ability scores meet prerequisites.
        
        Args:
            ability_scores: Dict of ability name -> AbilityScore object (with .total)
            is_primary: If True, check full prerequisites. If False, only check primary attr.
        
        Returns:
            True if prerequisites are met.
        """
        def get_score(attr: str) -> int:
            val = ability_scores.get(attr)
            if val is None:
                return 0
            if hasattr(val, 'total'):
                return val.total
            return int(val)
        
        # Check primary attribute
        primary_met = get_score(self.primary_attribute) >= self.primary_minimum
        
        if not is_primary:
            # Secondary path only needs primary attribute check
            return primary_met
        
        # Primary path also needs secondary attribute check
        secondary_met = any(
            get_score(attr) >= self.secondary_minimum 
            for attr in self.secondary_attributes
        )
        
        return primary_met and secondary_met


@dataclass
class Path:
    """A path loaded from JSON data."""
    
    id: str
    name: str
    description: str = ""
    
    # Prerequisites
    prerequisites: Optional[PathPrerequisite] = None
    
    # Primary bonus (only applied when this is Primary Path)
    # e.g., {"Endurance": 2, "Wisdom": 2}
    primary_bonus: Dict[str, int] = field(default_factory=dict)
    
    # Attribute used for calculating Talent Points (modifier + 5)
    talent_points_attribute: str = ""
    
    # Attack bonuses granted
    attack_bonus_melee: int = 0
    attack_bonus_ranged: int = 0
    
    # Combat/narrative role
    role: str = ""
    
    # Whether this path grants spellcasting (Mystic)
    spellcasting: bool = False
    
    # Features (narrative abilities)
    features: List[Feature] = field(default_factory=list)
    
    # List of talent IDs available to this path
    talents: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Path":
        prereq_data = data.get("prerequisites")
        prerequisites = PathPrerequisite.from_dict(prereq_data) if prereq_data else None
        
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            prerequisites=prerequisites,
            primary_bonus=data.get("primary_bonus", {}),
            talent_points_attribute=data.get("talent_points_attribute", ""),
            attack_bonus_melee=data.get("attack_bonus_melee", 0),
            attack_bonus_ranged=data.get("attack_bonus_ranged", 0),
            role=data.get("role", ""),
            spellcasting=data.get("spellcasting", False),
            features=[Feature.from_dict(f) for f in data.get("features", [])],
            talents=data.get("talents", []),
        )

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "primary_bonus": self.primary_bonus,
            "talent_points_attribute": self.talent_points_attribute,
            "attack_bonus_melee": self.attack_bonus_melee,
            "attack_bonus_ranged": self.attack_bonus_ranged,
            "role": self.role,
            "spellcasting": self.spellcasting,
            "features": [f.to_dict() for f in self.features],
            "talents": self.talents,
        }
        if self.prerequisites:
            result["prerequisites"] = self.prerequisites.to_dict()
        return result

    def check_prerequisites(self, ability_scores: Dict[str, Any], is_primary: bool = True) -> bool:
        """Check if character meets prerequisites for this path."""
        if not self.prerequisites:
            return True
        return self.prerequisites.check(ability_scores, is_primary)

    def apply(self, character: "CharacterTemplate", is_primary: bool = True) -> None:
        """
        Apply path traits to a character object.
        
        Args:
            character: The CharacterTemplate to modify
            is_primary: Whether this is the character's Primary Path
        """
        # Apply primary bonus only if this is the Primary Path
        if is_primary:
            for ability, bonus in self.primary_bonus.items():
                if ability in character.ability_scores:
                    # Primary path bonus goes into misc (not race)
                    character.ability_scores[ability].misc += bonus
                    character.ability_scores[ability].total += bonus
        
        # Apply attack bonuses
        character.attack_mods_melee.misc += self.attack_bonus_melee
        character.attack_mods_melee.total = (
            character.attack_mods_melee.attr + character.attack_mods_melee.misc
        )
        
        character.attack_mods_ranged.misc += self.attack_bonus_ranged
        character.attack_mods_ranged.total = (
            character.attack_mods_ranged.attr + character.attack_mods_ranged.misc
        )
        
        # Add features
        for feature in self.features:
            character.features.append({
                "name": feature.name,
                "text": feature.description,
            })

    def calculate_talent_points(self, ability_scores: Dict[str, Any]) -> int:
        """
        Calculate talent points per level from this path.
        
        Formula: ability modifier + 5
        """
        if not self.talent_points_attribute:
            return 5  # Default
        
        score = ability_scores.get(self.talent_points_attribute)
        if score is None:
            return 5
        
        if hasattr(score, 'mod'):
            modifier = score.mod
        elif hasattr(score, 'total'):
            modifier = (score.total - 10) // 2
        else:
            modifier = (int(score) - 10) // 2
        
        return modifier + 5


def load_path(filepath: str) -> Path:
    """Load a path from a JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return Path.from_dict(data)


def load_all_paths(directory: str) -> Dict[str, Path]:
    """Load all paths from a directory of JSON files."""
    paths = {}
    dir_path = FilePath(directory)
    for file in dir_path.glob("*.json"):
        path = load_path(str(file))
        paths[path.id] = path
    return paths
