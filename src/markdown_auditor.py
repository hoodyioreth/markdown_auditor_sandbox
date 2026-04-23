#!/usr/bin/env python3

"""
markdown_auditor.py

Version: 1.2.1

Scans a directory recursively for Markdown files and generates a report:
- Total markdown files
- Total links
- Image links
- Broken markdown links
- Broken image links
- Largest files

Usage:
    python markdown_auditor.py [--root ../test_data] [--output ../output/audit_report.md]
"""

from pathlib import Path
import argparse
import re
from urllib.parse import unquote
from collections import Counter

__version__ = "1.2.1"


LINK_PATTERN = re.compile(r'(?<!!)\[.*?\]\((.*?)\)')
IMAGE_PATTERN = re.compile(r'!\[.*?\]\((.*?)\)')
CODE_BLOCK_PATTERN = re.compile(r'```.*?```', re.DOTALL)
INLINE_CODE_PATTERN = re.compile(r'`[^`]*`')


def is_external(link: str) -> bool:
    return link.startswith("http://") or link.startswith("https://")


def strip_code(text: str) -> str:
    """Remove fenced and inline code so link regexes do not inspect code samples."""
    text = CODE_BLOCK_PATTERN.sub("", text)
    text = INLINE_CODE_PATTERN.sub("", text)
    return text


def normalise_link_target(link: str) -> str:
    """Strip optional title text, anchors, and URL encoding from a Markdown link target."""
    cleaned = link.strip()

    if ' "' in cleaned:
        cleaned = cleaned.split(' "', 1)[0]
    elif " '" in cleaned:
        cleaned = cleaned.split(" '", 1)[0]

    cleaned = cleaned.split("#", 1)[0].strip()
    cleaned = unquote(cleaned)
    return cleaned


def rel_to_root(path: Path, root: Path) -> str:
    """Return a display-friendly path relative to the audit root when possible."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def count_broken_links(items):
    """Count duplicate broken links by (file, target)."""
    return Counter(items)


def audit_markdown(root: Path):
    md_files = list(root.rglob("*.md"))

    total_links = 0
    image_links = 0
    broken_markdown_links = []
    broken_image_links = []
    file_sizes = []

    for md_file in md_files:
        text = md_file.read_text(encoding="utf-8", errors="ignore")
        text = strip_code(text)

        links = LINK_PATTERN.findall(text)
        images = IMAGE_PATTERN.findall(text)

        total_links += len(links)
        image_links += len(images)

        for link in links:
            link_target = normalise_link_target(link)

            if not link_target or is_external(link_target):
                continue

            target = (md_file.parent / link_target).resolve()
            if not target.exists():
                broken_markdown_links.append((md_file, link_target))

        for image in images:
            image_target = normalise_link_target(image)

            if not image_target or is_external(image_target):
                continue

            target = (md_file.parent / image_target).resolve()
            if not target.exists():
                broken_image_links.append((md_file, image_target))

        file_sizes.append((md_file, md_file.stat().st_size))

    largest_files = sorted(file_sizes, key=lambda x: x[1], reverse=True)[:5]

    broken_markdown_link_counts = count_broken_links(broken_markdown_links)
    broken_image_link_counts = count_broken_links(broken_image_links)

    return {
        "total_files": len(md_files),
        "total_links": total_links,
        "image_links": image_links,
        "broken_markdown_links": broken_markdown_links,
        "broken_image_links": broken_image_links,
        "broken_markdown_link_counts": broken_markdown_link_counts,
        "broken_image_link_counts": broken_image_link_counts,
        "largest_files": largest_files,
    }


def write_report(data, output_path: Path, root: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        f.write("# Markdown Audit Report\n\n")
        f.write(f"Version: {__version__}\n\n")
        f.write(f"Audit root: {root}\n\n")
        f.write(f"Total Markdown files: {data['total_files']}\n\n")
        f.write(f"Total links: {data['total_links']}\n\n")
        f.write(f"Image links: {data['image_links']}\n\n")
        f.write(f"Broken markdown links: {len(data['broken_markdown_links'])}\n\n")
        f.write(f"Broken image links: {len(data['broken_image_links'])}\n\n")

        f.write("## Broken Markdown Links\n")
        if data["broken_markdown_link_counts"]:
            for (file, link), count in sorted(
                data["broken_markdown_link_counts"].items(),
                key=lambda x: (str(x[0][0]), x[0][1])
            ):
                suffix = f" (x{count})" if count > 1 else ""
                f.write(f"- {rel_to_root(file, root)}: {link}{suffix}\n")
        else:
            f.write("- None\n")

        f.write("\n## Broken Image Links\n")
        if data["broken_image_link_counts"]:
            for (file, link), count in sorted(
                data["broken_image_link_counts"].items(),
                key=lambda x: (str(x[0][0]), x[0][1])
            ):
                suffix = f" (x{count})" if count > 1 else ""
                f.write(f"- {rel_to_root(file, root)}: {link}{suffix}\n")
        else:
            f.write("- None\n")

        f.write("\n## Largest Files\n")
        for file, size in data["largest_files"]:
            f.write(f"- {rel_to_root(file, root)} ({size} bytes)\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", "-v", action="store_true", help="Show script version")
    parser.add_argument("--root", default="../test_data", help="Root folder to scan")
    parser.add_argument("--output", default="../output/audit_report.md", help="Output report path")

    args = parser.parse_args()

    if args.version:
        print(f"markdown_auditor.py version {__version__}")
        return

    using_default_root = args.root == "../test_data"
    using_default_output = args.output == "../output/audit_report.md"

    if using_default_root:
        print("Using default --root: ../test_data")
    if using_default_output:
        print("Using default --output: ../output/audit_report.md")

    root = Path(args.root).resolve()
    output = Path(args.output).resolve()

    if not root.exists():
        print(f"Error: {root} does not exist")
        return

    data = audit_markdown(root)
    write_report(data, output, root)

    print(f"Report written to {output}")


if __name__ == "__main__":
    main()