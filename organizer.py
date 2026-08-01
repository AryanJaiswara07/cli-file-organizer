#!/usr/bin/env python3
"""
CLI File Organizer
==================
Organizes files in a directory into categorized subfolders
based on their file extensions.

Usage:
    python organizer.py /path/to/messy/folder
    python organizer.py /path/to/folder --dry-run
    python organizer.py /path/to/folder --recursive
    python organizer.py /path/to/folder --undo
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

LOG_FILENAME = ".organizer_log.json"

# ─── File Category Mapping ────────────────────────────────────────────────────
# Each key is a category (folder name), value is a set of extensions (lowercase)
CATEGORIES = {
    "Images": {
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp",
        ".ico", ".tiff", ".tif", ".psd", ".raw", ".heic",
    },
    "Documents": {
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".txt", ".rtf", ".odt", ".csv", ".pages", ".numbers", ".key",
        ".tex", ".md", ".rst", ".epub",
    },
    "Videos": {
        ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
        ".m4v", ".mpg", ".mpeg", ".3gp",
    },
    "Audio": {
        ".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a",
        ".opus", ".aiff",
    },
    "Archives": {
        ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz",
        ".tar.gz", ".tar.bz2", ".tar.xz", ".zst",
    },
    "Code": {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp",
        ".h", ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt",
        ".html", ".css", ".scss", ".sql", ".sh", ".bat", ".ps1",
    },
    "Fonts": {
        ".ttf", ".otf", ".woff", ".woff2", ".eot",
    },
    "Executables": {
        ".exe", ".msi", ".dmg", ".deb", ".rpm", ".AppImage", ".apk",
    },
    "Data": {
        ".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg",
        ".conf", ".env", ".db", ".sqlite",
    },
}

# Build a reverse lookup: extension -> category
EXTENSION_MAP = {}
for category, extensions in CATEGORIES.items():
    for ext in extensions:
        EXTENSION_MAP[ext] = category


def get_category(file_path: Path) -> str:
    """Determine the category folder for a given file."""
    ext = file_path.suffix.lower()
    return EXTENSION_MAP.get(ext, "Others")


def save_log(folder: Path, entries: list):
    """Save move log to a JSON file in the folder."""
    log_path = folder / LOG_FILENAME
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "folder": str(folder),
        "moves": entries,
    }
    with open(log_path, "w") as f:
        json.dump(log_data, f, indent=2)


def load_log(folder: Path) -> dict:
    """Load the move log from the folder."""
    log_path = folder / LOG_FILENAME
    if not log_path.exists():
        return None
    with open(log_path, "r") as f:
        return json.load(f)


def undo_organize(folder: Path):
    """
    Undo the last organize operation by reading the log file
    and moving files back to their original locations.
    """
    log_data = load_log(folder)

    if log_data is None:
        print(f"\n  ❌ No undo log found in {folder}")
        print(f"     Nothing to undo.\n")
        return

    moves = log_data.get("moves", [])
    timestamp = log_data.get("timestamp", "unknown")

    print(f"\n  📜 Found log from {timestamp}")
    print(f"     {len(moves)} move(s) to undo\n")
    print(f"  {'─' * 50}")

    restored = 0
    failed = 0

    for entry in moves:
        original = Path(entry["original"])
        current = Path(entry["current"])

        if not current.exists():
            print(f"    ⚠️  {current.name} — file no longer exists at {current}")
            failed += 1
            continue

        # Ensure original parent exists
        original.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.move(str(current), str(original))
            print(f"    ↩️  {current.name}")
            print(f"       → {original.parent}/")
            restored += 1
        except Exception as e:
            print(f"    ❌ {current.name} — {e}")
            failed += 1

    # Clean up empty category folders
    category_folders = set(CATEGORIES.keys()) | {"Others"}
    for cat in category_folders:
        cat_dir = folder / cat
        if cat_dir.exists() and cat_dir.is_dir() and not any(cat_dir.iterdir()):
            cat_dir.rmdir()

    # Remove log file
    log_path = folder / LOG_FILENAME
    if log_path.exists():
        log_path.unlink()

    # Summary
    print(f"\n  {'─' * 50}")
    print(f"\n  📊 Undo Summary:")
    print(f"     ✅ Restored: {restored}")
    if failed:
        print(f"     ❌ Failed:   {failed}")
    print()


def organize_folder(
    folder: Path,
    dry_run: bool = False,
    recursive: bool = False,
) -> dict:
    """
    Move files in `folder` into categorized subfolders.

    Args:
        folder:    The directory to organize.
        dry_run:   If True, only show what would happen without moving files.
        recursive: If True, also process subdirectories.

    Returns:
        A summary dict with counts per category.
    """
    summary = {}
    total_moved = 0
    total_skipped = 0
    move_log = []  # Track every move for undo

    # Gather files
    if recursive:
        files = [f for f in folder.rglob("*") if f.is_file() and f.name != LOG_FILENAME]
    else:
        files = [f for f in folder.iterdir() if f.is_file() and f.name != LOG_FILENAME]

    if not files:
        print(f"\n  No files found in {folder}")
        return summary

    # Skip files already inside our category folders
    category_folders = set(CATEGORIES.keys()) | {"Others"}

    print(f"\n  Scanning: {folder.resolve()}")
    print(f"  {'[DRY RUN] ' if dry_run else ''}Found {len(files)} file(s)\n")
    print(f"  {'─' * 50}")

    for file_path in files:
        # In non-recursive mode, only process files directly in the folder
        if not recursive and file_path.parent.resolve() != folder.resolve():
            total_skipped += 1
            continue

        # Skip files already inside a category folder
        relative = file_path.relative_to(folder)
        if len(relative.parts) > 1 and relative.parts[0] in category_folders:
            total_skipped += 1
            continue

        category = get_category(file_path)
        dest_dir = folder / category
        dest_path = dest_dir / file_path.name

        # Handle duplicate filenames
        counter = 1
        while dest_path.exists():
            stem = file_path.stem
            suffix = file_path.suffix
            dest_path = dest_dir / f"{stem}_{counter}{suffix}"
            counter += 1

        summary.setdefault(category, []).append(file_path.name)

        if dry_run:
            print(f"    📄 {file_path.name}")
            print(f"       → {category}/")
            total_moved += 1
        else:
            dest_dir.mkdir(exist_ok=True)
            shutil.move(str(file_path), str(dest_path))
            print(f"    ✅ {file_path.name}")
            print(f"       → {category}/")
            total_moved += 1

            # Log the move for undo
            move_log.append({
                "original": str(file_path),
                "current": str(dest_path),
            })

    # Save log for undo (only if we actually moved files)
    if move_log:
        save_log(folder, move_log)

    # Print summary
    print(f"\n  {'─' * 50}")
    print(f"\n  📊 Summary:")

    if summary:
        for category, files in sorted(summary.items()):
            print(f"     {category}: {len(files)} file(s)")

    print(f"\n     Total: {total_moved} moved, {total_skipped} skipped")

    if dry_run:
        print(f"\n     🔍 This was a dry run — no files were actually moved.")
    elif move_log:
        print(f"\n     💾 Move log saved. Use --undo to reverse.")

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="📁 CLI File Organizer — Organize messy folders by file type",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python organizer.py ~/Downloads
  python organizer.py ~/Downloads --dry-run
  python organizer.py ~/Desktop --recursive
  python organizer.py ~/Downloads --undo
  python organizer.py . --dry-run --recursive

Categories:
  Images, Documents, Videos, Audio, Archives,
  Code, Fonts, Executables, Data, Others
        """,
    )

    parser.add_argument(
        "folder",
        type=str,
        help="Path to the folder you want to organize",
    )
    parser.add_argument(
        "-n", "--dry-run",
        action="store_true",
        help="Preview changes without actually moving files",
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Include files in subdirectories",
    )
    parser.add_argument(
        "-u", "--undo",
        action="store_true",
        help="Undo the last organize operation and restore files",
    )

    args = parser.parse_args()

    folder = Path(args.folder).expanduser().resolve()

    # Validate folder
    if not folder.exists():
        print(f"\n  ❌ Error: Folder not found: {folder}")
        sys.exit(1)

    if not folder.is_dir():
        print(f"\n  ❌ Error: Not a directory: {folder}")
        sys.exit(1)

    # Banner
    print(f"""
  ╔═══════════════════════════════════════╗
  ║       📁 CLI FILE ORGANIZER          ║
  ╚═══════════════════════════════════════╝
    """)

    start_time = datetime.now()

    if args.undo:
        undo_organize(folder)
    else:
        organize_folder(folder, dry_run=args.dry_run, recursive=args.recursive)

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"     Time: {elapsed:.2f}s\n")


if __name__ == "__main__":
    main()
