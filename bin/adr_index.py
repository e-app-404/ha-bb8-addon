#!/usr/bin/env python3
# /config/bin/adr-index.py - Configuration-Driven ADR Governance Index Renderer
import datetime
import json
import os
import re
import sys
from pathlib import Path

try:
    import toml
except ImportError:
    print("ERROR: toml module is required for configuration parsing")
    exit(1)

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml module is required for frontmatter parsing")
    exit(1)

# Path resolution (supports HA host and local workspace)
REPO_ROOT = Path(__file__).resolve().parents[1]


def _resolve_paths():
    """Resolve configuration, ADR, and output directories.

    Preference order:
    1) Explicit CLI/env overrides (CONFIG_ROOT, WORKSPACE_ROOT)
    2) HA host defaults under /config
    3) Local workspace defaults under the repository
    """
    # Env hints
    config_root = Path(os.environ.get("CONFIG_ROOT", "/config"))
    workspace_root = Path(os.environ.get("WORKSPACE_ROOT", str(REPO_ROOT)))

    # Candidate host paths
    host_meta = config_root / "hestia/config/meta/adr.toml"
    host_adr_dir = config_root / "hestia/library/docs/ADR"
    host_output = config_root / ".workspace"

    # Workspace defaults
    ws_meta = workspace_root / "docs/meta/adr.toml"
    ws_adr_dir = workspace_root / "docs/ADR"
    ws_output = workspace_root / "reports/governance"

    if host_meta.exists() and host_adr_dir.exists():
        base_root = config_root
        meta_path = host_meta
        adr_dir = host_adr_dir
        out_dir = host_output
    else:
        base_root = workspace_root
        meta_path = ws_meta
        adr_dir = ws_adr_dir
        out_dir = ws_output

    out_dir.mkdir(parents=True, exist_ok=True)
    return base_root, meta_path, adr_dir, out_dir


CONFIG_DIR, META_CONFIG_PATH, ADR_DIR, OUTPUT_DIR = _resolve_paths()


