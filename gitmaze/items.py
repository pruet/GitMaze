"""Item system for GitMaze (NetHack-inspired)."""
from dataclasses import dataclass
from typing import Optional, Callable


@dataclass
class Item:
    name: str
    char: str
    color: str  # ANSI color or name
    category: str  # 'weapon', 'armor', 'potion', 'scroll', 'food', 'gold'
    value: int = 0
    weight: int = 1
    description: str = ""

    def use(self, user, engine) -> str:
        """Default use method."""
        return f"You can't figure out how to use the {self.name}."


@dataclass
class Weapon(Item):
    damage_dice: int = 1  # e.g., 1d6
    damage_sides: int = 6
    bonus: int = 0
    category: str = "weapon"

    def __post_init__(self):
        self.char = ")"

    def describe(self) -> str:
        bonus_str = f"+{self.bonus}" if self.bonus > 0 else (f"{self.bonus}" if self.bonus < 0 else "")
        return f"{self.name} {bonus_str} ({self.damage_dice}d{self.damage_sides})"


@dataclass
class Armor(Item):
    ac_bonus: int = 2  # NetHack: lower AC is better, but defense rating can be positive
    slot: str = "body"  # 'body', 'shield', 'helmet'
    category: str = "armor"

    def __post_init__(self):
        self.char = "["

    def describe(self) -> str:
        return f"{self.name} [AC +{self.ac_bonus}]"


@dataclass
class Potion(Item):
    effect: str = "heal"
    power: int = 15
    category: str = "potion"

    def __post_init__(self):
        self.char = "!"

    def use(self, user, engine) -> str:
        if self.effect == "heal":
            recovered = min(user.max_hp - user.hp, self.power)
            user.hp += recovered
            return f"You drink the {self.name}. You feel much better! (+{recovered} HP)"
        elif self.effect == "extra_heal":
            user.max_hp += 3
            user.hp = user.max_hp
            return f"You drink the {self.name}. Vitality surges through your veins! (Full HP, Max HP +3)"
        elif self.effect == "speed":
            user.speed_boost = 15
            return f"You drink the {self.name}. Your movements blur with speed!"
        return f"You drink the {self.name}. It tastes strange."


@dataclass
class Scroll(Item):
    effect: str = "teleport"
    category: str = "scroll"

    def __post_init__(self):
        self.char = "?"

    def use(self, user, engine) -> str:
        if self.effect == "teleport":
            engine.teleport_entity(user)
            return f"You read the {self.name}. The world spins around you as you teleport!"
        elif self.effect == "magic_mapping":
            engine.reveal_full_map()
            return f"You read the {self.name}. A vision of the entire dungeon fills your mind!"
        elif self.effect == "identify":
            return f"You read the {self.name}. You feel more knowledgeable."
        return f"You read the {self.name}. It crumbles into dust."


@dataclass
class Food(Item):
    nutrition: int = 400
    category: str = "food"

    def __post_init__(self):
        self.char = "%"

    def use(self, user, engine) -> str:
        user.hunger = min(user.max_hunger, user.hunger + self.nutrition)
        return f"You eat the {self.name}. That was delicious!"


@dataclass
class Gold(Item):
    amount: int = 1
    category: str = "gold"

    def __post_init__(self):
        self.char = "$"
        self.name = f"{self.amount} gold pieces"


def create_item_from_char(char: str, depth: int = 1) -> Optional[Item]:
    """Factory to create standard items from map character."""
    import random
    if char == "$":
        amount = random.randint(5 * depth, 25 * depth)
        return Gold(name=f"{amount} gold pieces", char="$", color="yellow", amount=amount, category="gold")
    elif char == "!":
        potions = [
            Potion(name="potion of healing", char="!", color="magenta", effect="heal", power=15, value=50),
            Potion(name="potion of extra healing", char="!", color="bright_magenta", effect="extra_heal", power=30, value=100),
            Potion(name="potion of speed", char="!", color="cyan", effect="speed", power=15, value=75),
        ]
        return random.choice(potions)
    elif char == "?":
        scrolls = [
            Scroll(name="scroll of teleportation", char="?", color="white", effect="teleport", value=60),
            Scroll(name="scroll of magic mapping", char="?", color="bright_cyan", effect="magic_mapping", value=80),
        ]
        return random.choice(scrolls)
    elif char in (")", "/"):
        weapons = [
            Weapon(name="dagger", char=")", color="white", damage_dice=1, damage_sides=4, bonus=1, value=15),
            Weapon(name="short sword", char=")", color="white", damage_dice=1, damage_sides=6, bonus=0, value=30),
            Weapon(name="long sword", char=")", color="bright_white", damage_dice=1, damage_sides=8, bonus=1, value=60),
        ]
        return random.choice(weapons)
    elif char == "[":
        armors = [
            Armor(name="leather armor", char="[", color="yellow", ac_bonus=2, value=30),
            Armor(name="chain mail", char="[", color="white", ac_bonus=4, value=80),
            Armor(name="plate mail", char="[", color="bright_white", ac_bonus=6, value=200),
        ]
        return random.choice(armors)
    elif char == "%":
        foods = [
            Food(name="food ration", char="%", color="green", nutrition=500, value=10),
            Food(name="apple", char="%", color="red", nutrition=150, value=2),
            Food(name="loaf of bread", char="%", color="yellow", nutrition=350, value=5),
        ]
        return random.choice(foods)
    return None
