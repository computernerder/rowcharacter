"""
Profession dataclass - represents profession traits loaded from JSON.

Professions provide:
- Base HP
- Feature (narrative ability)
- Armor proficiencies
- Weapon proficiencies
- Tool proficiencies (some with choices)
- Skill choices
- Suggested paths
- Duties (sub-options for some professions)
- Equipment pack or gold alternative
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, TYPE_CHECKING
import json
from pathlib import Path

from .common import Feature

if TYPE_CHECKING:
    from template_model import CharacterTemplate


@dataclass
class Duty:
    """A duty sub-option for professions like Warrior."""
    
    id: str
    name: str
    description: str = ""
    
    # Suggested paths for this duty
    suggested_paths: List[str] = field(default_factory=list)
    
    # Additional proficiencies from this duty
    armor_proficiencies: List[str] = field(default_factory=list)
    weapon_proficiencies: List[str] = field(default_factory=list)
    
    # Tool choices: {"count": 1, "options": ["whetstone kit", "armorer's tools"]}
    tool_choices: Optional[Dict[str, Any]] = None
    
    # Skill choices: {"count": 1, "options": ["Athletics", "Intimidation"]}
    skill_choices: Optional[Dict[str, Any]] = None
    
    # Equipment pack
    equipment_pack: str = ""
    gold_alternative: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Duty":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            suggested_paths=data.get("suggested_paths", []),
            armor_proficiencies=data.get("armor_proficiencies", []),
            weapon_proficiencies=data.get("weapon_proficiencies", []),
            tool_choices=data.get("tool_choices"),
            skill_choices=data.get("skill_choices"),
            equipment_pack=data.get("equipment_pack", ""),
            gold_alternative=data.get("gold_alternative", 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "suggested_paths": self.suggested_paths,
            "armor_proficiencies": self.armor_proficiencies,
            "weapon_proficiencies": self.weapon_proficiencies,
            "equipment_pack": self.equipment_pack,
            "gold_alternative": self.gold_alternative,
        }
        if self.tool_choices:
            result["tool_choices"] = self.tool_choices
        if self.skill_choices:
            result["skill_choices"] = self.skill_choices
        return result


@dataclass
class Profession:
    """A profession loaded from JSON data."""
    
    id: str
    name: str
    description: str = ""
    
    # Base HP granted by this profession
    base_hp: int = 8
    
    # Feature (narrative ability)
    feature: Optional[Feature] = None
    
    # Proficiencies
    armor_proficiencies: List[str] = field(default_factory=list)
    weapon_proficiencies: List[str] = field(default_factory=list)
    tool_proficiencies: List[str] = field(default_factory=list)
    
    # Tool choices: {"count": 1, "options": ["artisan tool", "gaming set"]}
    tool_choices: Optional[Dict[str, Any]] = None
    
    # Skill choices: {"count": 2, "options": ["Athletics", "Intimidation", "Perception"]}
    skill_choices: Optional[Dict[str, Any]] = None
    
    # Suggested paths
    suggested_paths: List[str] = field(default_factory=list)
    
    # Duties (sub-options, e.g., Fighter/Ranger for Warrior)
    duties: List[Duty] = field(default_factory=list)
    
    # Equipment pack (if no duties)
    equipment_pack: str = ""
    gold_alternative: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Profession":
        feature_data = data.get("feature")
        feature = Feature.from_dict(feature_data) if feature_data else None
        
        duties = [Duty.from_dict(d) for d in data.get("duties", [])]
        
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            base_hp=data.get("base_hp", 8),
            feature=feature,
            armor_proficiencies=data.get("armor_proficiencies", []),
            weapon_proficiencies=data.get("weapon_proficiencies", []),
            tool_proficiencies=data.get("tool_proficiencies", []),
            tool_choices=data.get("tool_choices"),
            skill_choices=data.get("skill_choices"),
            suggested_paths=data.get("suggested_paths", []),
            duties=duties,
            equipment_pack=data.get("equipment_pack", ""),
            gold_alternative=data.get("gold_alternative", 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "base_hp": self.base_hp,
            "armor_proficiencies": self.armor_proficiencies,
            "weapon_proficiencies": self.weapon_proficiencies,
            "tool_proficiencies": self.tool_proficiencies,
            "suggested_paths": self.suggested_paths,
            "duties": [d.to_dict() for d in self.duties],
            "equipment_pack": self.equipment_pack,
            "gold_alternative": self.gold_alternative,
        }
        if self.feature:
            result["feature"] = self.feature.to_dict()
        if self.tool_choices:
            result["tool_choices"] = self.tool_choices
        if self.skill_choices:
            result["skill_choices"] = self.skill_choices
        return result

    def apply(self, character: "CharacterTemplate", chosen_skills: List[str] = None, 
              chosen_tools: List[str] = None, chosen_duty: "Duty" = None) -> None:
        """
        Apply profession traits to a character object.
        
        Args:
            character: The CharacterTemplate to modify
            chosen_skills: List of skill names chosen by the user
            chosen_tools: List of tool names chosen by the user
            chosen_duty: The duty chosen (for professions with duties)
        """
        # Set base HP (profession base + Endurance modifier)
        end_score = character.ability_scores.get("Endurance")
        if end_score:
            character.health.max = self.base_hp + end_score.mod
            character.health.current = character.health.max
        else:
            character.health.max = self.base_hp
            character.health.current = self.base_hp
        
        # Add feature
        if self.feature:
            character.features.append({
                "name": self.feature.name,
                "text": self.feature.description,
            })
        
        # Add armor proficiencies
        for prof in self.armor_proficiencies:
            if prof not in character.proficiencies:
                character.proficiencies.append(prof)
        
        # Add weapon proficiencies
        for prof in self.weapon_proficiencies:
            if prof not in character.proficiencies:
                character.proficiencies.append(prof)
        
        # Add tool proficiencies
        for prof in self.tool_proficiencies:
            if prof not in character.proficiencies:
                character.proficiencies.append(prof)
        
        # Add chosen tools
        if chosen_tools:
            for tool in chosen_tools:
                if tool not in character.proficiencies:
                    character.proficiencies.append(tool)
        
        # Train chosen skills
        if chosen_skills:
            for skill in chosen_skills:
                if skill in character.skills:
                    character.skills[skill].trained = True
                    if character.skills[skill].rank == 0:
                        character.skills[skill].rank = 1
        
        # Apply duty if chosen
        if chosen_duty:
            self._apply_duty(character, chosen_duty)

    def _apply_duty(self, character: "CharacterTemplate", duty: Duty) -> None:
        """Apply duty-specific traits."""
        # Add additional proficiencies from duty
        for prof in duty.armor_proficiencies:
            if prof not in character.proficiencies:
                character.proficiencies.append(prof)
        
        for prof in duty.weapon_proficiencies:
            if prof not in character.proficiencies:
                character.proficiencies.append(prof)


def load_profession(filepath: str) -> Profession:
    """Load a profession from a JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return Profession.from_dict(data)


def load_all_professions(directory: str) -> Dict[str, Profession]:
    """Load all professions from a directory of JSON files."""
    professions = {}
    path = Path(directory)
    for file in path.glob("*.json"):
        profession = load_profession(str(file))
        professions[profession.id] = profession
    return professions
