"""
Background dataclass - represents background traits loaded from JSON.

Backgrounds provide:
- Skill proficiencies
- Languages granted (count to choose)
- Tool proficiencies (if any)
- Equipment
- Feature (narrative ability)
- Personality tables (traits, ideals, bonds, flaws)
- Morality/reputation modifiers from personality choices
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, TYPE_CHECKING
import json
from pathlib import Path

from .common import Feature

if TYPE_CHECKING:
    from template_model import CharacterTemplate


@dataclass
class PersonalityEntry:
    """A single entry in a personality table."""
    roll: int  # d8 for traits, d6 for ideals/bonds/flaws
    text: str
    morality: int = 0
    reputation: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonalityEntry":
        return cls(
            roll=data.get("roll", 1),
            text=data.get("text", ""),
            morality=data.get("morality", 0),
            reputation=data.get("reputation", 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "roll": self.roll,
            "text": self.text,
            "morality": self.morality,
            "reputation": self.reputation,
        }


@dataclass
class PersonalityTables:
    """Personality tables for a background."""
    traits: List[PersonalityEntry] = field(default_factory=list)  # d8
    ideals: List[PersonalityEntry] = field(default_factory=list)  # d6
    bonds: List[PersonalityEntry] = field(default_factory=list)   # d6
    flaws: List[PersonalityEntry] = field(default_factory=list)   # d6

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonalityTables":
        return cls(
            traits=[PersonalityEntry.from_dict(e) for e in data.get("traits", [])],
            ideals=[PersonalityEntry.from_dict(e) for e in data.get("ideals", [])],
            bonds=[PersonalityEntry.from_dict(e) for e in data.get("bonds", [])],
            flaws=[PersonalityEntry.from_dict(e) for e in data.get("flaws", [])],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "traits": [e.to_dict() for e in self.traits],
            "ideals": [e.to_dict() for e in self.ideals],
            "bonds": [e.to_dict() for e in self.bonds],
            "flaws": [e.to_dict() for e in self.flaws],
        }


@dataclass
class Background:
    """A background loaded from JSON data."""
    
    id: str
    name: str
    description: str = ""
    
    # Skill proficiencies granted
    skill_proficiencies: List[str] = field(default_factory=list)
    
    # Languages granted (count to choose)
    languages_granted: int = 0
    
    # Tool proficiencies
    tool_proficiencies: List[str] = field(default_factory=list)
    
    # Equipment
    equipment: List[str] = field(default_factory=list)
    
    # Feature (narrative ability)
    feature: Optional[Feature] = None
    
    # Personality tables
    personality_tables: Optional[PersonalityTables] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Background":
        feature_data = data.get("feature")
        feature = Feature.from_dict(feature_data) if feature_data else None
        
        tables_data = data.get("personality_tables")
        tables = PersonalityTables.from_dict(tables_data) if tables_data else None
        
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            skill_proficiencies=data.get("skill_proficiencies", []),
            languages_granted=data.get("languages_granted", 0),
            tool_proficiencies=data.get("tool_proficiencies", []),
            equipment=data.get("equipment", []),
            feature=feature,
            personality_tables=tables,
        )

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "skill_proficiencies": self.skill_proficiencies,
            "languages_granted": self.languages_granted,
            "tool_proficiencies": self.tool_proficiencies,
            "equipment": self.equipment,
        }
        if self.feature:
            result["feature"] = self.feature.to_dict()
        if self.personality_tables:
            result["personality_tables"] = self.personality_tables.to_dict()
        return result

    def apply(self, character: "CharacterTemplate", chosen_languages: List[str] = None,
              chosen_trait: PersonalityEntry = None,
              chosen_ideal: PersonalityEntry = None,
              chosen_bond: PersonalityEntry = None,
              chosen_flaw: PersonalityEntry = None) -> None:
        """
        Apply background traits to a character object.
        
        Args:
            character: The CharacterTemplate to modify
            chosen_languages: Languages chosen by the user
            chosen_trait/ideal/bond/flaw: Personality choices
        """
        # Add skill proficiencies
        for skill in self.skill_proficiencies:
            if skill in character.skills:
                character.skills[skill].trained = True
                if character.skills[skill].rank == 0:
                    character.skills[skill].rank = 1
        
        # Add chosen languages
        if chosen_languages:
            for lang in chosen_languages:
                if lang not in character.languages:
                    character.languages.append(lang)
        
        # Add tool proficiencies
        for prof in self.tool_proficiencies:
            if prof not in character.proficiencies:
                character.proficiencies.append(prof)
        
        # Add equipment to inventory
        for item in self.equipment:
            character.inventory.items.append(item)
        
        # Add feature
        if self.feature:
            character.features.append({
                "name": self.feature.name,
                "text": self.feature.description,
            })
        
        # Apply personality choices
        morality_total = 0
        reputation_total = 0
        
        if chosen_trait:
            character.personality.traits = chosen_trait.text
            morality_total += chosen_trait.morality
            reputation_total += chosen_trait.reputation
        
        if chosen_ideal:
            character.personality.ideal = chosen_ideal.text
            morality_total += chosen_ideal.morality
            reputation_total += chosen_ideal.reputation
        
        if chosen_bond:
            character.personality.bond = chosen_bond.text
            morality_total += chosen_bond.morality
            reputation_total += chosen_bond.reputation
        
        if chosen_flaw:
            character.personality.flaw = chosen_flaw.text
            morality_total += chosen_flaw.morality
            reputation_total += chosen_flaw.reputation
        
        # Update alignment/reputation scores
        character.alignment.mod += morality_total
        character.reputation.mod += reputation_total

    def calculate_morality(self, ideal: PersonalityEntry, 
                          bond: PersonalityEntry, 
                          flaw: PersonalityEntry) -> int:
        """Calculate total morality score from personality choices."""
        return ideal.morality + bond.morality + flaw.morality

    def calculate_reputation(self, ideal: PersonalityEntry,
                            bond: PersonalityEntry,
                            flaw: PersonalityEntry) -> int:
        """Calculate total reputation modifier from personality choices."""
        return ideal.reputation + bond.reputation + flaw.reputation


def load_background(filepath: str) -> Background:
    """Load a background from a JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return Background.from_dict(data)


def load_all_backgrounds(directory: str) -> Dict[str, Background]:
    """Load all backgrounds from a directory of JSON files."""
    backgrounds = {}
    path = Path(directory)
    for file in path.glob("*.json"):
        background = load_background(str(file))
        backgrounds[background.id] = background
    return backgrounds
