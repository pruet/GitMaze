"""Main entrypoint and interactive game loop for GitMaze."""
import os
import sys
import argparse
from .engine import GameEngine
from .ui import TerminalUI, get_key, colorize
from .validator import MapValidator


def run_game(levels_dir: str = "levels", start_level: str = "level_01"):
    engine = GameEngine(levels_dir=levels_dir, start_level_id=start_level)
    ui = TerminalUI(engine)

    # Key to direction mapping
    direction_map = {
        # Arrows
        "UP": (0, -1),
        "DOWN": (0, 1),
        "LEFT": (-1, 0),
        "RIGHT": (1, 0),
        "UP_LEFT": (-1, -1),
        "UP_RIGHT": (1, -1),
        "DOWN_LEFT": (-1, 1),
        "DOWN_RIGHT": (1, 1),
        # Vi keys
        "k": (0, -1),
        "j": (0, 1),
        "h": (-1, 0),
        "l": (1, 0),
        "y": (-1, -1),
        "u": (1, -1),
        "b": (-1, 1),
        "n": (1, 1),
        # Numpad
        "8": (0, -1),
        "2": (0, 1),
        "4": (-1, 0),
        "6": (1, 0),
        "7": (-1, -1),
        "9": (1, -1),
        "1": (-1, 1),
        "3": (1, 1),
    }

    try:
        while not engine.game_over:
            ui.render()
            key = get_key()

            if not key:
                continue

            # Movement or attack
            if key in direction_map:
                dx, dy = direction_map[key]
                engine.handle_move_or_attack(dx, dy)
            elif key in (",", "g"):
                engine.pickup_item()
            elif key == "i":
                idx = ui.show_inventory_menu("Select item to inspect/use:")
                if idx is not None:
                    engine.use_item(idx)
            elif key == "d":
                idx = ui.show_inventory_menu("Select item to drop:")
                if idx is not None:
                    engine.drop_item(idx)
            elif key == "e":
                idx = ui.show_inventory_menu("Select food to eat:")
                if idx is not None:
                    engine.use_item(idx)
            elif key == "q":
                idx = ui.show_inventory_menu("Select potion to quaff:")
                if idx is not None:
                    engine.use_item(idx)
            elif key == "r":
                idx = ui.show_inventory_menu("Select scroll to read:")
                if idx is not None:
                    engine.use_item(idx)
            elif key in ("w", "W"):
                idx = ui.show_inventory_menu("Select weapon/armor to equip/unwield:")
                if idx is not None:
                    engine.use_item(idx)
            elif key == ">":
                engine.descend_stairs()
            elif key == "<":
                engine.ascend_stairs()
            elif key in (".", "s", "5"):
                engine.wait_turn()
            elif key == "?":
                ui.show_help_menu()
            elif key == "M":
                ui.show_git_info_menu()
            elif key in ("Q", "\x03"):  # Q or Ctrl+C
                ui.clear_screen()
                print("Do you really want to quit GitMaze? (y/n)")
                if get_key().lower() == "y":
                    print("Goodbye, brave adventurer!")
                    break

        # End game screen
        ui.render()
        if engine.won:
            print(colorize("\n\n🏆 CONGRATULATIONS! You conquered the GitMaze and ascended! 🏆", "bright_yellow", bold=True))
            print(f"Final Score: {engine.player.score} | Turns: {engine.turn} | Gold: {engine.player.gold}")
        elif engine.game_over:
            print(colorize("\n\n💀 REST IN PEACE... You perished in the depths of GitMaze. 💀", "bright_red", bold=True))
            print(f"Final Score: {engine.player.score} | Turns: {engine.turn} | Gold: {engine.player.gold}")
            print("Want a better chance next time? Propose a map tweak via a Git Pull Request!")
    except KeyboardInterrupt:
        print("\nGame aborted.")


def main():
    parser = argparse.ArgumentParser(description="GitMaze - A NetHack-inspired Roguelike powered by Git maps.")
    parser.add_argument("--gui", "-g", action="store_true", help="Launch the GUI graphical frontend")
    parser.add_argument("--editor", "-e", action="store_true", help="Launch the interactive Map Editor")
    parser.add_argument("--level", "-l", default="level_01", help="Start level ID (default: level_01)")
    parser.add_argument("--levels-dir", "-d", default="levels", help="Directory containing map files")
    parser.add_argument("--validate", "-v", action="store_true", help="Validate all maps in the levels directory and exit")
    args = parser.parse_args()

    if args.editor:
        from .editor import start_editor
        start_editor()
        return

    if args.gui:
        from .gui import start_gui
        start_gui(levels_dir=args.levels_dir, start_level=args.level)
        return

    if args.validate:
        print(f"Validating maps in '{args.levels_dir}'...")
        total_errors = 0
        total_warnings = 0
        if not os.path.exists(args.levels_dir):
            print(f"Directory not found: {args.levels_dir}")
            sys.exit(1)

        map_files = [f for f in os.listdir(args.levels_dir) if f.endswith(".map") or f.endswith(".txt")]
        if not map_files:
            print(f"No map files found in {args.levels_dir}")
            sys.exit(1)

        for mf in sorted(map_files):
            fpath = os.path.join(args.levels_dir, mf)
            issues = MapValidator.validate_file(fpath)
            if not issues:
                print(f"  [PASS] {mf} : OK")
            else:
                for issue in issues:
                    if issue.severity == "ERROR":
                        total_errors += 1
                        print(f"  [FAIL] {issue}")
                    else:
                        total_warnings += 1
                        print(f"  [WARN] {issue}")

        print(f"\nValidation finished: {len(map_files)} maps checked. {total_errors} errors, {total_warnings} warnings.")
        sys.exit(1 if total_errors > 0 else 0)

    run_game(levels_dir=args.levels_dir, start_level=args.level)


if __name__ == "__main__":
    main()
