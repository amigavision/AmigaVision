-include .env
export
.DEFAULT_GOAL := default
.PHONY: default help env env-rm update updates pull-archives import-notwhdl-demos initial-downloads index index-add-missing prune-missing-archives manifests missing-manifests verify-manifests prune-manifests prune-manifests-apply sync-manifests sync-manifests-apply promote-newer-archives missing-images fetch-images fetch-images-interactive convert-images sync-images sqlite csv screenshots invalidate-build-cache prepare-image-temp image image-fsuae image-fuse clone-fsuae clone-fuse image-amiberry clone-amiberry pocket-image mini-image test-image test-dry pi pi-only cd32 distros make-distros mister emulators amiga clean clean-temp clean-build

PYTHON ?= python3.11
SOURCE ?= $(subst ",,${AGSCONTENT})/titles/manual-downloads
ARCHIVE_FETCH_DEST ?= ${HOME}/Developer/AmigaVision-Content

AMIBERRYBIN ?= /Applications/Amiberry.app/Contents/MacOS/Amiberry
REPLAYOS_BASE_IMG ?= $(subst ",,${AGSCONTENT})/replay
REPLAYOS_OUTPUT_IMG ?= $(subst ",,${DISTRO_OUT})/AmigaVision-RPi-$(DISTRO_DATE).img
REPLAYOS_COMPRESSED_IMG ?= $(subst ",,${REPLAYOS_OUTPUT_IMG}).xz
REPLAYOS_IMG_SIZE ?= 14900m
REPLAYOS_BIOS_DIR ?= $(subst ",,${AGSCONTENT})/replay/bios
AMIGAVISION_HDF ?= ${AGSDEST}/games/Amiga/AmigaVision.hdf
AMIGAVISION_UAE ?= content/distro/games/Amiga/default.uae
DISTRO_DATE ?= $(shell date +%Y.%m.%d)
DISTRO_OUT ?= ${AGSDEST}/distros
DISTRO_SAVES_HDF ?= ${AGSCONTENT}/distro/games/Amiga/AmigaVision-Saves.hdf
DISTRO_ROM ?= ${AGSCONTENT}/distro/games/Amiga/AmigaVision.rom
DISTRO_SHARED_DIR ?= ${AGSCONTENT}/distro/games/Amiga/shared
DISTRO_VISUALS_DIR ?= ${AGSCONTENT}/distro/games/Amiga/Visuals
DISTRO_LISTINGS_DIR ?= ${AGSDEST}/games/Amiga/listings
MISTER_DISTRO_DIR ?= ${AGSCONTENT}/distro
CD32_DISTRO_DIR ?= ./cd32
DISTRO_PACKAGE = $(PYTHON) build/package_distros.py --date-stamp "$(DISTRO_DATE)" --output-dir "$(subst ",,${DISTRO_OUT})" --mister-root "$(subst ",,${MISTER_DISTRO_DIR})" --cd32-root "$(subst ",,${CD32_DISTRO_DIR})" --main-hdf "$(subst ",,${AMIGAVISION_HDF})" --saves-hdf "$(subst ",,${DISTRO_SAVES_HDF})" --rom-file "$(subst ",,${DISTRO_ROM})" --listings-dir "$(subst ",,${DISTRO_LISTINGS_DIR})" --shared-dir "$(subst ",,${DISTRO_SHARED_DIR})" --visuals-dir "$(subst ",,${DISTRO_VISUALS_DIR})" --pi-script "build/pi_image.sh"
DISTRO_PACKAGE_PROMPT = bash build/run_distros.sh --output-dir "$(subst ",,${DISTRO_OUT})" --mister-root "$(subst ",,${MISTER_DISTRO_DIR})" --cd32-root "$(subst ",,${CD32_DISTRO_DIR})" --main-hdf "$(subst ",,${AMIGAVISION_HDF})" --saves-hdf "$(subst ",,${DISTRO_SAVES_HDF})" --rom-file "$(subst ",,${DISTRO_ROM})" --listings-dir "$(subst ",,${DISTRO_LISTINGS_DIR})" --shared-dir "$(subst ",,${DISTRO_SHARED_DIR})" --visuals-dir "$(subst ",,${DISTRO_VISUALS_DIR})" --pi-script "build/pi_image.sh"

define print-start-time
	@printf 'Start time: %s\n' "$$(date '+%Y-%m-%d %H:%M:%S')"
endef

# Clone backends:
# - `make image` uses Amiberry as the default final cloner backend.
# - `make image-fsuae` keeps the legacy FS-UAE final clone path available as a fallback.
# - `*-fuse` targets are opt-in experiments using macFUSE + amifuse and may
#   require reduced macOS startup security settings.
# - `*-amiberry` targets are kept as explicit aliases around the Amiberry backend.
# Keep these paths separate from the default build flow.

default: help

IMAGE_PREP_CMD = pipenv run build/ags_imager.py -c configs/AmigaVision.yaml --all-games --all-demoscene -d ${AGSCONTENT}/extra_dirs/Music::DH1:Music -o ${AGSDEST}
POCKET_IMAGE_PREP_CMD = pipenv run build/ags_imager.py -c configs/AmigaVision-Pocket.yaml --all-demos --auto-lists -d ${AGSCONTENT}/extra_dirs/LessMusic::DH1:Music -o ${AGSDEST}
MINI_IMAGE_PREP_CMD = pipenv run build/ags_imager.py -c configs/AmigaVision-Mini.yaml --all-demos --auto-lists -d ${AGSCONTENT}/extra_dirs/LessMusic::DH1:Music -o ${AGSDEST}
TEST_IMAGE_PREP_CMD = pipenv run build/ags_imager.py -c configs/Test.yaml --auto-lists -o ${AGSDEST}
TEST_DRY_PREP_CMD = pipenv run build/ags_imager.py -c configs/Test.yaml --only-ags-tree --auto-lists -o ${AGSDEST}
FINALIZE_MAIN_IMAGE = mkdir -p "$(subst ",,${AGSDEST})/games/Amiga" && mv "$(subst ",,${AGSDEST})/AmigaVision.hdf" "$(subst ",,${AGSDEST})/games/Amiga" && cp "$(subst ",,${AMIGAVISION_UAE})" "$(subst ",,${AGSDEST})/games/Amiga/"

help:
	@printf '%s\n' \
		'Available top-level make targets:' \
		'' \
		'Standard release flow:' \
		'make env' \
		'make update' \
		'make image' \
		'make distros' \
		'' \
		'make env' \
		'Set up the Python environment used by the build tools.' \
		'' \
		'make update' \
		'Pull archives from the configured source, promote newer manual-downloads archives into the canonical tree, re-index the content database, and run the preferred image sync pipeline.' \
		'' \
		'make image' \
		'Create the Amiga HDF image and filesystem specified in configs/AmigaVision.yaml using Amiberry as the final cloner.' \
		'' \
		'make distros' \
		'Prompt for the release date, then package all uploadable platform-specific release artifacts from the built image.' \
		'' \
		'Other useful targets:' \
		'' \
		'make updates' \
		'Alias for make update.' \
		'' \
		'make initial-downloads [ARCHIVE_FETCH_DEST=...]' \
		'Download the demo/game/mags archive paths currently listed in data/db/titles.csv into a local content tree, skipping files already present. Useful for initial contributor setup.' \
		'' \
		'make import-notwhdl-demos [SOURCE=...]' \
		'Import repacked non-WHDLoad demo archives from manual-downloads into demo-notwhdl, generate .run launchers, and enrich titles.csv with online Pouet/Demozoo metadata where possible.' \
		'' \
		'make index' \
		'Index canonical WHDLoad archives in the $$AGSCONTENT path, update database references, and write the resulting state back to data/db/titles.csv.' \
		'' \
		'make index-add-missing' \
		'Run indexing, write the current SQLite state back to data/db/titles.csv, and then append or backfill missing fields in the CSV using an online Wikidata lookup.' \
		'' \
		'make prune-missing-archives' \
		'Clear archive/slave references in the database for rows whose archive_path no longer exists in the titles tree, then write the result back to data/db/titles.csv.' \
		'' \
		'make manifests' \
		'Regenerate all archive manifests under $$AGSCONTENT/manifests.' \
		'' \
		'make missing-manifests' \
		'Generate manifests only for archives that do not already have one.' \
		'' \
		'make verify-manifests' \
		'Verify .lha archive contents against the manifests in $$AGSCONTENT/manifests.' \
		'' \
		'make sync-manifests' \
		'Generate missing manifests and report stale manifests whose archive no longer exists.' \
		'' \
		'make sync-manifests-apply' \
		'Generate missing manifests and remove stale manifests.' \
		'' \
		'make prune-manifests' \
		'Report stale manifests without deleting them.' \
		'' \
		'make prune-manifests-apply' \
		'Remove stale manifests whose archive no longer exists.' \
		'' \
		'make promote-newer-archives [SOURCE=...]' \
		'Promote newer .lha archives from the $${AGSCONTENT}/titles/manual-downloads directory into the canonical tree.' \
		'' \
		'make missing-images' \
		'Print how many titles still lack low-res screenshots.' \
		'' \
		'make sync-images' \
		'Preferred image pipeline. Import matching PNGs from data/img_highres/Unprocessed/, fetch missing demo screenshots from Demozoo, Pouet, and Exotica, fetch missing game screenshots from Lemon Amiga in Chrome, then try HoL in Chrome for remaining HoL-linked games, then itch.io, convert staged images into canonical low-res and high-res IFF screenshots, and print the remaining missing count.' \
		'' \
		'make image-fsuae' \
		'Run the legacy FS-UAE final clone path for configs/AmigaVision.yaml.' \
		'' \
		'make pi' \
		'Build the Raspberry Pi / RePlayOS package from the configured base image and output an .img.xz sized to fit typical 16GB SD cards.' \
		'' \
		'make amiga' \
		'Package the real-Amiga hardware release artifact from the built image.' \
		'' \
		'make emulators' \
		'Package the reusable Amiberry-based emulator distribution.' \
		'' \
		'make mister' \
		'Package the MiSTer release artifact.' \
		'' \
		'make cd32' \
		'Generate the CD32 SD/USB/NAS payloads and build the CD32 MiSTer release artifact.' \
		'' \
		'make screenshots' \
		'Create scaled IFF images from arbitrary PNG files placed in screenshots.' \
		'' \
		'make sqlite' \
		'Create SQLite database from data/db/titles.csv (for easier viewing and editing).' \
		'' \
		'make csv' \
		'Output the contents of SQLite database to data/db/titles.csv (for committing to version control).'

env:
	$(call print-start-time)
	-@pipenv --rm
	-@pipenv --clear
	@pipenv --python "$$(command -v $(PYTHON) || command -v python3 || command -v python)"
	@pipenv install

env-rm:
	$(call print-start-time)
	-@pipenv -v --rm
	-@pipenv -v --clear

update:
	$(call print-start-time)
	@pipenv run python build/pull_archives.py --dest "$(SOURCE)"
	@pipenv run python build/import_notwhdl_demos.py --source-root "$(SOURCE)" --apply
	@pipenv run python build/promote_newer_archives.py --apply "$(SOURCE)"
	@pipenv run build/ags_index.py -v --ingest
	@pipenv run python build/sync_missing_images.py --fetch-lemon-interactive --apply

updates: update

pull-archives:
	$(call print-start-time)
	@pipenv run python build/pull_archives.py --dest "$(SOURCE)"

import-notwhdl-demos:
	$(call print-start-time)
	@pipenv run python build/import_notwhdl_demos.py --source-root "$(SOURCE)" --apply

initial-downloads:
	$(call print-start-time)
	@pipenv run python build/fetch_archives_from_csv.py --dest "$(subst ",,${ARCHIVE_FETCH_DEST})"

index:
	$(call print-start-time)
	@pipenv run build/ags_index.py -v
	@pipenv run build/ags_index.py --make-csv

index-add-missing:
	$(call print-start-time)
	@pipenv run build/ags_index.py -v --append-missing-csv

prune-missing-archives:
	$(call print-start-time)
	@pipenv run build/ags_index.py -v --append-missing-csv --apply

manifests:
	$(call print-start-time)
	@pipenv run build/ags_index.py --make-manifests

missing-manifests:
	$(call print-start-time)
	@pipenv run build/ags_index.py --make-manifests --only-missing

verify-manifests:
	$(call print-start-time)
	@pipenv run build/ags_index.py --verify-manifests

prune-manifests:
	$(call print-start-time)
	@pipenv run build/ags_index.py --prune-manifests

prune-manifests-apply:
	$(call print-start-time)
	@pipenv run build/ags_index.py --prune-manifests --apply

sync-manifests:
	$(call print-start-time)
	@pipenv run build/ags_index.py --sync-manifests

sync-manifests-apply:
	$(call print-start-time)
	@pipenv run build/ags_index.py --sync-manifests --apply

promote-newer-archives:
	$(call print-start-time)
	@pipenv run python build/promote_newer_archives.py --apply "$(SOURCE)"

missing-images:
	$(call print-start-time)
	@pipenv run python build/sync_missing_images.py

sync-images:
	$(call print-start-time)
	@pipenv run python build/sync_missing_images.py --fetch-lemon-interactive --apply

sqlite:
	$(call print-start-time)
	@pipenv run build/ags_index.py -v --make-sqlite

csv:
	$(call print-start-time)
	@pipenv run build/ags_index.py -v --make-csv

screenshots:
	$(call print-start-time)
	@pipenv run build/make_screenshots.sh screenshots

invalidate-build-cache:
	$(call print-start-time)
	@mkdir -p "${HOME}/Library/Caches/AmigaVision"
	@date +%Y%m%d%H%M%S > "${HOME}/Library/Caches/AmigaVision/build-cache-generation.txt"
	@echo "Build cache generation bumped to $$(cat "${HOME}/Library/Caches/AmigaVision/build-cache-generation.txt")"

prepare-image-temp:
	$(call print-start-time)
	@$(IMAGE_PREP_CMD)

clone-fsuae:
	$(call print-start-time)
	@echo "Running FS-UAE..."
	@start=$$(date +%s); \
	if [ ! -d "$(subst ",,${AGSTEMP})" ]; then \
		echo "Preparing temp build tree..."; \
		$(MAKE) prepare-image-temp || exit $$?; \
	fi; \
	if [ ! -f "$(subst ",,${AGSTEMP})/cfg.fs-uae" ]; then \
		echo "error: $(subst ",,${AGSTEMP})/cfg.fs-uae not found after preparing the temp build tree."; \
		exit 1; \
	fi; \
	if [ ! -e "$(subst ",,${AGSTEMP})/target.hdf" ]; then \
		echo "error: $(subst ",,${AGSTEMP})/target.hdf not found after preparing the temp build tree."; \
		exit 1; \
	fi; \
	log="${AGSTEMP}/fs-uae-image.log"; \
	if ! ${FSUAEBIN} ${AGSTEMP}/cfg.fs-uae >"$$log" 2>&1; then \
		cat "$$log"; \
		exit 1; \
	fi; \
	end=$$(date +%s); \
	echo "FS-UAE clone time: $$((end - start))s"

