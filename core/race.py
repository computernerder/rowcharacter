"""
Race dataclass - represents racial traits loaded from JSON.

Races provide:
- Creature type
- Size
- Speed
- Languages
- Special features (narrative abilities)
- Darkvision (if any)
- Core ability adjustment
- Skill proficiencies (if any)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, TYPE_CHECKING
import json
from pathlib import Path

from .common import Feature

if TYPE_CHECKING:
    from template_model import CharacterTemplate


@dataclass
class Race:
    """A playable race loaded from JSON data."""
    
    id: str
    name: str
    description: str = ""
    
    # Core traits
    creature_type: str = "Humanoid"
    size: str = "Medium"
    speed: int = 30
    
    # Languages granted
    languages: List[str] = field(default_factory=list)
    bonus_language_choices: int = 0  # How many extra languages to choose
    
    # Vision
    darkvision: int = 0  # 0 means no darkvision
    
    # Ability adjustments: {"Intellect": 1, "Charisma": -1}
    ability_modifiers: Dict[str, int] = field(default_factory=dict)
    
    # Flexible ability adjustment (like humans)
    # e.g., {"points": 1, "count": 1} means +1 to one ability
    # or {"points": 2, "count": 2, "penalty": -1} means +2 to one, -1 to another
    flexible_ability_adjustment: Optional[Dict[str, Any]] = None
    
    # Skill proficiencies granted
    skill_proficiencies: List[str] = field(default_factory=list)
    
    # Skill bonuses (misc bonus, not full proficiency)
    skill_bonuses: Dict[str, int] = field(default_factory=dict)
    
    # Skill choices: {"count": 2, "options": ["Athletics", "Perception"]}
    skill_choices: Optional[Dict[str, Any]] = None
    
    # Special features (narrative abilities)
    features: List[Feature] = field(default_factory=list)
    
    # List of valid ancestry IDs for this race
    ancestries: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Race":
        features = [Feature.from_dict(f) for f in data.get("features", [])]
        
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            creature_type=data.get("creature_type", "Humanoid"),
            size=data.get("size", "Medium"),
            speed=data.get("speed", 30),
            languages=data.get("languages", []),
            bonus_language_choices=data.get("bonus_language_choices", 0),
            darkvision=data.get("darkvision", 0),
            ability_modifiers=data.get("ability_modifiers", {}),
            flexible_ability_adjustment=data.get("flexible_ability_adjustment"),
            skill_proficiencies=data.get("skill_proficiencies", []),
            skill_bonuses=data.get("skill_bonuses", {}),
            skill_choices=data.get("skill_choices"),
            features=[Feature.from_dict(f) for f in data.get("features", [])],
            ancestries=data.get("ancestries", []),
        )

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "creature_type": self.creature_type,
            "size": self.size,
            "speed": self.speed,
            "languages": self.languages,
            "bonus_language_choices": self.bonus_language_choices,
            "darkvision": self.darkvision,
            "ability_modifiers": self.ability_modifiers,
            "skill_proficiencies": self.skill_proficiencies,
            "skill_bonuses": self.skill_bonuses,
            "features": [f.to_dict() for f in self.features],
            "ancestries": self.ancestries,
        }
        if self.flexible_ability_adjustment:
            result["flexible_ability_adjustment"] = self.flexible_ability_adjustment
        if self.skill_choices:
            result["skill_choices"] = self.skill_choices
        return result

    def apply(self, character: "CharacterTemplate") -> None:
        """
        Apply racial traits to a character object.
        
        Args:
            character: The CharacterTemplate to modify
        """
        # Set physical traits
        character.physical_traits.creature_type = self.creature_type
        character.physical_traits.size = self.size
        character.speed = self.speed
        
        # Add languages
        for lang in self.languages:
            if lang not in character.languages:
                character.languages.append(lang)
        
        # Apply ability modifiers
        for ability, mod in self.ability_modifiers.items():
            if ability in character.ability_scores:
                character.ability_scores[ability].race += mod
                character.ability_scores[ability].total += mod
        
        # Add skill proficiencies
        for skill in self.skill_proficiencies:
            if skill in character.skills:
                character.skills[skill].trained = True
                if character.skills[skill].rank == 0:
                    character.skills[skill].rank = 1
        
        # Apply skill bonuses (misc modifier)
        for skill, bonus in self.skill_bonuses.items():
            if skill in character.skills:
                character.skills[skill].misc += bonus
        
        # Add features
        for feature in self.features:
            character.features.append({
                "name": feature.name,
                "text": feature.description,
            })
        
        # Note: flexible_ability_adjustment and skill_choices require user input
        # and should be handled by the character builder wizard


def load_race(filepath: str) -> Race:
    """Load a race from a JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return Race.from_dict(data)


def load_all_races(directory: str) -> Dict[str, Race]:
    """Load all races from a directory of JSON files."""
    races = {}
    path = Path(directory)
    for file in path.glob("*.json"):
        race = load_race(str(file))
        races[race.id] = race
    return races
