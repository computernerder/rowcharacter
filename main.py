from enum import Enum
from ROW_constants import *
from ROW_race import *

from dataclasses import dataclass, field
from typing import List, Dict, Callable





@dataclass
class Character:
    ''' 
    Represents a player character in the RPG system.
    Should be loaded with a player object as defined in charactertemplate.json
    
    '''    
    
    
    
    
    
    
    name: str = "Default Name"

    alive: bool = True 
    roll_method: RollType = RollType.STANDARD_ARRAY
    # attributes = {attr: 10 for attr in Attribute}  # Initialize all attributes to 10
    
    # attributes: Dict[Attribute, int] = field(default_factory=lambda: {attr: [10,attribute_modifier(10),0,0] for attr in Attribute})  # Initialize all attributes to 10

    languages: set[str] = field(default_factory=set)
    speed: int = 30  # Default speed




    # Path Related
    primary_path: Path | None = None
    secondary_path: List[Path] = field(default_factory=list)
    talent_points: int = 0
    spellcraft_points: int = 0
    casting_points: int = 0


    experience_points: int = 0
    level: int = 1
    advancement_points: int = 0  # This is equal to Intellect modifier on level up

    # Computed / derived stats (dataclass pattern):
    # These values are *derived* from the character’s core state (attributes, gear, bonuses, etc.)
    # and are therefore not provided by the caller in __init__ (init=False). They are calculated
    # in __post_init__ so every Character instance starts in a consistent, ready-to-use state.
    #
    # Declaring them as dataclass fields (instead of creating them dynamically in __post_init__)
    # makes them visible in repr/debugging, easier for the IDE/type-checker to reason about, and
    # prevents “forgot to set this attribute” bugs.
    
    skills: Dict[Skill, List[int]] = field(init=False)  # skill name -> [attr_mod, rank, misc]
    skill_totals: Dict[Skill, int] = field(init=False)   # skill name -> total bonus
    defense: List[int] = field(init=False)  # [base, agl_mod, armor, misc]
    defense_total: int = field(init=False)  # Default total defense (including modifiers)
    health_points: int = field(init=False)  # Default HP




    def __post_init__(self):
        
        # self.skills = {skill: [attribute_modifier(self.attributes[SKILL_ATTRIBUTE[skill]]), 0, 0] for skill in Skill}  # skill name -> bonus/rank (default 0)
        self.skills = {
            skill: [attribute_modifier(self.attributes[skill.attribute]), 0, 0] for skill in Skill
        }
        self.skill_totals = {skill: sum(self.skills[skill]) for skill in Skill}   # skill name -> total bonus
        self.defense = [DEFENSE_BASE, attribute_modifier(self.attributes[Attribute.AGILITY]), 0, 0]  # Base 9 + agl mod + armor + misc
        self.defense_total = sum(self.defense)  # Default total defense (including modifiers)
        self.health_points = 10 + attribute_modifier(self.attributes[Attribute.ENDURANCE])  # Default HP








    



