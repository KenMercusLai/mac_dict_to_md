#!/usr/bin/env python3
"""
Splits a large dictionary XML file into individual entry files.

Each <d:entry> element is extracted and saved to a separate XML file,
named after the word (d:title attribute). Homographs are distinguished
by appending the homograph number to the filename.
"""

import re
import sys
from pathlib import Path
from typing import Iterator, NamedTuple


class Entry(NamedTuple):
    """Represents a dictionary entry with its content and metadata."""
    title: str
    homograph: str | None
    content: str


def make_filename(entry: Entry) -> str:
    """
    Generate a filename for an entry.

    Uses 'word.xml' for entries without homograph,
    'word_N.xml' for entries with homograph number N.
    Special characters that are invalid in filenames are replaced with '_'.
    """
    sanitized_title = re.sub(r'[/\\:*?"<>|]', '_', entry.title.strip())

    if entry.homograph:
        return f"{sanitized_title}_{entry.homograph}.xml"
    return f"{sanitized_title}.xml"


def extract_title(entry_content: str) -> str:
    """Extract the d:title attribute from the d:entry tag."""
    title_match = re.search(r'd:title="([^"]*)"', entry_content)
    return title_match.group(1) if title_match else ""


def extract_homograph(entry_content: str) -> str | None:
    """
    Extract homograph number from the entry content.

    The homograph attribute is on <span class="hw" homograph="N">,
    not on the d:entry tag itself.
    """
    homograph_match = re.search(r'<span\s+[^>]*class="hw"[^>]*homograph="(\d+)"', entry_content)
    if not homograph_match:
        homograph_match = re.search(r'<span\s+[^>]*homograph="(\d+)"[^>]*class="hw"', entry_content)
    return homograph_match.group(1) if homograph_match else None


def find_entries(content: str) -> Iterator[Entry]:
    """
    Find all d:entry elements in the XML content.

    Uses regex to locate entry boundaries without full XML parsing,
    which is more efficient for very large files.
    """
    entry_pattern = re.compile(
        r'<d:entry\s+[^>]*>.*?</d:entry>',
        re.DOTALL
    )

    for match in entry_pattern.finditer(content):
        entry_content = match.group(0)
        title = extract_title(entry_content)
        homograph = extract_homograph(entry_content)

        if title.strip():
            yield Entry(
                title=title,
                homograph=homograph,
                content=entry_content
            )


def save_entry(entry: Entry, output_dir: Path) -> Path:
    """Save an entry to a file and return the file path."""
    filename = make_filename(entry)
    filepath = output_dir / filename
    filepath.write_text(entry.content, encoding='utf-8')
    return filepath


def process_entries(entries: Iterator[Entry], output_dir: Path) -> Iterator[Path]:
    """Process all entries and yield the paths of created files."""
    return (save_entry(entry, output_dir) for entry in entries)


def split_dictionary(input_path: Path, output_dir: Path) -> int:
    """
    Split a dictionary XML file into individual entry files.

    Returns the count of entries processed.
    """
    content = input_path.read_text(encoding='utf-8')
    entries = find_entries(content)

    output_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for filepath in process_entries(entries, output_dir):
        print(f"Created: {filepath.name}")
        count += 1

    return count


def main() -> int:
    """Main entry point."""
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <dictionary.xml>", file=sys.stderr)
        return 1

    input_path = Path(sys.argv[1])

    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        return 1

    output_dir = Path("entries")

    print(f"Splitting {input_path} into {output_dir}/...")
    count = split_dictionary(input_path, output_dir)
    print(f"Done. Created {count} entry files.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
