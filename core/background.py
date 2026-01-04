"""
Background class for Realm of Warriors character creation.

Backgrounds provide:
- Skill proficiencies (2 skills)
- Languages (0-2 choices)
- Tool proficiencies (0-1)
- Starting equipment
- Background feature
- Personality tables (traits, ideals, bonds, flaws)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import json
from pathlib import Path


@dataclass
class PersonalityEntry:
    """A single entry in a personality table (ideal, bond, flaw, trait)."""
    roll: int
    text: str
    morality: int = 0       # -1 to +1
    reputation: int = 0     # -2 to +2


@dataclass
class PersonalityTables:
    """Complete personality tables for a background."""
    traits: List[PersonalityEntry] = field(default_factory=list)
    ideals: List[PersonalityEntry] = field(default_factory=list)
    bonds: List[PersonalityEntry] = field(default_factory=list)
    flaws: List[PersonalityEntry] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonalityTables":
        """Create from dictionary."""
        def parse_entries(entries: List[Dict]) -> List[PersonalityEntry]:
            result = []
            for e in entries:
                result.append(PersonalityEntry(
                    roll=e.get("roll", 0),
                    text=e.get("text", ""),
                    morality=e.get("morality", 0),
                    reputation=e.get("reputation", 0),
                ))
            return result
        
        return cls(
            traits=parse_entries(data.get("traits", [])),
            ideals=parse_entries(data.get("ideals", [])),
            bonds=parse_entries(data.get("bonds", [])),
            flaws=parse_entries(data.get("flaws", [])),
        )


@dataclass
class BackgroundFeature:
    """A special feature granted by a background."""
    name: str
    description: str


@dataclass
class Background:
    """
    Represents a character background.
    
    Backgrounds provide roleplay hooks, skills, and starting equipment.
    """
    id: str
    name: str
    description: str
    
    # Proficiencies
    skill_proficiencies: List[str] = field(default_factory=list)
    tool_proficiencies: List[str] = field(default_factory=list)
    
    # Languages
    languages_granted: int = 0  # Number of languages to choose
    
    # Equipment
    equipment: List[str] = field(default_factory=list)
    
    # Feature
    feature: Optional[BackgroundFeature] = None
    
    # Personality
    personality_tables: Optional[PersonalityTables] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Background":
        """Create a Background from a dictionary (loaded from JSON)."""
        feature = None
        if "feature" in data and data["feature"]:
            feature = BackgroundFeature(
                name=data["feature"].get("name", ""),
                description=data["feature"].get("description", ""),
            )
        
        personality = None
        if "personality_tables" in data:
            personality = PersonalityTables.from_dict(data["personality_tables"])
        
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            skill_proficiencies=data.get("skill_proficiencies", []),
            tool_proficiencies=data.get("tool_proficiencies", []),
            languages_granted=data.get("languages_granted", 0),
            equipment=data.get("equipment", []),
            feature=feature,
            personality_tables=personality,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "skill_proficiencies": self.skill_proficiencies,
            "tool_proficiencies": self.tool_proficiencies,
            "languages_granted": self.languages_granted,
            "equipment": self.equipment,
        }
        
        if self.feature:
            result["feature"] = {
                "name": self.feature.name,
                "description": self.feature.description,
            }
        
        if self.personality_tables:
            result["personality_tables"] = {
                "traits": [{"roll": e.roll, "text": e.text} for e in self.personality_tables.traits],
                "ideals": [{"roll": e.roll, "text": e.text, "morality": e.morality, "reputation": e.reputation} for e in self.personality_tables.ideals],
                "bonds": [{"roll": e.roll, "text": e.text, "morality": e.morality, "reputation": e.reputation} for e in self.personality_tables.bonds],
                "flaws": [{"roll": e.roll, "text": e.text, "morality": e.morality, "reputation": e.reputation} for e in self.personality_tables.flaws],
            }
        
        return result
    
    def apply(self, character: Any) -> List[Dict[str, Any]]:
        """
        Apply this background to a character.
        
        Returns list of pending choices (e.g., language selection).
        """
        pending = []
        
        # Apply skill proficiencies
        for skill in self.skill_proficiencies:
            if skill in character.skills:
                if not character.skills[skill].trained:
                    character.skills[skill].trained = True
                    character.skills[skill].rank = 1
        
        # Apply tool proficiencies
        for tool in self.tool_proficiencies:
            if tool not in character.proficiencies:
                character.proficiencies.append(tool)
        
        # Apply feature
        if self.feature:
            character.features.append({
                "name": self.feature.name,
                "text": self.feature.description,
                "source": f"Background: {self.name}",
            })
        
        # Queue language choices
        if self.languages_granted > 0:
            pending.append({
                "type": "language",
                "count": self.languages_granted,
                "source": f"Background: {self.name}",
            })
        
        return pending


def load_background(filepath: str) -> Background:
    """Load a background from a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Background.from_dict(data)


def load_all_backgrounds(directory: str) -> Dict[str, Background]:
    """Load all backgrounds from a directory."""
    backgrounds = {}
    dir_path = Path(directory)
    
    if not dir_path.exists():
        return backgrounds
    
    for filepath in dir_path.glob("*.json"):
        try:
            bg = load_background(str(filepath))
            backgrounds[bg.id] = bg
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
    
    return backgrounds