class Player:
    def __init__(self, name, roll_method: RollType = RollType.STANDARD_ARRAY):
        self.name = name
        self.alive: bool = True
        self.roll_method: RollType = roll_method
        print(f"Player {self.name} has entered the arena!")


        # Attributes
        self.attributes = {attr.value: 10 for attr in Attribute}  # Initialize all attributes to 10

        # self.create_player()
        #Create Player
        self.languages = set()
        self.speed = 30  # Default speed
        self.defense = [DEFENSE_BASE, self.return_attribute_modifier(self.attributes[Attribute.AGILITY]), 0, 0]  # Base 9 + agl mod + armor + misc
        self.defense_total = sum(self.defense)  # Default total defense (including modifiers)
        self.health_points = 10 + self.return_attribute_modifier(self.attributes[Attribute.ENDURANCE])  # Default HP

        
 

        self.skills = {skill.value: 0 for skill in Skill}  # skill name -> bonus/rank (default 0)
        self.create_skills()  # Initialize skills with attribute modifiers

        # Select your Path
        self.select_path()



    def select_path(self):
        print(f'Select a Path for {self.name}:')
        print('Available Paths:')
        # Paths available to player are where both attributes are 15 or higher
        available_paths = []
        for path in Path:
            attrs = path.attributes
            if all(self.attributes[attr.value] >= 15 for attr in attrs):
                available_paths.append(path)
                print(f'  {path.value} (Attributes: {attrs[0].value}, {attrs[1].value})')

        if not available_paths:
            print('No available Paths based on your attributes.')
            return


        return


    def create_skills(self):
        self.skills = {}         # skill name -> [attr_mod, rank, misc]
        self.skill_totals = {}   # skill name -> total bonus

        for skill in Skill:
            attr_mod = self.return_attribute_modifier(
                self.attributes[skill.attribute.value]
            )
            self.skills[skill.value] = [attr_mod, 0, 0]
            self.skill_totals[skill.value] = sum(self.skills[skill.value])

        for skill_name in self.skills.keys():
                print(f'Skill: {skill_name}, Total Bonus: {self.skill_totals[skill_name]}')
        print(self.get_skill_total(Skill.ATHLETICS))
        self.add_rank_to_skill(Skill.ATHLETICS, 2)
        print(self.get_skill_total(Skill.ATHLETICS))


    def add_rank_to_skill(self, skill_name: Skill, ranks: int) -> int:
        self.skills[skill_name.value][1] += ranks
        self.skill_totals[skill_name.value] = sum(self.skills[skill_name.value])
        return self.skill_totals[skill_name.value]
    

    def get_skill_total(self, skill_name: Skill) -> int:
        return self.skill_totals[skill_name.value]


    def set_speed(self, new_speed: int) -> int:
        self.speed = new_speed
        return self.speed
    

    def get_defense_total(self) -> int:
        self.defense_total = sum(self.defense)
        return self.defense_total
    
    def update_defense_misc(self, misc_bonus: int) -> int:
        self.defense[3] = misc_bonus  #Update misc bonus
        return self.get_defense_total()  #recalculate total defense and return it

    def standard_array(self) -> list:
        # Rulebook array (7 numbers); choose any 6 without reuse.
        return [15, 14, 13, 12, 11, 10, 8]
    
    def roll_for_attributes(self) -> list:
        import random


        attributes = []
        for _ in range(6):
            rolls = [random.randint(1, 6) for _ in range(4)]    # Roll 4d6
            rolls.remove(min(rolls))                            # Drop the lowest roll.
            attributes.append(sum(rolls))                       # Sum the remaining three rolls.
            attributes.sort(reverse=True)                       # Return sorted.
        return attributes
    
    def point_buy(self) -> list[int]:
        """
        Implements point buy system for attribute generation.
        Returns a list of 6 attribute values.

        Uses the following cost table:
        8:0, 9:1, 10:2, 11:3, 12:4, 13:5, 14:7, 15:9, 16:11
        """
        cost_table = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9, 16: 11}
        points = 30
        attributes = [8, 8, 8, 8, 8, 8]  # Start with all attributes at minimum value.

        def total_cost(vals: list[int]) -> int:
            return sum(cost_table[v] for v in vals)

        print(f"You have {points} points to spend on attributes (8-16). Type 'q' to finish early.")
        while True:
            spent = total_cost(attributes)
            remaining = points - spent

            print(f"Current attributes: {attributes} | Spent: {spent} | Remaining: {remaining}")

            if remaining == 0:
                break

            idx_raw = input("Enter attribute index (0-5) to increase, or 'q': ").strip().lower()
            if idx_raw in ("q", "quit", "done", "exit"):
                break

            try:
                index = int(idx_raw)
            except ValueError:
                print("Invalid input. Please enter a number between 0 and 5, or 'q'.")
                continue

            if not (0 <= index < 6):
                print("Invalid index. Please enter a number between 0 and 5.")
                continue

            if attributes[index] >= 16:
                print("Attribute is already at maximum value of 16.")
                continue

            # Try increasing by 1 and check if it fits within the budget.
            candidate = attributes[:]
            candidate[index] += 1
            if total_cost(candidate) <= points:
                attributes = candidate
            else:
                print("Not enough points remaining for that increase.")

        return sorted(attributes, reverse=True)









    def create_player(self):
        # Does the player have attributes?
        print(f'Creating player {self.name}')
        
        if self.roll_method is None:
            print(f'How did you want to determin your attributes? (roll / point buy / standard array)')
            input_method = input('> ')
        else:
            input_method = self.roll_method.value

        print (f'Using attribute generation method: {input_method}')
        # Create attribute list, as they are not tied to a attribute yet
        temp_values = []

        if input_method == 'roll' or input_method == '0':
            print('Rolling for attributes...')
            temp_values = self.roll_for_attributes()
        elif input_method == 'point_buy' or input_method == '1':
            print('Using point buy system...')
            temp_values = self.point_buy()
        elif input_method == 'standard_array' or input_method == '2':
            print('Using standard array...')
            temp_values = self.standard_array()
            
        else:
            print('Invalid input method. Using default attributes.')
            temp_values = self.standard_array()
        
        print(f'Attribute values assigned: {temp_values}')

        print(f'Now, assign these values to your attributes: Might, Agility, Endurance, Wisdom, Intellect, Charisma:')
        # Assign attributes
        self.assign_attributes(temp_values)

        # Show Attributes with attribute mods
        self.show_attributes()



    def show_attributes(self):
        print(f'Attributes for {self.name}:')
        for key, value in self.attributes.items():
            mod = self.return_attribute_modifier(value)
            mod_str = f'+{mod}' if mod >= 0 else str(mod)
            print(f'  {key}: {value} ({mod_str})')

    def assign_attributes(self, values: list[int]):
        attribute_keys = list(self.attributes.keys())
        for key in attribute_keys:
            while True:
                print(f'Available values: {values}')
                val_raw = input(f'Enter value for {key}: ').strip()
                try:
                    val = int(val_raw)
                except ValueError:
                    print('Invalid input. Please enter a number from the available values.')
                    continue

                if val not in values:
                    print('Value not in available values. Please choose again.')
                    continue

                self.attributes[key] = val
                values.remove(val)
                break
        print(f'Final attributes for {self.name}: {self.attributes}')

    def return_attribute_modifier(self, value: int) -> int:
        '''
        Returns the attribute modifier for a given attribute value.
        Args:
            value (int): The attribute value (1-30).
        Returns:
            int: The attribute modifier.

        calculation is done as follows:
        Value minus 10, divided by 2, rounded down.
        '''
        return (value - 10) // 2
    


def main():

    p1 = Player("Josh",roll_method=RollType.STANDARD_ARRAY)
   
 
if __name__ == "__main__":
    main()