image:
	$(call print-start-time)
	@$(IMAGE_PREP_CMD)
	@$(MAKE) clone-amiberry
	@$(FINALIZE_MAIN_IMAGE)
	@printf '\a'

image-fsuae:
	$(call print-start-time)
	@$(IMAGE_PREP_CMD)
	@$(MAKE) clone-fsuae
	@$(FINALIZE_MAIN_IMAGE)
	@printf '\a'

clone-fuse:
	$(call print-start-time)
	@echo "Running amifuse..."
	@start=$$(date +%s); \
	if [ ! -d "$(subst ",,${AGSTEMP})" ]; then \
		echo "Preparing temp build tree..."; \
		$(MAKE) prepare-image-temp || exit $$?; \
	fi; \
	hdf="$(subst ",,${AGSDEST})/AmigaVision.hdf"; \
	if [ ! -f "$$hdf" ]; then \
		hdf="$(subst ",,${AMIGAVISION_HDF})"; \
	fi; \
	build/hdf_fuse_clone.sh \
		--hdf "$$hdf" \
		--src-root "$(subst ",,${AGSTEMP})" \
		--amifuse "${AMIFUSEBIN}" \
		--temp-root "$(subst ",,${AGSTEMP})"; \
	if [ -f "$(subst ",,${AGSDEST})/AmigaVision.hdf" ]; then \
		mv "$(subst ",,${AGSDEST})/AmigaVision.hdf" "$(subst ",,${AGSDEST})/games/Amiga"; \
	fi; \
	end=$$(date +%s); \
	echo "amifuse clone time: $$((end - start))s"
	@printf '\a'

image-fuse:
	$(call print-start-time)
	@$(IMAGE_PREP_CMD)
	@$(MAKE) clone-fuse

clone-amiberry:
	$(call print-start-time)
	@echo "Running Amiberry..."
	@start=$$(date +%s); \
	if [ ! -d "$(subst ",,${AGSTEMP})" ]; then \
		echo "Preparing temp build tree..."; \
		$(MAKE) prepare-image-temp || exit $$?; \
	fi; \
	if [ ! -f "$(subst ",,${AGSTEMP})/cfg.uae" ]; then \
		echo "error: $(subst ",,${AGSTEMP})/cfg.uae not found after preparing the temp build tree."; \
		exit 1; \
	fi; \
	if [ ! -f "$(subst ",,${AGSTEMP})/clone" ]; then \
		echo "error: $(subst ",,${AGSTEMP})/clone not found after preparing the temp build tree."; \
		exit 1; \
	fi; \
	if [ ! -e "$(subst ",,${AGSTEMP})/target.hdf" ]; then \
		echo "error: $(subst ",,${AGSTEMP})/target.hdf not found after preparing the temp build tree."; \
		exit 1; \
	fi; \
	log="${AGSTEMP}/amiberry-image.log"; \
	if ! "${AMIBERRYBIN}" -f "${AGSTEMP}/cfg.uae" --log >"$$log" 2>&1; then \
		cat "$$log"; \
		exit 1; \
	fi; \
	end=$$(date +%s); \
	echo "Amiberry clone time: $$((end - start))s"
	@printf '\a'