class ADRIndexRenderer:
    """Configuration-driven ADR governance index renderer"""

    def __init__(self):
        self.config = self.load_config()
        self.rendering_config = self.config.get("rendering", {})
        self.record_config = self.rendering_config.get("record", {})
        self.field_configs = self.config.get("fields", {})
        # Derived for convenience
        self.record_field_display = self.record_config.get("fields", {})

    def load_config(self):
        """Load configuration from meta/adr.toml"""
        try:
            return toml.load(META_CONFIG_PATH)
        except Exception as e:
            print(f"ERROR: Could not load configuration from {META_CONFIG_PATH}: {e}")
            exit(1)

    def read_file_safely(self, path):
        """Safely read file content with encoding handling"""
        try:
            with open(path, encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Warning: Could not read {path}: {e}")
            return ""

    def extract_frontmatter(self, content):
        """Extract and parse YAML frontmatter from content"""
        if not content.startswith("---"):
            return {}

        frontmatter_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not frontmatter_match:
            return {}

        try:
            return yaml.safe_load(frontmatter_match.group(1)) or {}
        except Exception as e:
            print(f"Warning: Could not parse YAML frontmatter: {e}")
            return {}

    def extract_decision_from_body(self, content: str) -> str:
        """Extract a short decision summary from body per config patterns.

        Uses extraction patterns from [extraction.decision] in the config.
        """
        decision_cfg = (
            self.config.get("extraction", {}).get("decision", {})
        )
        primary = decision_cfg.get("primary_patterns", [])
        fallback = decision_cfg.get("fallback_patterns", [])
        max_sentences = int(decision_cfg.get("max_sentences", 2))
        sentence_break = decision_cfg.get(
            "sentence_break_pattern", r"(?<=[.!?])\s+"
        )
        default_text = decision_cfg.get(
            "default_text", "Architectural decision documented in this ADR."
        )

        def _first_match(patterns):
            for pat in patterns:
                m = re.search(pat, content, re.DOTALL)
                if m:
                    # Take first capturing group or whole match
                    txt = m.group(1) if m.groups() else m.group(0)
                    txt = txt.strip()
                    if txt:
                        return txt
            return ""

        text = _first_match(primary) or _first_match(fallback)
        if not text:
            return default_text

        # Trim to N sentences
        parts = re.split(sentence_break, text)
        return " ".join(parts[:max_sentences]).strip()

    @staticmethod
    def _normalize_decision(text: str) -> str:
        """Normalize decision text to meet length and style constraints.

        Rules (aligned with docs/meta/adr.toml intent):
        - Collapse whitespace; remove backticks
        - Sentence case first character
        - Limit to 1–2 sentences and 20–300 characters
        - Ensure final period if not already ending with punctuation
        """
        if not text:
            return "Architectural decision documented in this ADR."

        # Remove code backticks and collapse whitespace
        cleaned = re.sub(r"\s+", " ", text.replace("`", "").strip())

        # Sentence case (best effort)
        if cleaned:
            cleaned = cleaned[0].upper() + cleaned[1:]

        # Enforce max length boundary at sentence end if possible
        max_len = 300
        min_len = 20
        if len(cleaned) > max_len:
            # Try cut at nearest sentence boundary before max_len
            cut = cleaned[: max_len + 1]
            m = re.search(r"[.!?](?!.*[.!?]).*$", cut)
            if m:
                end = m.end()
                cleaned = cut[:end].strip()
            else:
                cleaned = cleaned[:max_len].rstrip()

        # Ensure terminal punctuation
        if cleaned and cleaned[-1] not in ".!?":
            cleaned = cleaned + "."

        # Enforce minimum length by appending a short scope note
        if len(cleaned) < min_len:
            cleaned = (cleaned.rstrip(".")) + ". Applies to this project."

        return cleaned

    @staticmethod
    def _match_frontmatter_block(content: str):
        """Return (match, fm_text, body_start_idx) for the YAML frontmatter block."""
        if not content.startswith("---"):
            return None, "", 0
        m = re.match(r"^---\n(.*?)\n---\n?", content, re.DOTALL)
        if not m:
            return None, "", 0
        fm_text = m.group(1)
        return m, fm_text, m.end()

    def _insert_decision_into_frontmatter(
        self, frontmatter: dict, decision_text: str
    ) -> dict:
        """Return a new dict with 'decision' inserted in a stable position.

        Preferred insertion point: after 'status' if present; else after 'title'; else at the end.
        """
        if frontmatter.get("decision"):
            return frontmatter

        ordered_keys = list(frontmatter.keys())
        new_fm: dict = {}
        inserted = False

        def maybe_insert():
            nonlocal inserted
            if not inserted:
                new_fm["decision"] = decision_text
                inserted = True

        for k in ordered_keys:
            new_fm[k] = frontmatter[k]
            if k == "status" or (k == "title" and "status" not in frontmatter):
                maybe_insert()

        if not inserted:
            maybe_insert()

        return new_fm

    def autofill_decisions(self) -> tuple[int, int, list[str]]:
        """Walk ADRs and insert a generated 'decision' into frontmatter if missing.

        Returns: (updated_count, skipped_count, updated_files)
        Skips files without frontmatter or with an existing non-empty decision.
        """
        updated = 0
        skipped = 0
        updated_files: list[str] = []

        for adr_file in ADR_DIR.glob("ADR-*.md"):
            content = self.read_file_safely(adr_file)
            if not content:
                skipped += 1
                continue

            m, fm_text, body_idx = self._match_frontmatter_block(content)
            if not m:
                print(f"Warning: No frontmatter block in {adr_file.name}")
                skipped += 1
                continue

            try:
                fm_data = yaml.safe_load(fm_text) or {}
            except Exception as e:
                print(f"Warning: Failed to parse frontmatter in {adr_file.name}: {e}")
                skipped += 1
                continue

            if fm_data.get("decision"):
                skipped += 1
                continue

            # Generate and normalize decision from full content
            decision_raw = self.extract_decision_from_body(content)
            decision = self._normalize_decision(decision_raw)

            # Build new frontmatter preserving order and inserting decision
            new_fm = self._insert_decision_into_frontmatter(fm_data, decision)

            # Reconstruct file contents
            new_fm_text = yaml.safe_dump(new_fm, sort_keys=False).strip()
            rest = content[body_idx:]
            new_content = f"---\n{new_fm_text}\n---\n{rest}"

            try:
                Path(adr_file).write_text(new_content, encoding="utf-8")
                updated += 1
                updated_files.append(str(adr_file))
            except Exception as e:
                print(f"Warning: Could not write {adr_file}: {e}")
                skipped += 1

        return updated, skipped, updated_files

    def collect_adr_records(self):
        """Collect all ADR records using only frontmatter data"""
        records = []
        display_fields = self.record_config.get("display_fields", [])

        for adr_file in ADR_DIR.glob("ADR-*.md"):
            content = self.read_file_safely(adr_file)
            if not content:
                continue

            # Extract frontmatter (validated by field processors)
            frontmatter = self.extract_frontmatter(content)
            if not frontmatter:
                print(f"Warning: No frontmatter found in {adr_file.name}")
                continue

            # Fill decision field from body if configured/displayed and missing
            if "decision" in display_fields and not frontmatter.get("decision"):
                frontmatter["decision"] = self.extract_decision_from_body(content)

            # Build record using only configured display fields
            record = self.build_record(adr_file, frontmatter, display_fields)
            if record:
                records.append(record)

        return records

    def build_record(self, adr_file, frontmatter, display_fields):
        """Build a single ADR record from frontmatter data"""
        # Derive file paths relative to the base config dir if possible
        try:
            rel = str(adr_file.relative_to(CONFIG_DIR))
        except ValueError:
            rel = str(adr_file)
        record = {
            "file_path": rel,
            "absolute_path": str(adr_file),
        }

        # Add configured display fields
        for field_name in display_fields:
            if field_name in self.field_configs:
                field_config = self.field_configs[field_name]
                raw_value = frontmatter.get(field_name)

                if raw_value is None:
                    record[field_name] = field_config.get("default", "")
                elif isinstance(raw_value, list):
                    if not raw_value:
                        record[field_name] = field_config.get("default", "")
                    else:
                        # Prefer rendering.record.fields.<name>.separator if present
                        separator = (
                            self.record_field_display.get(field_name, {}).get("separator", ", ")
                        )
                        record[field_name] = separator.join(str(item) for item in raw_value)
                else:
                    record[field_name] = str(raw_value)
            else:
                # Direct pass-through for unconfigured fields
                record[field_name] = frontmatter.get(field_name, "")

        return record

    def render_json(self, records):
        """Render records as JSON"""
        json_config = (
            self.record_config.get("json", {})
            or self.rendering_config.get("json", {})
        )
        output = {
            "generated_utc": datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z"),
            "total_records": len(records),
            "records": records,
        }
        indent = int(json_config.get("indent_spaces", 2))
        if json_config.get("sort_keys", False):
            return json.dumps(output, indent=indent, ensure_ascii=False, sort_keys=True)
        return json.dumps(output, indent=indent, ensure_ascii=False)

    def render_markdown(self, records):
        """Render records as Markdown using configuration"""
        md_config = (
            self.record_config.get("md", {})
            or self.rendering_config.get("markdown", {})
        )
        lines = []

        # Header
        header_template = md_config.get("header_template", "# Governance Index (autogenerated)")
        timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%S")
        lines.append(header_template)
        lines.append(f"\n_Generated (UTC): {timestamp}_\n")

        # Statistics if configured
        if md_config.get("include_statistics", True):
            lines.extend(self.render_statistics(records))

        # Hot rules if configured
        if md_config.get("include_hot_rules", True):
            lines.extend(self.render_hot_rules())

        # Records by status
        lines.extend(self.render_records_by_status(records, md_config))

        return "\n".join(lines)

    def render_statistics(self, records):
        """Render statistics section"""
        stats_config = self.rendering_config.get("statistics", {})
        if not stats_config.get("enabled", True):
            return []

        lines = ["## Index Statistics"]
        lines.append(f"**Total ADRs**: {len(records)}")

        # Count by status
        status_counts = {}
        for record in records:
            status = record.get("status", "Draft")
            status_counts[status] = status_counts.get(status, 0) + 1

        active_statuses = stats_config.get("active_statuses", ["Accepted", "Proposed"])
        deprecated_statuses = stats_config.get("deprecated_statuses", ["Superseded"])

        active_count = sum(status_counts.get(s, 0) for s in active_statuses)
        deprecated_count = sum(status_counts.get(s, 0) for s in deprecated_statuses)

        lines.append(f"**Active ADRs**: {active_count}")
        lines.append(f"**Deprecated ADRs**: {deprecated_count}")
        lines.append("")
        lines.append("**By Status**:")

        for status in sorted(status_counts.keys()):
            lines.append(f"- **{status}**: {status_counts[status]}")

        lines.append("")
        return lines

    def render_hot_rules(self):
        """Render hot rules section"""
        hot_rules_config = self.rendering_config.get("hot_rules", {})
        if not hot_rules_config.get("enabled", True):
            return []

        lines = ["## Critical Governance Rules"]
        lines.append("")
        lines.append("**AI agents and tools must honor these hot rules:**")
        lines.append("")

        # Use configured rules or defaults
        rules = hot_rules_config.get(
            "rules",
            hot_rules_config.get(
                "default_rules",
                [
                    "ADR-0024: Single canonical config mount → `/config` only; no dual SMB mounts.",
                    "ADR-0022: Mount management via LaunchAgent; preflight before writes.",
                    "ADR-0018: Workspace lifecycle policies with backup patterns and hygiene.",
                    "Path contracts: prefer container paths over host aliases; avoid `/Volumes/...` in tooling.",
                ],
            ),
        )

        for rule in rules:
            lines.append(f"- {rule}")

        lines.append("")
        lines.append("---")
        lines.append("")
        return lines

    def render_records_by_status(self, records, md_config):
        """Render records grouped by status"""
        lines = ["## ADR Catalog"]
        lines.append("")

        # Group by status
        status_groups = {}
        # New schema: list of groups with names and statuses
        configured_groups = md_config.get("status_groups", [])
        status_order = [g.get("name") for g in configured_groups] if configured_groups else [
            "Active ADRs", "Proposed ADRs", "Draft ADRs", "Superseded ADRs"
        ]

        for record in records:
            status = record.get("status", "Draft")

            # Map to display groups by configured statuses, else fallback
            group = None
            for g in configured_groups:
                if status in g.get("statuses", []):
                    group = g.get("name")
                    break
            if not group:
                if status in ["Accepted", "Implemented"]:
                    group = "Active ADRs"
                elif status in ["Proposed"]:
                    group = "Proposed ADRs"
                elif status in ["Draft", "Pending"]:
                    group = "Draft ADRs"
                elif status in ["Superseded", "Deprecated"]:
                    group = "Superseded ADRs"
                else:
                    group = f"{status} ADRs"

            if group not in status_groups:
                status_groups[group] = []
            status_groups[group].append(record)

        # Render each group
        for group in status_order:
            if group in status_groups and status_groups[group]:
                lines.append(f"### {group}")
                lines.append("")

                for record in sorted(status_groups[group], key=lambda r: r.get("id", "")):
                    lines.extend(self.render_single_record(record, md_config))

                lines.append("")

        return lines

    def render_single_record(self, record, md_config):
        """Render a single ADR record"""
        lines = []

        # Title line with status
        title = record.get("title", "Untitled")
        status = record.get("status", "Draft")
        file_path = record.get("file_path", "")

        lines.append(f"- **{title}** _{status}_")
        lines.append(f"  `{file_path}`")

        # Optional fields based on configuration
        if record.get("date") and md_config.get("show_date", True):
            lines.append(f"  Date: {record['date']}")

        if record.get("decision") and md_config.get("show_decision", True):
            decision = record["decision"]
            if len(decision) > 100:
                decision = decision[:97] + "..."
            lines.append(f"  Decision: {decision}")

        if record.get("related") and md_config.get("show_related", True):
            lines.append(f"  References: {record['related']}")

        if record.get("supersedes") and md_config.get("show_supersedes", True):
            lines.append(f"  Supersedes: {record['supersedes']}")

        return lines


def main():
    """Main entry point - pure configuration-driven rendering"""
    import argparse

    parser = argparse.ArgumentParser(description="Generate ADR governance index")
    parser.add_argument(
        "--format", choices=["json", "markdown"], default="markdown", help="Output format"
    )
    parser.add_argument(
        "--output", help="Output file path (default: .workspace/governance_index.md)"
    )
    parser.add_argument(
        "--autofill-decisions",
        action="store_true",
        help="Scan ADRs and insert generated 'decision' into frontmatter where missing",
    )
    args = parser.parse_args()

    try:
        # Initialize renderer
        renderer = ADRIndexRenderer()

        # Optional: autofill decisions and exit
        if args.autofill_decisions:
            updated, skipped, updated_files = renderer.autofill_decisions()
            print(
                json.dumps(
                    {
                        "updated": updated,
                        "skipped": skipped,
                        "updated_files": updated_files,
                    },
                    indent=2,
                ),
                file=sys.stderr,
            )
            return

        # Collect records using configuration (render mode)
        records = renderer.collect_adr_records()

        # Generate output using configuration
        if args.format == "json":
            output = renderer.render_json(records)
            # Prefer configured output path if available
            out_files = renderer.rendering_config.get("output_files", [])
            json_out = next(
                (Path(o.get("path")) for o in out_files if o.get("format") == "json"),
                OUTPUT_DIR / "governance_index.json",
            )
            default_output = json_out
        else:
            output = renderer.render_markdown(records)
            out_files = renderer.rendering_config.get("output_files", [])
            md_out = next(
                (Path(o.get("path")) for o in out_files if o.get("format") == "markdown"),
                OUTPUT_DIR / "governance_index.md",
            )
            default_output = md_out

        # Write output
        output_path = Path(args.output) if args.output else default_output
        output_path.parent.mkdir(exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
        print(f"Index written to {output_path}", file=sys.stderr)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


# Legacy functions removed - functionality moved to ADRIndexRenderer class


# Legacy function removed - hot rules now configuration-driven


# Legacy scan_adrs function removed - record collection now handled by ADRIndexRenderer.collect_adr_records()


# Legacy generate_index function removed - functionality moved to ADRIndexRenderer class


# Legacy generate_markdown_index function removed - functionality moved to ADRIndexRenderer.render_markdown()


if __name__ == "__main__":
    main()
