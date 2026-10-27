"""Combat resolution system (D&D / NetHack inspired)."""
import random
from typing import Tuple, List
from .entities import Fighter, Player, Monster
from .items import Weapon


def resolve_attack(attacker: Fighter, defender: Fighter) -> List[str]:
    """Resolve an attack from attacker to defender and return narrative log messages."""
    messages = []
    
    # Calculate attack roll
    d20 = random.randint(1, 20)
    str_mod = (attacker.str_score - 10) // 2
    
    weapon: Weapon = getattr(attacker, "equipped_weapon", None)
    weapon_bonus = weapon.bonus if weapon else 0
    attack_total = d20 + str_mod + weapon_bonus
    
    # Target defense: base_ac + bonuses
    target_ac = getattr(defender, "ac", defender.base_ac)
    
    is_player_attacker = isinstance(attacker, Player)
    atk_name = "You" if is_player_attacker else f"The {attacker.name}"
    def_name = "you" if isinstance(defender, Player) else f"the {defender.name}"
    
    # Check hit
    is_hit = False
    is_crit = (d20 == 20)
    
    if d20 == 1:
        is_hit = False
    elif is_crit or attack_total >= target_ac:
        is_hit = True

    if not is_hit:
        if is_player_attacker:
            messages.append(f"You miss {def_name}.")
        else:
            messages.append(f"{atk_name} misses you.")
        return messages

    # Roll damage
    if weapon:
        num_dice = weapon.damage_dice * (2 if is_crit else 1)
        dmg = sum(random.randint(1, weapon.damage_sides) for _ in range(num_dice)) + weapon.bonus
    else:
        num_dice = attacker.base_damage_dice * (2 if is_crit else 1)
        dmg = sum(random.randint(1, attacker.base_damage_sides) for _ in range(num_dice))
        
    dmg += str_mod
    dmg = max(1, dmg)
    
    actual_dmg = defender.take_damage(dmg)
    
    crit_text = " Critically!" if is_crit else ""
    if is_player_attacker:
        messages.append(f"You hit {def_name}{crit_text} for {actual_dmg} damage!")
    else:
        messages.append(f"{atk_name} hits {def_name}{crit_text} for {actual_dmg} damage!")
        
    if not defender.is_alive:
        if isinstance(defender, Player):
            messages.append("You have died!...")
        else:
            messages.append(f"The {defender.name} is destroyed!")
            if is_player_attacker:
                exp = getattr(defender, "exp_reward", 10)
                lvl_msgs = attacker.add_exp(exp)
                messages.append(f"You gain {exp} experience points.")
                messages.extend(lvl_msgs)

    return messages