image-amiberry:
	$(call print-start-time)
	@$(IMAGE_PREP_CMD)
	@$(MAKE) clone-amiberry
	@$(FINALIZE_MAIN_IMAGE)
	@printf '\a'

pocket-image:
	$(call print-start-time)
	@$(POCKET_IMAGE_PREP_CMD)
	@$(MAKE) clone-amiberry
	@mv ${AGSDEST}/AmigaVision-Pocket.hdf ${AGSDEST}/AmigaVision-Pocket
	@printf '\a'

mini-image:
	$(call print-start-time)
	@$(MINI_IMAGE_PREP_CMD)
	@$(MAKE) clone-amiberry
	@mv ${AGSDEST}/AmigaVision-Mini.hdf ${AGSDEST}/AmigaVision-Mini
	@printf '\a'

test-image:
	$(call print-start-time)
	@$(TEST_IMAGE_PREP_CMD)
	@$(MAKE) clone-amiberry
	@printf '\a'

test-dry:
	$(call print-start-time)
	@$(TEST_DRY_PREP_CMD)
	@printf '\a'

pi:
	$(call print-start-time)
	@rm -f "${REPLAYOS_OUTPUT_IMG}" "${REPLAYOS_COMPRESSED_IMG}"
	@build/pi_image.sh \
		--hdf "${AMIGAVISION_HDF}" \
		--output-img "${REPLAYOS_OUTPUT_IMG}"
	@mkdir -p "$(dir ${REPLAYOS_COMPRESSED_IMG})"
	@rm -f "${REPLAYOS_COMPRESSED_IMG}"
	@xz -T0 -1 -v -k -c "${REPLAYOS_OUTPUT_IMG}" > "${REPLAYOS_COMPRESSED_IMG}"
	@rm -f "${REPLAYOS_OUTPUT_IMG}"
	@printf '\a'

