"""
Ancestry dataclass - represents ancestry traits loaded from JSON.

Ancestries provide:
- Additional ability adjustment
- Special abilities (narrative)
- Personality suggestions
- Bonus language
- Reputation modifier
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, TYPE_CHECKING
import json
from pathlib import Path

from .common import Feature, ReputationModifier

if TYPE_CHECKING:
    from template_model import CharacterTemplate


@dataclass
class Ancestry:
    """An ancestry (sub-race) loaded from JSON data."""
    
    id: str
    name: str
    race_id: str  # Reference to parent race
    description: str = ""
    
    # Region of origin
    region: str = ""
    
    # Ability adjustments: {"Wisdom": 1}
    ability_modifiers: Dict[str, int] = field(default_factory=dict)
    
    # Bonus languages granted
    languages: List[str] = field(default_factory=list)
    
    # Language choices: {"count": 1, "options": ["Elvish", "Dwarvish"]}
    language_choices: Optional[Dict[str, Any]] = None
    
    # Special abilities (narrative features)
    features: List[Feature] = field(default_factory=list)
    
    # Skill proficiencies granted
    skill_proficiencies: List[str] = field(default_factory=list)
    
    # Skill bonuses (not full proficiency, just a bonus)
    skill_bonuses: Dict[str, int] = field(default_factory=dict)
    
    # Tool proficiencies granted
    tool_proficiencies: List[str] = field(default_factory=list)
    
    # Reputation modifier
    reputation_modifier: Optional[ReputationModifier] = None
    
    # Personality suggestion (for roleplay guidance)
    personality: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Ancestry":
        rep_data = data.get("reputation_modifier")
        rep_mod = ReputationModifier.from_dict(rep_data) if rep_data else None
        
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            race_id=data.get("race_id", ""),
            description=data.get("description", ""),
            region=data.get("region", ""),
            ability_modifiers=data.get("ability_modifiers", {}),
            languages=data.get("languages", []),
            language_choices=data.get("language_choices"),
            features=[Feature.from_dict(f) for f in data.get("features", [])],
            skill_proficiencies=data.get("skill_proficiencies", []),
            skill_bonuses=data.get("skill_bonuses", {}),
            tool_proficiencies=data.get("tool_proficiencies", []),
            reputation_modifier=rep_mod,
            personality=data.get("personality", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "name": self.name,
            "race_id": self.race_id,
            "description": self.description,
            "region": self.region,
            "ability_modifiers": self.ability_modifiers,
            "languages": self.languages,
            "features": [f.to_dict() for f in self.features],
            "skill_proficiencies": self.skill_proficiencies,
            "skill_bonuses": self.skill_bonuses,
            "tool_proficiencies": self.tool_proficiencies,
            "personality": self.personality,
        }
        if self.language_choices:
            result["language_choices"] = self.language_choices
        if self.reputation_modifier:
            result["reputation_modifier"] = self.reputation_modifier.to_dict()
        return result

    def apply(self, character: "CharacterTemplate") -> None:
        """
        Apply ancestry traits to a character object.
        
        Args:
            character: The CharacterTemplate to modify
        """
        # Apply ability modifiers
        for ability, mod in self.ability_modifiers.items():
            if ability in character.ability_scores:
                character.ability_scores[ability].race += mod
                character.ability_scores[ability].total += mod
        
        # Add languages
        for lang in self.languages:
            if lang not in character.languages:
                character.languages.append(lang)
        
        # Add skill proficiencies
        for skill in self.skill_proficiencies:
            if skill in character.skills:
                character.skills[skill].trained = True
                if character.skills[skill].rank == 0:
                    character.skills[skill].rank = 1
        
        # Apply skill bonuses
        for skill, bonus in self.skill_bonuses.items():
            if skill in character.skills:
                character.skills[skill].misc += bonus
        
        # Add tool proficiencies
        for tool in self.tool_proficiencies:
            if tool not in character.proficiencies:
                character.proficiencies.append(tool)
        
        # Add features
        for feature in self.features:
            character.features.append({
                "name": feature.name,
                "text": feature.description,
            })
        
        # Apply reputation modifier
        if self.reputation_modifier:
            character.reputation.mod += self.reputation_modifier.value
        
        # Note: language_choices require user input
        # and should be handled by the character builder wizard


def load_ancestry(filepath: str) -> Ancestry:
    """Load an ancestry from a JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return Ancestry.from_dict(data)


def load_all_ancestries(directory: str) -> Dict[str, Ancestry]:
    """Load all ancestries from a directory of JSON files."""
    ancestries = {}
    path = Path(directory)
    for file in path.glob("*.json"):
        ancestry = load_ancestry(str(file))
        ancestries[ancestry.id] = ancestry
    return ancestries


def get_ancestries_for_race(ancestries: Dict[str, Ancestry], race_id: str) -> List[Ancestry]:
    """Get all ancestries that belong to a specific race."""
    return [a for a in ancestries.values() if a.race_id == race_id]
