#!/usr/bin/env python3
# /config/bin/knowledge-base-index.py
# Knowledge Base Indexer for Hestia Documentation
# To leverage for BB8 project

import datetime
import json
import os
import re
from pathlib import Path

# Configuration
CONFIG_ROOT = "/config"
OUTPUT_DIR = "/config/.workspace"
INDEX_PATHS = {
    "guides": "/config/hestia/library/docs/guides",
    "playbooks": "/config/hestia/library/docs/playbooks",
    "ha_addon": "/config/hestia/library/ha_implementation/addon",
    "ha_automation": "/config/hestia/library/ha_implementation/automation",
    "ha_hacs": "/config/hestia/library/ha_implementation/hacs",
    "ha_homeassistant": "/config/hestia/library/ha_implementation/homeassistant",
    "ha_integration": "/config/hestia/library/ha_implementation/integration",
    "ha_vscode": "/config/hestia/library/ha_implementation/vscode",
}

os.makedirs(OUTPUT_DIR, exist_ok=True)


def read_file(path):
    """Safely read file content"""
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Warning: Could not read {path}: {e}")
        return ""


def extract_field(regex, text, flags=re.I | re.M):
    """Extract field using regex"""
    match = re.search(regex, text, flags)
    return match.group(1).strip() if match else ""


def extract_yaml_frontmatter(text):
    """Extract YAML frontmatter fields"""
    frontmatter = {}
    yaml_match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if yaml_match:
        yaml_content = yaml_match.group(1)
        # Simple YAML parsing for common fields
        for line in yaml_content.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip().strip("\"'")
                frontmatter[key] = value
    return frontmatter


def extract_summary(text, max_length=200):
    """Extract meaningful summary from content"""
    # Remove frontmatter
    text = re.sub(r"^---.*?---\n", "", text, flags=re.DOTALL)
    # Remove markdown headers
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    # Get first paragraph or meaningful content
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if paragraphs:
        summary = paragraphs[0]
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
        return summary
    return "(No description available)"


def categorize_content_type(path, content):
    """Determine content type from path and content"""
    path_str = str(path).lower()
    content_lower = content.lower()

    # Check for specific indicators
    if "blueprint" in path_str or "blueprint" in content_lower:
        return "blueprint"
    elif "automation" in path_str:
        return "automation"
    elif "integration" in path_str:
        return "integration"
    elif "addon" in path_str or "add-on" in content_lower:
        return "addon"
    elif "guide" in path_str or "tutorial" in content_lower:
        return "guide"
    elif "playbook" in path_str:
        return "playbook"
    elif "vscode" in path_str:
        return "vscode"
    elif "hacs" in path_str:
        return "hacs"
    else:
        return "documentation"


def scan_directory(base_path, category):
    """Scan directory for documentation files"""
    records = []
    if not os.path.exists(base_path):
        print(f"Warning: Directory {base_path} does not exist")
        return records

    for root, dirs, files in os.walk(base_path):
        for file in files:
            # Only process documentation files
            if not file.lower().endswith((".md", ".rst", ".txt", ".adoc")):
                continue

            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, CONFIG_ROOT)
            content = read_file(file_path)

            # Extract metadata
            frontmatter = extract_yaml_frontmatter(content)
            title = (
                frontmatter.get("title")
                or extract_field(r"^\s*#\s+(.+)$", content)
                or Path(file).stem.replace("_", " ").replace("-", " ").title()
            )

            # Additional metadata
            tags = frontmatter.get("tags", "").split(",") if frontmatter.get("tags") else []
            tags.extend(re.findall(r"#[\w-]+", content))  # Extract hashtags
            tags = [tag.strip("#").strip() for tag in tags if tag.strip()]

            record = {
                "path": file_path,
                "relative_path": relative_path,
                "title": title,
                "category": category,
                "content_type": categorize_content_type(file_path, content),
                "author": frontmatter.get("author", ""),
                "date": frontmatter.get("date", ""),
                "last_updated": frontmatter.get("last_updated", ""),
                "summary": extract_summary(content),
                "tags": sorted(set(tags)),
                "slug": frontmatter.get("slug", ""),
                "source": frontmatter.get("source", ""),
                "file_size": len(content),
                "word_count": len(content.split()),
            }
            records.append(record)

    return records


def generate_index():
    """Generate complete knowledge base index"""
    all_records = []
    category_stats = {}

    print("Scanning knowledge base directories...")

    for category, path in INDEX_PATHS.items():
        print(f"Processing {category}: {path}")
        records = scan_directory(path, category)
        all_records.extend(records)
        category_stats[category] = len(records)
        print(f"  Found {len(records)} documents")

    # Sort records by category, then title
    all_records.sort(key=lambda r: (r["category"], r["title"]))

    # Generate timestamp
    timestamp = datetime.datetime.utcnow().isoformat(timespec="seconds")

    # Write JSON index
    json_path = os.path.join(OUTPUT_DIR, "knowledge_base_index.json")
    index_data = {
        "generated": timestamp,
        "total_documents": len(all_records),
        "categories": category_stats,
        "documents": all_records,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)

    # Write Markdown index
    md_path = os.path.join(OUTPUT_DIR, "knowledge_base_index.md")
    generate_markdown_index(all_records, category_stats, timestamp, md_path)

    print("\nGenerated indexes:")
    print(f"  JSON: {json_path}")
    print(f"  Markdown: {md_path}")
    print(f"  Total documents: {len(all_records)}")

    return all_records


def generate_markdown_index(records, stats, timestamp, output_path):
    """Generate human-readable markdown index"""
    md = []

    # Header
    md.append("# Knowledge Base Index (autogenerated)\n")
    md.append(f"_Generated (UTC): {timestamp}_\n")

    # Summary statistics
    md.append("## Summary")
    md.append(f"**Total Documents**: {len(records)}\n")
    md.append("**Categories**:")
    for category, count in sorted(stats.items()):
        md.append(f"- **{category.replace('_', ' ').title()}**: {count} documents")
    md.append("")

    # Content by category
    md.append("---\n")
    md.append("## Document Catalog\n")

    current_category = None
    for record in records:
        if record["category"] != current_category:
            current_category = record["category"]
            md.append(f"### {current_category.replace('_', ' ').title()}\n")

        # Format document entry
        title = record["title"]
        path = record["relative_path"]
        content_type = record["content_type"].title()
        summary = record["summary"]

        md.append(f"- **{title}** _{content_type}_")
        md.append(f"  `{path}`")
        if summary != "(No description available)":
            md.append(f"  {summary}")
        if record["tags"]:
            tags_str = ", ".join(f"`{tag}`" for tag in record["tags"][:5])  # Limit tags
            md.append(f"  Tags: {tags_str}")
        md.append("")

    # Write file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))


if __name__ == "__main__":
    try:
        generate_index()
        print("\nKnowledge base indexing completed successfully!")
    except Exception as e:
        print(f"Error generating knowledge base index: {e}")
        exit(1)