pi-only: pi
	@:

cd32:
	$(call print-start-time)
	@PYTHONDONTWRITEBYTECODE=1 $(PYTHON) "$(subst ",,${CD32_DISTRO_DIR})/make_cd32_mgl_cfg.py" --quiet
	@mkdir -p "$(subst ",,${DISTRO_OUT})"
	@cd "$(subst ",,${CD32_DISTRO_DIR})" && bash ./pack "$(DISTRO_DATE)" "$(subst ",,${DISTRO_OUT})/!AmigaVision-CD32-MiSTer-$(DISTRO_DATE).zip"
	@printf '\a'

distros:
	$(call print-start-time)
	@echo "Building all the distros will take around an hour on a MacBook M1."
	@check_path="$(subst ",,${DISTRO_OUT})"; \
	while [ ! -d "$$check_path" ]; do \
		check_path="$$(dirname "$$check_path")"; \
	done; \
	free_kb="$$(df -Pk "$$check_path" | awk 'NR==2 {print $$4}')"; \
	if [ "$$free_kb" -lt 23068672 ]; then \
		echo "Building all the distros requires 22GB or more of free space."; \
		exit 1; \
	fi
	@$(DISTRO_PACKAGE_PROMPT) all

make-distros: distros

mister:
	$(call print-start-time)
	@$(DISTRO_PACKAGE_PROMPT) mister

