"""
Character Builder - Orchestrates the character creation process.

This class manages the step-by-step creation of a character:
1. Choose race
2. Choose ancestry
3. Choose profession (and duty if applicable)
4. Set ability scores
5. Choose path
6. Choose background

Each step applies its effects to the character and tracks what choices
still need to be made.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum, auto

from template_model import (
    CharacterTemplate, 
    AbilityScore, 
    SkillEntry,
    Feature as TemplateFeature,
)
from ROW_constants import Attribute, Skill

from core import (
    Race, Ancestry, Profession, Duty, Path, Background,
    PersonalityEntry,
    load_all_races, load_all_ancestries, load_all_professions,
    load_all_paths, load_all_backgrounds,
    get_ancestries_for_race,
)


class BuilderStep(Enum):
    """The current step in character creation."""
    ABILITY_SCORES = auto()
    RACE = auto()
    ANCESTRY = auto()
    PROFESSION = auto()
    PATH = auto()
    BACKGROUND = auto()
    COMPLETE = auto()


@dataclass
class PendingChoice:
    """Represents a choice the user still needs to make."""
    choice_type: str  # "skill", "language", "tool", "ability_bonus", etc.
    count: int  # How many to choose
    options: List[str]  # Available options
    source: str  # Where this choice came from (e.g., "Human Race", "Warrior Profession")


@dataclass 
class CharacterBuilder:
    """
    Manages the character creation process.
    
    Usage:
        builder = CharacterBuilder()
        builder.load_game_data("data")
        
        # Set ability scores
        builder.set_ability_scores({"Might": 15, "Agility": 14, ...})
        
        # Choose race and ancestry
        builder.set_race("elf")
        builder.set_ancestry("sylari")
        
        # Choose profession
        builder.set_profession("warrior", duty_id="fighter")
        builder.resolve_choice("skill", ["Athletics", "Perception"])
        
        # Choose path
        builder.set_path("defense")
        
        # Choose background
        builder.set_background("soldier")
        
        # Get the finished character
        character = builder.get_character()
    """
    
    character: CharacterTemplate = field(default_factory=CharacterTemplate)
    current_step: BuilderStep = BuilderStep.ABILITY_SCORES
    pending_choices: List[PendingChoice] = field(default_factory=list)
    
    # Loaded game data
    races: Dict[str, Race] = field(default_factory=dict)
    ancestries: Dict[str, Ancestry] = field(default_factory=dict)
    professions: Dict[str, Profession] = field(default_factory=dict)
    paths: Dict[str, Path] = field(default_factory=dict)
    backgrounds: Dict[str, Background] = field(default_factory=dict)
    
    # Track what's been chosen
    chosen_race: Optional[Race] = None
    chosen_ancestry: Optional[Ancestry] = None
    chosen_profession: Optional[Profession] = None
    chosen_duty: Optional[Duty] = None
    chosen_path: Optional[Path] = None
    chosen_background: Optional[Background] = None

    def __post_init__(self):
        """Initialize the character with default ability scores and skills."""
        self._init_ability_scores()
        self._init_skills()

    def _init_ability_scores(self):
        """Initialize all ability scores to base 10."""
        for attr in Attribute:
            self.character.ability_scores[attr.value] = AbilityScore(
                total=10, roll=10, mod=0, saving_throw=0, race=0, misc=0
            )

    def _init_skills(self):
        """Initialize all skills."""
        for skill in Skill:
            self.character.skills[skill.value] = SkillEntry(
                trained=False, mod=0, rank=0, misc=0, total=0
            )

    def load_game_data(self, data_dir: str = "data") -> None:
        """Load all game data from JSON files."""
        self.races = load_all_races(f"{data_dir}/races")
        self.ancestries = load_all_ancestries(f"{data_dir}/ancestries")
        self.professions = load_all_professions(f"{data_dir}/professions")
        self.paths = load_all_paths(f"{data_dir}/paths")
        self.backgrounds = load_all_backgrounds(f"{data_dir}/backgrounds")

    # -------------------------------------------------------------------------
    # Step 1: Ability Scores
    # -------------------------------------------------------------------------

    def set_ability_scores(self, scores: Dict[str, int]) -> None:
        """
        Set the character's base ability scores.
        
        Args:
            scores: Dict mapping ability name to score value
                    e.g., {"Might": 15, "Agility": 14, "Endurance": 13, ...}
        """
        for name, value in scores.items():
            if name in self.character.ability_scores:
                score = self.character.ability_scores[name]
                # Treat input as the "natural" (base) score.
                # If race/ancestry/profession already applied earlier, preserve those modifiers.
                score.roll = value
                score.total = score.roll + score.race + score.misc
                score.mod = (score.total - 10) // 2
                score.saving_throw = score.mod
        
        self.current_step = BuilderStep.RACE

    def get_available_races(self) -> List[Race]:
        """Get list of available races."""
        return list(self.races.values())

    # -------------------------------------------------------------------------
    # Step 2: Race
    # -------------------------------------------------------------------------

    def set_race(self, race_id: str) -> None:
        """
        Choose a race for the character.
        
        Args:
            race_id: The ID of the race (e.g., "elf", "human")
        """
        if race_id not in self.races:
            raise ValueError(f"Unknown race: {race_id}")
        
        race = self.races[race_id]
        self.chosen_race = race
        
        # Apply race traits
        race.apply(self.character)
        
        # Store race name on character
        self.character.race = race.name
        
        # Add pending choices if race has them
        if race.skill_choices:
            options = race.skill_choices.get("options", [])
            if options == "any":
                options = [s.value for s in Skill]
            self.pending_choices.append(PendingChoice(
                choice_type="skill",
                count=race.skill_choices.get("count", 1),
                options=options,
                source=f"{race.name} Race",
            ))
        
        if race.bonus_language_choices > 0:
            self.pending_choices.append(PendingChoice(
                choice_type="language",
                count=race.bonus_language_choices,
                options=self._get_available_languages(),
                source=f"{race.name} Race",
            ))
        
        if race.flexible_ability_adjustment:
            adj_type = race.flexible_ability_adjustment.get("type", "")
            
            if adj_type == "human_core":
                # Human special: choose +1 to one OR +2/-1 split
                # First, choose the mode
                self.pending_choices.append(PendingChoice(
                    choice_type="human_ability_mode",
                    count=1,
                    options=["+1 to one ability", "+2 to one ability and -1 to another"],
                    source=f"{race.name} Race - Core Ability Adjustment",
                ))
            else:
                # Generic flexible adjustment
                all_abilities = [a.value for a in Attribute]
                self.pending_choices.append(PendingChoice(
                    choice_type="ability_bonus",
                    count=1,
                    options=all_abilities,
                    source=f"{race.name} Race - Ability Adjustment",
                ))
        
        self.current_step = BuilderStep.ANCESTRY

    def get_available_ancestries(self) -> List[Ancestry]:
        """Get ancestries available for the chosen race."""
        if not self.chosen_race:
            return []
        return get_ancestries_for_race(self.ancestries, self.chosen_race.id)

    # -------------------------------------------------------------------------
    # Step 3: Ancestry
    # -------------------------------------------------------------------------

    def set_ancestry(self, ancestry_id: str) -> None:
        """
        Choose an ancestry for the character.
        
        Args:
            ancestry_id: The ID of the ancestry (e.g., "sylari", "velari")
        """
        if ancestry_id not in self.ancestries:
            raise ValueError(f"Unknown ancestry: {ancestry_id}")
        
        ancestry = self.ancestries[ancestry_id]
        
        # Verify ancestry belongs to chosen race
        if self.chosen_race and ancestry.race_id != self.chosen_race.id:
            raise ValueError(f"Ancestry {ancestry.name} is not valid for race {self.chosen_race.name}")
        
        self.chosen_ancestry = ancestry
        
        # Apply ancestry traits
        ancestry.apply(self.character)
        
        # Store ancestry name on character
        self.character.ancestry = ancestry.name
        
        # Add pending language choices if ancestry has them
        if ancestry.language_choices:
            self.pending_choices.append(PendingChoice(
                choice_type="language",
                count=ancestry.language_choices.get("count", 1),
                options=ancestry.language_choices.get("options", []),
                source=f"{ancestry.name} Ancestry",
            ))
        
        self.current_step = BuilderStep.PROFESSION

    def get_available_professions(self) -> List[Profession]:
        """Get list of available professions."""
        return list(self.professions.values())

    # -------------------------------------------------------------------------
    # Step 4: Profession
    # -------------------------------------------------------------------------

    def set_profession(self, profession_id: str, duty_id: str = None) -> None:
        """
        Choose a profession for the character.
        
        Args:
            profession_id: The ID of the profession (e.g., "warrior", "scholar")
            duty_id: Optional duty ID for professions with duties (e.g., "fighter", "ranger")
        """
        if profession_id not in self.professions:
            raise ValueError(f"Unknown profession: {profession_id}")
        
        profession = self.professions[profession_id]
        self.chosen_profession = profession
        
        # Handle duty selection
        duty = None
        if profession.duties:
            if duty_id:
                duty = next((d for d in profession.duties if d.id == duty_id), None)
                if not duty:
                    raise ValueError(f"Unknown duty: {duty_id}")
            else:
                # Duty required but not provided
                raise ValueError(f"Profession {profession.name} requires a duty choice: {[d.id for d in profession.duties]}")
        
        self.chosen_duty = duty
        
        # Apply profession (without skills/tools - those are choices)
        profession.apply(self.character, chosen_duty=duty)
        
        # Store profession name on character
        self.character.profession = profession.name
        
        # Add pending skill choices
        if profession.skill_choices:
            self.pending_choices.append(PendingChoice(
                choice_type="skill",
                count=profession.skill_choices.get("count", 1),
                options=profession.skill_choices.get("options", []),
                source=f"{profession.name} Profession",
            ))
        
        # Add pending tool choices
        if profession.tool_choices:
            self.pending_choices.append(PendingChoice(
                choice_type="tool",
                count=profession.tool_choices.get("count", 1),
                options=profession.tool_choices.get("options", []),
                source=f"{profession.name} Profession",
            ))
        
        # Add duty-specific choices
        if duty:
            if duty.skill_choices:
                self.pending_choices.append(PendingChoice(
                    choice_type="skill",
                    count=duty.skill_choices.get("count", 1),
                    options=duty.skill_choices.get("options", []),
                    source=f"{duty.name} Duty",
                ))
            if duty.tool_choices:
                self.pending_choices.append(PendingChoice(
                    choice_type="tool",
                    count=duty.tool_choices.get("count", 1),
                    options=duty.tool_choices.get("options", []),
                    source=f"{duty.name} Duty",
                ))
        
        self.current_step = BuilderStep.PATH

    def get_available_paths(self) -> List[Tuple[Path, bool]]:
        """
        Get available paths and whether prerequisites are met.
        
        Returns:
            List of (Path, meets_prerequisites) tuples
        """
        result = []
        for path in self.paths.values():
            meets = path.check_prerequisites(self.character.ability_scores, is_primary=True)
            result.append((path, meets))
        return result

    # -------------------------------------------------------------------------
    # Step 5: Path
    # -------------------------------------------------------------------------

    def set_path(self, path_id: str, ignore_prerequisites: bool = False) -> None:
        """
        Choose a primary path for the character.
        
        Args:
            path_id: The ID of the path (e.g., "defense", "mystic")
            ignore_prerequisites: If True, skip prerequisite check (for testing)
        """
        if path_id not in self.paths:
            raise ValueError(f"Unknown path: {path_id}")
        
        path = self.paths[path_id]
        
        # Check prerequisites
        if not ignore_prerequisites:
            if not path.check_prerequisites(self.character.ability_scores, is_primary=True):
                prereq = path.prerequisites
                raise ValueError(
                    f"Prerequisites not met for {path.name}: "
                    f"Need {prereq.primary_attribute} {prereq.primary_minimum}+ "
                    f"and one of {prereq.secondary_attributes} {prereq.secondary_minimum}+"
                )
        
        self.chosen_path = path
        
        # Apply path as primary
        path.apply(self.character, is_primary=True)
        
        # Store path name on character
        self.character.primary_path = path.name
        
        self.current_step = BuilderStep.BACKGROUND

    def get_available_backgrounds(self) -> List[Background]:
        """Get list of available backgrounds."""
        return list(self.backgrounds.values())

    # -------------------------------------------------------------------------
    # Step 6: Background
    # -------------------------------------------------------------------------

    def set_background(self, background_id: str) -> None:
        """
        Choose a background for the character.
        
        Args:
            background_id: The ID of the background (e.g., "devotee", "scholar")
        """
        if background_id not in self.backgrounds:
            raise ValueError(f"Unknown background: {background_id}")
        
        background = self.backgrounds[background_id]
        self.chosen_background = background
        
        # Apply background (without personality - that's a choice)
        background.apply(self.character)
        
        # Store background name on character
        self.character.background = background.name
        
        # Add pending language choices
        if background.languages_granted > 0:
            self.pending_choices.append(PendingChoice(
                choice_type="language",
                count=background.languages_granted,
                options=self._get_available_languages(),
                source=f"{background.name} Background",
            ))
        
        # Add pending personality choices
        if background.personality_tables:
            tables = background.personality_tables
            if tables.traits:
                self.pending_choices.append(PendingChoice(
                    choice_type="personality_trait",
                    count=1,
                    options=[f"{e.roll}: {e.text}" for e in tables.traits],
                    source=f"{background.name} Background",
                ))
            if tables.ideals:
                self.pending_choices.append(PendingChoice(
                    choice_type="personality_ideal",
                    count=1,
                    options=[f"{e.roll}: {e.text}" for e in tables.ideals],
                    source=f"{background.name} Background",
                ))
            if tables.bonds:
                self.pending_choices.append(PendingChoice(
                    choice_type="personality_bond",
                    count=1,
                    options=[f"{e.roll}: {e.text}" for e in tables.bonds],
                    source=f"{background.name} Background",
                ))
            if tables.flaws:
                self.pending_choices.append(PendingChoice(
                    choice_type="personality_flaw",
                    count=1,
                    options=[f"{e.roll}: {e.text}" for e in tables.flaws],
                    source=f"{background.name} Background",
                ))
        
        self.current_step = BuilderStep.COMPLETE

    # -------------------------------------------------------------------------
    # Resolve Pending Choices
    # -------------------------------------------------------------------------

    def get_pending_choices(self) -> List[PendingChoice]:
        """Get all pending choices that need to be resolved."""
        return self.pending_choices

    def resolve_choice(self, choice_type: str, selections: List[str], source: str = None) -> None:
        """
        Resolve a pending choice.
        
        Args:
            choice_type: Type of choice ("skill", "language", "tool", etc.)
            selections: List of selected options
            source: Optional source to match (if multiple choices of same type)
        """
        # Find the matching pending choice
        matching = [c for c in self.pending_choices 
                   if c.choice_type == choice_type and (source is None or c.source == source)]
        
        if not matching:
            raise ValueError(f"No pending choice of type '{choice_type}'")
        
        choice = matching[0]
        
        # Validate selection count
        if len(selections) != choice.count:
            raise ValueError(f"Expected {choice.count} selections, got {len(selections)}")
        
        # Validate selections are valid options
        for sel in selections:
            if sel not in choice.options:
                raise ValueError(f"Invalid selection '{sel}'. Options: {choice.options}")
        
        # Apply the selections
        if choice_type == "skill":
            for skill_name in selections:
                if skill_name in self.character.skills:
                    self.character.skills[skill_name].trained = True
                    if self.character.skills[skill_name].rank == 0:
                        self.character.skills[skill_name].rank = 1
        
        elif choice_type == "language":
            for lang in selections:
                if lang not in self.character.languages:
                    self.character.languages.append(lang)
        
        elif choice_type == "tool":
            for tool in selections:
                if tool not in self.character.proficiencies:
                    self.character.proficiencies.append(tool)
        
        elif choice_type == "ability_bonus":
            # Handle flexible ability adjustment - selection is an ability name
            for sel in selections:
                if sel in self.character.ability_scores:
                    self.character.ability_scores[sel].misc += 1
                    self.character.ability_scores[sel].total += 1
                    self._recalculate_modifier(sel)
        
        elif choice_type == "human_ability_mode":
            # Human chose their adjustment mode, now queue the actual choices
            all_abilities = [a.value for a in Attribute]
            
            if "+2" in selections[0]:
                # +2 to one, -1 to another
                self.pending_choices.append(PendingChoice(
                    choice_type="ability_bonus_plus2",
                    count=1,
                    options=all_abilities,
                    source="Human Race - +2 Bonus",
                ))
                self.pending_choices.append(PendingChoice(
                    choice_type="ability_penalty",
                    count=1,
                    options=all_abilities,
                    source="Human Race - -1 Penalty",
                ))
            else:
                # +1 to one ability
                self.pending_choices.append(PendingChoice(
                    choice_type="ability_bonus",
                    count=1,
                    options=all_abilities,
                    source="Human Race - +1 Bonus",
                ))
        
        elif choice_type == "ability_bonus_plus2":
            # +2 to selected ability
            for sel in selections:
                if sel in self.character.ability_scores:
                    self.character.ability_scores[sel].misc += 2
                    self.character.ability_scores[sel].total += 2
                    self._recalculate_modifier(sel)
        
        elif choice_type == "ability_penalty":
            # -1 to selected ability
            for sel in selections:
                if sel in self.character.ability_scores:
                    self.character.ability_scores[sel].misc -= 1
                    self.character.ability_scores[sel].total -= 1
                    self._recalculate_modifier(sel)
        
        elif choice_type.startswith("personality_"):
            # Handle personality choices
            if self.chosen_background and self.chosen_background.personality_tables:
                tables = self.chosen_background.personality_tables
                
                # Parse the selection - format is "N: text"
                sel = selections[0]
                roll_num = int(sel.split(":")[0])
                
                if choice_type == "personality_trait":
                    entry = next((e for e in tables.traits if e.roll == roll_num), None)
                    if entry:
                        self.character.personality.traits = entry.text
                        self.character.alignment.mod += entry.morality
                        self.character.reputation.mod += entry.reputation
                
                elif choice_type == "personality_ideal":
                    entry = next((e for e in tables.ideals if e.roll == roll_num), None)
                    if entry:
                        self.character.personality.ideal = entry.text
                        self.character.alignment.mod += entry.morality
                        self.character.reputation.mod += entry.reputation
                
                elif choice_type == "personality_bond":
                    entry = next((e for e in tables.bonds if e.roll == roll_num), None)
                    if entry:
                        self.character.personality.bond = entry.text
                        self.character.alignment.mod += entry.morality
                        self.character.reputation.mod += entry.reputation
                
                elif choice_type == "personality_flaw":
                    entry = next((e for e in tables.flaws if e.roll == roll_num), None)
                    if entry:
                        self.character.personality.flaw = entry.text
                        self.character.alignment.mod += entry.morality
                        self.character.reputation.mod += entry.reputation
        
        # Remove the resolved choice
        self.pending_choices.remove(choice)

    # -------------------------------------------------------------------------
    # Finalization
    # -------------------------------------------------------------------------

    def recalculate_all(self) -> None:
        """Recalculate all derived values."""
        # Recalculate ability modifiers
        for name, score in self.character.ability_scores.items():
            score.total = score.roll + score.race + score.misc
            score.mod = (score.total - 10) // 2
            score.saving_throw = score.mod

        # Recalculate profession-based HP once ability mods are known.
        if self.chosen_profession is not None:
            end_mod = self.character.ability_scores.get("Endurance").mod if "Endurance" in self.character.ability_scores else 0
            self.character.health.max = self.chosen_profession.base_hp + end_mod
            # Keep current HP within bounds
            if self.character.health.current > self.character.health.max:
                self.character.health.current = self.character.health.max
            elif self.character.health.current <= 0:
                self.character.health.current = self.character.health.max
        
        # Recalculate skill totals
        for skill_name, entry in self.character.skills.items():
            # Get the linked attribute
            skill_enum = next((s for s in Skill if s.value == skill_name), None)
            if skill_enum:
                attr = skill_enum.attribute
                if attr.value in self.character.ability_scores:
                    entry.mod = self.character.ability_scores[attr.value].mod
            entry.total = entry.mod + entry.rank + entry.misc
        
        # Recalculate attack modifiers
        if "Might" in self.character.ability_scores:
            self.character.attack_mods_melee.attr = self.character.ability_scores["Might"].mod
        if "Agility" in self.character.ability_scores:
            self.character.attack_mods_ranged.attr = self.character.ability_scores["Agility"].mod
        
        self.character.attack_mods_melee.total = (
            self.character.attack_mods_melee.attr + self.character.attack_mods_melee.misc
        )
        self.character.attack_mods_ranged.total = (
            self.character.attack_mods_ranged.attr + self.character.attack_mods_ranged.misc
        )
        
        # Recalculate defense
        if "Agility" in self.character.ability_scores:
            self.character.defense.agility = self.character.ability_scores["Agility"].mod
        shield = self.character.defense.shield if isinstance(self.character.defense.shield, int) else 0
        self.character.defense.total = (
            self.character.defense.base + 
            self.character.defense.agility + 
            shield + 
            self.character.defense.misc
        )
        
        # Recalculate initiative
        if "Agility" in self.character.ability_scores:
            self.character.initiative = self.character.ability_scores["Agility"].mod
        
        # Recalculate passive stats
        if "Perception" in self.character.skills:
            self.character.passive_perception.skill = self.character.skills["Perception"].total
            self.character.passive_perception.total = (
                self.character.passive_perception.base + 
                self.character.passive_perception.skill + 
                self.character.passive_perception.misc
            )
        
        if "Insight" in self.character.skills:
            self.character.passive_insight.skill = self.character.skills["Insight"].total
            self.character.passive_insight.total = (
                self.character.passive_insight.base + 
                self.character.passive_insight.skill + 
                self.character.passive_insight.misc
            )
        
        # Recalculate life points from Endurance
        if "Endurance" in self.character.ability_scores:
            end_total = self.character.ability_scores["Endurance"].total
            # Rulebook table rounds down odd scores (10-11 ->10, 12-13 ->12, etc.)
            self.character.life_points.max = max(1, (end_total // 2) * 2)
            self.character.life_points.current = self.character.life_points.max

    def _recalculate_modifier(self, ability_name: str) -> None:
        """Recalculate a single ability's modifier."""
        if ability_name in self.character.ability_scores:
            score = self.character.ability_scores[ability_name]
            score.total = score.roll + score.race + score.misc
            score.mod = (score.total - 10) // 2
            score.saving_throw = score.mod

    def _get_available_languages(self) -> List[str]:
        """Get a list of available languages to choose from."""
        # Common languages - could be loaded from data
        return [
            "Common", "Elvish", "Dwarvish", "Ancient Dwarvish", "Orcish", "Goblin", 
            "Halffolk", "Draconic", "Celestial", "Infernal", 
            "Sylvan", "Aquan", "Tauric", "Simarru", "Velkarran"
        ]

    def is_complete(self) -> bool:
        """Check if character creation is complete."""
        return (
            self.current_step == BuilderStep.COMPLETE and 
            len(self.pending_choices) == 0
        )

    def get_character(self) -> CharacterTemplate:
        """
        Get the finished character.
        
        Recalculates all derived values before returning.
        """
        self.recalculate_all()
        return self.character

    def get_summary(self) -> str:
        """Get a summary of the current character build."""
        lines = [
            f"Character: {self.character.character_name or '(unnamed)'}",
            f"Current Step: {self.current_step.name}",
            f"",
            f"Race: {self.chosen_race.name if self.chosen_race else '(not chosen)'}",
            f"Ancestry: {self.chosen_ancestry.name if self.chosen_ancestry else '(not chosen)'}",
            f"Profession: {self.chosen_profession.name if self.chosen_profession else '(not chosen)'}",
        ]
        if self.chosen_duty:
            lines.append(f"  Duty: {self.chosen_duty.name}")
        lines.extend([
            f"Path: {self.chosen_path.name if self.chosen_path else '(not chosen)'}",
            f"Background: {self.chosen_background.name if self.chosen_background else '(not chosen)'}",
            f"",
            f"Pending Choices: {len(self.pending_choices)}",
        ])
        for choice in self.pending_choices:
            lines.append(f"  - {choice.source}: Choose {choice.count} {choice.choice_type}(s)")
        
        return "\n".join(lines)