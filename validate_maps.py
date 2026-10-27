#!/usr/bin/env python3
"""Map validator CLI for GitMaze - useful for pre-commit hooks and GitHub Actions CI."""
import sys
import os
from gitmaze.validator import MapValidator


def validate_all(levels_dir: str = "levels") -> int:
    if not os.path.isdir(levels_dir):
        print(f"Error: Directory '{levels_dir}' does not exist.")
        return 1

    map_files = [f for f in os.listdir(levels_dir) if f.endswith(".map") or f.endswith(".txt")]
    if not map_files:
        print(f"Warning: No map files found in '{levels_dir}'.")
        return 0

    print("=================================================================")
    print("                GitMaze Map Validator (CI / Pre-commit)          ")
    print("=================================================================")
    
    total_errors = 0
    total_warnings = 0

    for mf in sorted(map_files):
        path = os.path.join(levels_dir, mf)
        issues = MapValidator.validate_file(path)
        errors = [i for i in issues if i.severity == "ERROR"]
        warnings = [i for i in issues if i.severity == "WARNING"]

        if not issues:
            print(f"  [PASS] {mf}")
        else:
            status = "[FAIL]" if errors else "[WARN]"
            print(f"  {status} {mf}")
            for err in errors:
                print(f"         [X] {err.message}")
            for warn in warnings:
                print(f"         [!] {warn.message}")
            
        total_errors += len(errors)
        total_warnings += len(warnings)

    print("-----------------------------------------------------------------")
    print(f"Summary: {len(map_files)} files checked | {total_errors} errors | {total_warnings} warnings")
    if total_errors > 0:
        print("RESULT: FAILED. Please resolve errors before merging PR.")
        return 1
    else:
        print("RESULT: PASSED. All maps meet GitMaze standards!")
        return 0


if __name__ == "__main__":
    dir_to_check = sys.argv[1] if len(sys.argv) > 1 else "levels"
    sys.exit(validate_all(dir_to_check))