emulators:
	$(call print-start-time)
	@$(DISTRO_PACKAGE_PROMPT) emulators

amiga:
	$(call print-start-time)
	@$(DISTRO_PACKAGE_PROMPT) amiga

clean-temp:
	$(call print-start-time)
	@echo "Removing temp workspace..."
	@rm -rf "$(subst ",,${AGSTEMP})"

clean-build:
	$(call print-start-time)
	@echo "Removing temp workspace, rotating current build cache, and clearing generated HDF outputs..."
	@rm -rf "$(subst ",,${AGSTEMP})"
	@cache_gen="$$(cat "${HOME}/Library/Caches/AmigaVision/build-cache-generation.txt" 2>/dev/null || echo current)"; \
	cache_dir="${HOME}/Library/Caches/AmigaVision/build/$$cache_gen"; \
	if [ -d "$$cache_dir" ]; then \
		trash_dir="$$cache_dir.trash.$$(date +%Y%m%d%H%M%S)"; \
		mv "$$cache_dir" "$$trash_dir"; \
		mkdir -p "$$cache_dir"; \
		nohup rm -rf "$$trash_dir" >/dev/null 2>&1 & \
		echo "Rotated build cache to $$trash_dir for background deletion."; \
	fi
	@rm -f "$(subst ",,${AGSDEST})/AmigaVision.hdf" \
		"$(subst ",,${AGSDEST})/games/Amiga/AmigaVision.hdf" \
		"$(subst ",,${AGSDEST})/AmigaVision-Pocket.hdf" \
		"$(subst ",,${AGSDEST})/AmigaVision-Mini.hdf"
