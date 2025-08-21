# Next Steps Checklist — 20250818_165309Z

- [ ] Apply patches (if any): `git apply reports/patches/20250818_165309Z/*.patch`
- [ ] Consolidate workspace: `python tools/consolidate_workspace.py --apply`
- [ ] Re-run addon audit (strict): `python tools/audit_addon_tree.py --strict --out reports/addon_audit_20250818_165309Z.json`
- [ ] Re-run import tests: `pytest -q tests/test_import_order_warning.py tests/test_imports_no_cycles.py --disable-warnings -q`
- [ ] Commit with message: `chore(audit): flip WARN→PASS; workspace & imports clean`
- [ ] Push to origin
