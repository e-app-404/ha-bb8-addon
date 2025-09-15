# Snapshot Makefile (standalone). Use: make -f scripts/snapshot.mk <target>

LOC_THRESHOLD ?= 2000
FILES_THRESHOLD ?= 80

.PHONY: snapshot-dry snapshot-auto snapshot-tarball snapshot-untracked

snapshot: snapshot-tarball

snapshot-dry:
	@LOC_THRESHOLD=$(LOC_THRESHOLD) FILES_THRESHOLD=$(FILES_THRESHOLD) \
	bash scripts/snapshot_policy.sh --dry-run

snapshot-auto:
	@LOC_THRESHOLD=$(LOC_THRESHOLD) FILES_THRESHOLD=$(FILES_THRESHOLD) \
	SNAPSHOT_AUTO=1 bash -c 'out=$$(bash scripts/snapshot_policy.sh --dry-run); echo "$$out"; \
		need=$$(echo "$$out" | jq -r .needs_snapshot); \
		if [ "$$need" = "true" ] || [ "$$need" = "1" ]; then \
			LOC_THRESHOLD=$(LOC_THRESHOLD) FILES_THRESHOLD=$(FILES_THRESHOLD) bash scripts/snapshot_policy.sh; \
		else echo "NO_SNAPSHOT_NEEDED"; fi'

snapshot-tarball:
	@LOC_THRESHOLD=$(LOC_THRESHOLD) FILES_THRESHOLD=$(FILES_THRESHOLD) \
	bash scripts/snapshot_policy.sh

snapshot-untracked:
	@TS=$$(date +%Y%m%d_%H%M%S); mkdir -p _backups/inventory; \
	git ls-files --others --exclude-standard | sort > "_backups/inventory/untracked_$${TS}.txt"; \
	echo "UNTRACKED_OK _backups/inventory/untracked_$${TS}.txt"
