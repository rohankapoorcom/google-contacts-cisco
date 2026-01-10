#!/usr/bin/env python3
"""Verify test coverage and identify gaps.

This script analyzes coverage data and provides:
- Overall coverage percentage
- Per-module coverage breakdown
- Identification of uncovered critical modules
- List of files below coverage threshold
- Actionable recommendations

Usage:
    python scripts/verify-coverage.py
    python scripts/verify-coverage.py --threshold 80
    python scripts/verify-coverage.py --critical-only
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# ANSI color codes
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
BLUE = "\033[0;34m"
BOLD = "\033[1m"
NC = "\033[0m"  # No Color

# Critical modules that should have high coverage
CRITICAL_MODULES = [
    "google_contacts_cisco.services",
    "google_contacts_cisco.repositories",
    "google_contacts_cisco.models",
    "google_contacts_cisco.auth",
]

# Modules that require extra attention
HIGH_PRIORITY_MODULES = [
    "google_contacts_cisco.api",
    "google_contacts_cisco.schemas",
]


def load_coverage_data() -> Dict:
    """Load coverage data from coverage.json."""
    coverage_file = Path("coverage.json")

    if not coverage_file.exists():
        print(f"{RED}Error: coverage.json not found{NC}")
        print(f"{YELLOW}Run tests with coverage first:{NC}")
        print("  ./scripts/test.sh")
        print("  or")
        print("  uv run pytest --cov=google_contacts_cisco --cov-report=json")
        sys.exit(1)

    with open(coverage_file) as f:
        return json.load(f)


def calculate_module_coverage(files: Dict[str, Dict]) -> Dict[str, Dict]:
    """Calculate coverage statistics per module.

    Args:
        files: Coverage data for each file

    Returns:
        Dictionary mapping module names to coverage statistics
    """
    modules = {}

    for filepath, data in files.items():
        if not filepath.startswith("google_contacts_cisco/"):
            continue

        # Skip __init__.py files
        if filepath.endswith("__init__.py"):
            continue

        # Skip main.py (entry point)
        if filepath.endswith("main.py"):
            continue

        # Extract module name
        parts = filepath.split("/")
        if len(parts) >= 2:
            # Check if parts[1] is a file (has .py extension) or directory
            module_part = parts[1]
            if module_part.endswith(".py"):
                # Remove .py extension for root-level files
                module_part = module_part[:-3]
            module = f"google_contacts_cisco.{module_part}"
        else:
            module = "google_contacts_cisco"

        # Initialize module stats if needed
        if module not in modules:
            modules[module] = {
                "covered": 0,
                "total": 0,
                "files": [],
            }

        # Get coverage stats
        summary = data.get("summary", {})
        covered = summary.get("covered_lines", 0)
        total = summary.get("num_statements", 0)
        percent = summary.get("percent_covered", 0.0)

        # Add to module totals
        modules[module]["covered"] += covered
        modules[module]["total"] += total
        modules[module]["files"].append(
            {
                "path": filepath,
                "covered": covered,
                "total": total,
                "percent": percent,
            }
        )

    # Calculate percentages
    for module_data in modules.values():
        if module_data["total"] > 0:
            module_data["percent"] = (
                module_data["covered"] / module_data["total"]
            ) * 100
        else:
            module_data["percent"] = 0.0

    return modules


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{BLUE}{'=' * 60}{NC}")
    print(f"{BLUE}{BOLD}{text}{NC}")
    print(f"{BLUE}{'=' * 60}{NC}\n")


def print_overall_summary(coverage_data: Dict):
    """Print overall coverage summary."""
    totals = coverage_data.get("totals", {})
    percent = totals.get("percent_covered", 0.0)
    covered = totals.get("covered_lines", 0)
    total = totals.get("num_statements", 0)

    print_header("Overall Coverage Summary")

    # Color based on coverage level
    if percent >= 80:
        color = GREEN
        status = "✓ PASSING"
    elif percent >= 70:
        color = YELLOW
        status = "⚠ WARNING"
    else:
        color = RED
        status = "✗ FAILING"

    print(f"  {BOLD}Total Coverage:{NC} {color}{percent:.2f}%{NC} {color}{status}{NC}")
    print(f"  Lines Covered: {covered}/{total}")
    print()


def print_module_breakdown(modules: Dict[str, Dict], threshold: float):
    """Print per-module coverage breakdown."""
    print_header("Coverage by Module")

    # Sort modules by coverage (lowest first)
    sorted_modules = sorted(modules.items(), key=lambda x: x[1]["percent"])

    for module, data in sorted_modules:
        percent = data["percent"]
        covered = data["covered"]
        total = data["total"]
        file_count = len(data["files"])

        # Color based on coverage
        if percent >= threshold:
            color = GREEN
            marker = "✓"
        elif percent >= threshold - 10:
            color = YELLOW
            marker = "⚠"
        else:
            color = RED
            marker = "✗"

        # Mark critical modules
        is_critical = any(module.startswith(cm) for cm in CRITICAL_MODULES)
        critical_marker = f"{RED}[CRITICAL]{NC}" if is_critical else ""

        print(
            f"  {marker} {color}{percent:6.2f}%{NC}  {module:40s}  "
            f"({covered:4d}/{total:4d} lines, {file_count} files) {critical_marker}"
        )


def identify_gaps(
    modules: Dict[str, Dict], threshold: float
) -> List[Tuple[str, float]]:
    """Identify modules below coverage threshold.

    Returns:
        List of (module_name, coverage_percent) tuples for modules below threshold
    """
    gaps = []

    for module, data in modules.items():
        if data["percent"] < threshold:
            gaps.append((module, data["percent"]))

    return sorted(gaps, key=lambda x: x[1])  # Sort by coverage (lowest first)


def print_coverage_gaps(gaps: List[Tuple[str, float]], threshold: float):
    """Print modules with coverage below threshold."""
    if not gaps:
        print_header("Coverage Gaps")
        print(f"  {GREEN}✓ All modules meet the {threshold}% threshold!{NC}\n")
        return

    print_header(f"Modules Below {threshold}% Threshold")

    for module, percent in gaps:
        diff = threshold - percent
        is_critical = any(module.startswith(cm) for cm in CRITICAL_MODULES)

        if is_critical:
            print(
                f"  {RED}✗ {module:40s}  {percent:6.2f}%  "
                f"(need {diff:+.2f}%) [CRITICAL]{NC}"
            )
        else:
            print(
                f"  {YELLOW}⚠ {module:40s}  {percent:6.2f}%  "
                f"(need {diff:+.2f}%){NC}"
            )

    print()


def print_recommendations(gaps: List[Tuple[str, float]], modules: Dict[str, Dict]):
    """Print actionable recommendations."""
    if not gaps:
        return

    print_header("Recommendations")

    # Identify critical gaps
    critical_gaps = [
        (module, percent)
        for module, percent in gaps
        if any(module.startswith(cm) for cm in CRITICAL_MODULES)
    ]

    if critical_gaps:
        print(f"{RED}Priority 1: Critical Modules{NC}")
        print("  These modules are essential and need immediate attention:\n")
        for module, percent in critical_gaps[:3]:  # Top 3
            files = modules[module]["files"]
            print(f"  • {module} ({percent:.2f}%)")
            # Show files with lowest coverage
            low_coverage_files = sorted(files, key=lambda x: x["percent"])[:2]
            for file_data in low_coverage_files:
                if file_data["percent"] < 80:
                    print(f"    - {file_data['path']} ({file_data['percent']:.2f}%)")
        print()

    # Identify high priority gaps
    high_priority_gaps = [
        (module, percent)
        for module, percent in gaps
        if any(module.startswith(hp) for hp in HIGH_PRIORITY_MODULES)
        and module not in [m for m, _ in critical_gaps]
    ]

    if high_priority_gaps:
        print(f"{YELLOW}Priority 2: High Priority Modules{NC}")
        print("  These modules should be addressed next:\n")
        for module, percent in high_priority_gaps[:3]:  # Top 3
            print(f"  • {module} ({percent:.2f}%)")
        print()

    print(f"{BLUE}General Tips:{NC}")
    print("  1. Run: ./scripts/test.sh --verbose")
    print("  2. View HTML report: open htmlcov/index.html")
    print("  3. Focus on untested branches and error paths")
    print("  4. Add tests for edge cases and validation")
    print("  5. Mock external dependencies (Google API, etc.)")
    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify test coverage and identify gaps"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=80.0,
        help="Coverage threshold percentage (default: 80.0)",
    )
    parser.add_argument(
        "--critical-only",
        action="store_true",
        help="Only check critical modules",
    )
    parser.add_argument(
        "--fail-under",
        type=float,
        help="Exit with error if coverage is below this threshold",
    )

    args = parser.parse_args()

    # Load coverage data
    coverage_data = load_coverage_data()

    # Calculate module coverage
    all_modules = calculate_module_coverage(coverage_data.get("files", {}))

    # Filter to critical modules if requested
    if args.critical_only:
        modules = {
            name: data
            for name, data in all_modules.items()
            if any(name.startswith(cm) for cm in CRITICAL_MODULES)
        }
    else:
        modules = all_modules

    # Print reports
    print_overall_summary(coverage_data)
    print_module_breakdown(modules, args.threshold)

    # Identify and print gaps
    gaps = identify_gaps(modules, args.threshold)
    print_coverage_gaps(gaps, args.threshold)
    print_recommendations(gaps, modules)

    # Check if we should fail
    overall_percent = coverage_data.get("totals", {}).get("percent_covered", 0.0)
    fail_threshold = args.fail_under if args.fail_under is not None else args.threshold

    if overall_percent < fail_threshold:
        print(
            f"{RED}✗ Coverage {overall_percent:.2f}% is below threshold "
            f"{fail_threshold:.2f}%{NC}\n"
        )
        sys.exit(1)

    if gaps:
        print(f"{YELLOW}⚠ Some modules are below {args.threshold}% threshold{NC}\n")
        sys.exit(0)  # Warning, but not a failure

    print(f"{GREEN}✓ All modules meet coverage requirements!{NC}\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
