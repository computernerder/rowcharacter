#Constants for Relm of Warriors game

from enum import Enum


DEFENSE_BASE = 9


    


class Skill(str, Enum):
    ACROBATICS = "Acrobatics"
    ANIMAL_HANDLING = "Animal Handling"
    APPRAISAL = "Appraisal"
    ARCANA = "Arcana"
    ATHLETICS = "Athletics"
    CRAFTING = "Crafting"
    DECEPTION = "Desception"
    DIPLOMACY = "Diplomacy"
    HISTORY = "History"
    INSIGHT = "Insight"
    INTIMIDATION = "Intimidation"
    INVESTIGATION = "Investigation"
    MEDICINE = "Medicine"
    NATURE = "Nature"
    PERCEPTION = "Perception"
    PERFORMANCE = "Performance"
    PERSUASION = "Persuasion"
    SLEIGHT_OF_HAND = "Slight of Hand"
    STEALTH = "Stealth"
    STREETWISE = "Streetwise"
    SURVIVAL = "Survival"

class Attribute(str, Enum):
    MIGHT = "Might"
    AGILITY = "Agility"
    ENDURANCE = "Endurance"
    WISDOM = "Wisdom"
    INTELLECT = "Intellect"
    CHARISMA = "Charisma"

class Path(Enum):
    DEFENSE = "Defense"
    DIVINE = "Divine"
    EXPLOITATION = "Exploitation"
    MARTIAL = "Martial"
    MYSTIC = "Mystic"
    POWER = "Power"
    SURVIVAL = "Survival"

    @property
    def attributes(self) -> list[Attribute]:
        return {
            Path.DEFENSE: [Attribute.ENDURANCE, Attribute.WISDOM],
            Path.DIVINE: [Attribute.WISDOM, Attribute.CHARISMA],
            Path.EXPLOITATION: [Attribute.AGILITY, Attribute.INTELLECT],
            Path.MARTIAL: [Attribute.MIGHT, Attribute.WISDOM],
            Path.MYSTIC: [Attribute.INTELLECT, Attribute.WISDOM],
            Path.POWER: [Attribute.MIGHT, Attribute.ENDURANCE],
            Path.SURVIVAL: [Attribute.WISDOM, Attribute.AGILITY],
        }[self]

class Race(str, Enum):
    HUMAN = "human"
    ELF = "elf"
    DWARF = "dwarf"
    HALFFOLK = "halffolk"
    GOBLIN = "goblin"
    SIMARI = "simari"
    VELKARR = "velkarr"
    TAURIN = "taurin"

class Profession(str, Enum):
    WARRIOR = "warrior"
    CRIMINAL = "criminal"
    PRIEST = "priest"
    BlackSMITH = "blacksmith"
    LEATHERWORKER = "leatherworker"
    ARTISAN = "artisan"
    WARDENOFTHEWILD = "warden of the wild"
    SCHOLAR = "scholar"
    FREEAGENT = "free agent"

class Role(str, Enum):
    STRIKER = "striker"
    DEFENDER = "defender"
    HEALER = "healer"
    SPECIALIST = "specialist"
    INFLUENCER = "influencer"

class Talent(str, Enum):
    ALERTNESS = "Alertness"
    ARCHERYFOCUS = "Archery Focus"
    ARMORTRAINING = "Armor Training"
    ATHLETE = "Athlete"
    BOOKSMART = "Booksmart"
    COMMONSENSE = "Commonsense"
    DEFENSIVETRAINING = "Defensive Training"
    DUALWIELDING = "Dual Wielding"
    EXPERIENCED = "Experienced"
    FIGHTINGSTYLE = "Fighting Style"
    LUCKY = "Lucky"
    MOBILE = "Mobile"
    NATURALLEADER = "Natural Leader"
    OBSERVANT = "Observant"
    PERSUASIVE = "Persuasive"
    QUICKLEARNER = "Quick Learner"
    QUICKNESS = "Quickness"
    RESILIENT = "Resilient"
    RESOURCEFUL = "Resourceful"
    SKILLFOCUS = "Skill Focus"
    TINKERER = "Tinkerer"
    TOUGHNESS = "Toughness"
    WEAPONMASTERY = "Weapon Mastery"




SKILL_ATTRIBUTE = {
    Skill.ACROBATICS: Attribute.AGILITY,
    Skill.SLEIGHT_OF_HAND: Attribute.AGILITY,
    Skill.STEALTH: Attribute.AGILITY,

    Skill.ATHLETICS: Attribute.MIGHT,

    Skill.ARCANA: Attribute.INTELLECT,
    Skill.HISTORY: Attribute.INTELLECT,
    Skill.INVESTIGATION: Attribute.INTELLECT,
    Skill.NATURE: Attribute.INTELLECT,
    Skill.APPRAISAL: Attribute.INTELLECT,
    Skill.CRAFTING: Attribute.INTELLECT,

    Skill.INSIGHT: Attribute.WISDOM,
    Skill.MEDICINE: Attribute.WISDOM,
    Skill.PERCEPTION: Attribute.WISDOM,
    Skill.SURVIVAL: Attribute.WISDOM,
    Skill.ANIMAL_HANDLING: Attribute.WISDOM,

    Skill.DECEPTION: Attribute.CHARISMA,
    Skill.DIPLOMACY: Attribute.CHARISMA,
    Skill.INTIMIDATION: Attribute.CHARISMA,
    Skill.PERFORMANCE: Attribute.CHARISMA,
    Skill.PERSUASION: Attribute.CHARISMA,
    Skill.STREETWISE: Attribute.CHARISMA,
}

class RollType(str, Enum):
    ROLL = "roll"
    POINT_BUY = "point_buy"
    STANDARD_ARRAY = "standard_array"