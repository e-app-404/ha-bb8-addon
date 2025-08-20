# Restore add-on workspace to ./addon

This repo mirrors the live add-on source from your mounted path:

- Source: `/Volumes/addons/local/beep_boop_bb8/`
- Destination in repo: `./addon/` (exact historical location)

## Restore / Sync
```bash
bash scripts/restore_addon.sh
bash scripts/verify_addon.sh
```
