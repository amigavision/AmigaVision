-include .env
export
.DEFAULT_GOAL := default
.PHONY: default help env env-rm update updates pull-archives import-notwhdl-demos initial-downloads index index-add-missing prune-missing-archives manifests missing-manifests verify-manifests prune-manifests prune-manifests-apply sync-manifests sync-manifests-apply promote-newer-archives missing-images fetch-images fetch-images-interactive convert-images sync-images listings sqlite csv screenshots invalidate-build-cache prepare-image-temp image image-amiberry clone-amiberry mini-image test-image test-dry pi cd32 distros make-distros mister emulators mini amiga amiga-ecs pistorm pistorm-ecs clean clean-temp clean-build

PYTHON ?= python3.11
PIP_BUILD_CONSTRAINT ?= $(CURDIR)/build/pip-build-constraints.txt
export PIP_BUILD_CONSTRAINT
SOURCE ?= $(subst ",,${AVSCONTENT})/titles/manual-downloads
ARCHIVE_FETCH_DEST ?= ${AVSCONTENT}

AMIBERRYBIN ?= /Applications/Amiberry.app/Contents/MacOS/Amiberry
REPLAYOS_BASE_IMG ?= $(subst ",,${AVSCONTENT})/replay
REPLAYOS_OUTPUT_IMG ?= $(subst ",,${DISTRO_OUT})/AmigaVision-RPi-$(DISTRO_DATE).img
REPLAYOS_COMPRESSED_IMG ?= $(subst ",,${REPLAYOS_OUTPUT_IMG}).xz
REPLAYOS_IMG_SIZE ?= 14900m
REPLAYOS_BIOS_DIR ?= $(subst ",,${AVSCONTENT})/replay/bios
AMIGAVISION_HDF ?= ${AVSDEST}/AmigaVision.hdf
# Experimental native-chipset Emu68 image; classic PiStorm uses the ECS HDF.
PISTORM_MODEL ?= pistorm32lite
PISTORM_HDF ?= $(if $(filter pistorm,$(PISTORM_MODEL)),$(ECS_HDF),$(AMIGAVISION_HDF))
PISTORM_ROM ?= $(KICKSTART_ROM)
PISTORM_OUTPUT ?=
ECS_HDF ?= ${AVSDEST}/AmigaVision-ECS.hdf
EMULATORS_ARCHIVE ?= auto
WINDOWS_INSTALLER ?=
DISTRO_DATE ?= $(shell date +%Y.%m.%d)
DISTRO_OUT ?= ${AVSDEST}/distros
FAT32_MAX_FILE_BYTES ?= 4294967295
DISTRO_SAVES_HDF ?= ${AVSCONTENT}/distro/games/Amiga/AmigaVision-Saves.hdf
DISTRO_ROM ?= ${AVSCONTENT}/distro/games/Amiga/AmigaVision.rom
DISTRO_SHARED_DIR ?= ${AVSCONTENT}/distro/games/Amiga/shared
DISTRO_VISUALS_DIR ?= ${AVSCONTENT}/distro/games/Amiga/Visuals
DISTRO_LISTINGS_DIR ?= ${AVSDEST}/listings
MINI_HDF ?= ${AVSDEST}/AmigaVision-Mini.hdf
MINI_UAE ?= ${AVSDEST}/AmigaVision-Mini.uae
# Rare ECS builds default to full rebuilds with no retained build caches.
ECS_INCREMENTAL ?= 0
ECS_KEEP_CACHE ?= $(ECS_INCREMENTAL)
ECS_IMAGE_UPDATE_ARGS = $(filter-out --incremental,$(IMAGE_UPDATE_ARGS)) $(if $(filter 1,$(ECS_INCREMENTAL)),--incremental)
ECS_TEMP ?= $(subst ",,${AVSTEMP})-ECS
MINI_DISTRO_DIR ?= ./content/distro_mini
MISTER_DISTRO_DIR ?= ${AVSCONTENT}/distro
CD32_DISTRO_DIR ?= ./cd32
DISTRO_PACKAGE = $(PYTHON) build/package_distros.py --date-stamp "$(DISTRO_DATE)" --output-dir "$(subst ",,${DISTRO_OUT})" --mister-root "$(subst ",,${MISTER_DISTRO_DIR})" --cd32-root "$(subst ",,${CD32_DISTRO_DIR})" --main-hdf "$(subst ",,${AMIGAVISION_HDF})" --ecs-hdf "$(subst ",,${ECS_HDF})" --saves-hdf "$(subst ",,${DISTRO_SAVES_HDF})" --rom-file "$(subst ",,${DISTRO_ROM})" --listings-dir "$(subst ",,${DISTRO_LISTINGS_DIR})" --shared-dir "$(subst ",,${DISTRO_SHARED_DIR})" --visuals-dir "$(subst ",,${DISTRO_VISUALS_DIR})" --mini-root "$(subst ",,${MINI_DISTRO_DIR})" --mini-hdf "$(subst ",,${MINI_HDF})" --mini-uae "$(subst ",,${MINI_UAE})" --pi-script "build/pi_image.sh" $(if $(WINDOWS_INSTALLER),--windows-installer "$(subst ",,${WINDOWS_INSTALLER})")
DISTRO_PACKAGE_PROMPT = bash build/run_distros.sh --output-dir "$(subst ",,${DISTRO_OUT})" --mister-root "$(subst ",,${MISTER_DISTRO_DIR})" --cd32-root "$(subst ",,${CD32_DISTRO_DIR})" --main-hdf "$(subst ",,${AMIGAVISION_HDF})" --ecs-hdf "$(subst ",,${ECS_HDF})" --saves-hdf "$(subst ",,${DISTRO_SAVES_HDF})" --rom-file "$(subst ",,${DISTRO_ROM})" --listings-dir "$(subst ",,${DISTRO_LISTINGS_DIR})" --shared-dir "$(subst ",,${DISTRO_SHARED_DIR})" --visuals-dir "$(subst ",,${DISTRO_VISUALS_DIR})" --mini-root "$(subst ",,${MINI_DISTRO_DIR})" --mini-hdf "$(subst ",,${MINI_HDF})" --mini-uae "$(subst ",,${MINI_UAE})" --pi-script "build/pi_image.sh" $(if $(WINDOWS_INSTALLER),--windows-installer "$(subst ",,${WINDOWS_INSTALLER})")
MINI_FAT32_WARN = $(PYTHON) -c 'import os, sys; path = sys.argv[1]; limit = int(sys.argv[2]); exists = os.path.isfile(path); size = os.path.getsize(path) if exists else 0; gib = size / (1024 ** 3) if exists else 0.0; limit_gib = limit / (1024 ** 3); status = "WARNING" if exists and size > limit else "OK"; msg = f"{status}: Mini HDF size is {size} bytes ({gib:.2f} GiB); FAT32 limit is {limit} bytes ({limit_gib:.2f} GiB)." if exists else f"WARNING: Mini HDF not found at {path}"; print(msg)' "$(subst ",,${MINI_HDF})" "$(FAT32_MAX_FILE_BYTES)"

define print-start-time
	@printf 'Start time: %s\n' "$$(date '+%Y-%m-%d %H:%M:%S')"
endef

# Amiberry is the image cloner; *-amiberry targets are explicit aliases.

default: help

# Optional source override; the native AV-Base checkout is the default.
IMAGE_UPDATE_ARGS ?= --incremental
IMAGE_CLONE_ARGS ?=
BASE_IMAGE_ARGS ?=
IMAGE_PREP_CMD = pipenv run build/avs_imager.py $(IMAGE_UPDATE_ARGS) $(BASE_IMAGE_ARGS) -c configs/AmigaVision.yaml --all-games --all-demoscene -d ${AVSCONTENT}/extra_dirs/Music::DH1:Music -o ${AVSDEST}
MINI_IMAGE_PREP_CMD = pipenv run build/avs_imager.py --image-size-bytes 0 --boot-extra-bytes 0 $(IMAGE_UPDATE_ARGS) $(BASE_IMAGE_ARGS) -c configs/AmigaVision-Mini.yaml --auto-lists -d "$(subst ",,${AVSCONTENT})/extra_dirs/LessMusic::DH1:Music" -o "$(subst ",,${AVSDEST})" --temp-dir "$(subst ",,${AVSTEMP})"
TEST_IMAGE_PREP_CMD = pipenv run build/avs_imager.py $(IMAGE_UPDATE_ARGS) $(BASE_IMAGE_ARGS) -c configs/Test.yaml --auto-lists -o ${AVSDEST}
TEST_DRY_PREP_CMD = pipenv run build/avs_imager.py $(IMAGE_UPDATE_ARGS) $(BASE_IMAGE_ARGS) -c configs/Test.yaml --only-avs-tree --auto-lists -o ${AVSDEST}
ECS_IMAGE_PREP_CMD = pipenv run build/avs_imager.py $(ECS_IMAGE_UPDATE_ARGS) $(BASE_IMAGE_ARGS) -c configs/AmigaVision-ECS.yaml --chipset-profile ecs --temp-dir "$(ECS_TEMP)" --all-games --all-demoscene -d ${AVSCONTENT}/extra_dirs/Music::DH1:Music -o ${AVSDEST}
MAKE_MANIFESTS_CMD = pipenv run build/avs_index.py --make-manifests --only-missing
MAKE_LISTINGS_CMD = $(PYTHON) build/generate_listings.py "$(subst ",,${AVSTEMP})/DH1/AVS" "$(subst ",,${DISTRO_LISTINGS_DIR})"
FINALIZE_MAIN_IMAGE = test -f "$(subst ",,${AMIGAVISION_HDF})"

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
		'Create or incrementally update AmigaVision.hdf using Amiberry. Use IMAGE_CLONE_ARGS=--full to force a complete rebuild.' \
		'' \
		'make distros' \
		'Prompt once for the release version and output directory, then build all distribution artifacts unattended.' \
		'' \
		'Other useful targets:' \
		'' \
		'make ecs-artwork' \
		'Pre-render changed ECS thumbnails from the existing high-resolution IFF masters, without dithering.' \
		'' \
		'make ecs-dry / make ecs-image' \
		'Build the shared ECS menu or AmigaVision-ECS.hdf using one hi-res interlaced 16-color launcher and a separate workspace.' \
		'' \
		'make backfill-ecs-archives / make backfill-ecs-metadata / make backfill-ecs-metadata-apply' \
		'Backfill non-AGA WHDLoad archives (excluding JST), preview metadata imports, or apply confirmed redundant variants.' \
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
		'Index canonical WHDLoad archives in the $$AVSCONTENT path, update database references, and write the resulting state back to data/db/titles.csv.' \
		'' \
		'make index-add-missing' \
		'Run indexing, write the current SQLite state back to data/db/titles.csv, and then append or backfill missing fields using the current canonical metadata already present in the project.' \
		'' \
		'make prune-missing-archives' \
		'Clear archive/slave references in the database for rows whose archive_path no longer exists in the titles tree, then write the result back to data/db/titles.csv.' \
		'' \
		'make manifests' \
		'Regenerate all archive manifests under $$AVSCONTENT/manifests.' \
		'' \
		'make missing-manifests' \
		'Generate manifests only for archives that do not already have one.' \
		'' \
		'make verify-manifests' \
		'Verify .lha archive contents against the manifests in $$AVSCONTENT/manifests.' \
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
		'Promote newer .lha archives from the $${AVSCONTENT}/titles/manual-downloads directory into the canonical tree.' \
		'' \
		'make missing-images' \
		'Print how many titles still lack low-res screenshots.' \
		'' \
		'make sync-images' \
		'Preferred image pipeline. Import matching PNGs from data/img_highres/Unprocessed/, fetch missing demo screenshots from Demozoo, Pouet, and Exotica, fetch missing game screenshots from Lemon Amiga in Chrome, then try HoL in Chrome for remaining HoL-linked games, convert staged images into canonical low-res and high-res IFF screenshots, and print the remaining missing count.' \
		'' \
		'make listings' \
		'Generate games.txt and demos.txt from the current AVS temp tree for distro packaging.' \
		'' \
		'make pi' \
		'Build the Raspberry Pi / RePlayOS package from the configured base image and output an .img.xz sized to fit typical 16GB SD cards.' \
		'' \
		'make amiga' \
		'Package the real-Amiga hardware release artifact from the built image.' \
		'' \
		'make amiga-ecs' \
		'Package the built ECS image as .img.xz for Raspberry Pi Imager.' \
		'' \
		'make pistorm' \
		'Experimental PiStorm32-lite image from the built AGA HDF.' \
		'' \
		'make pistorm-ecs' \
		'Experimental classic PiStorm image from the built ECS HDF.' \
		'' \
		'make emulators' \
		'Package the reusable Amiberry and WinUAE emulator distribution.' \
		'' \
		'make mini' \
		'Package the A500 Mini release artifact from the built Mini image.' \
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
	@pipenv run build/avs_index.py -v --ingest
	@pipenv run python build/sync_missing_images.py --include-missing-highres --fetch-lemon-interactive --apply
	@pipenv run python build/promote_newer_archives.py --report-pending "$(SOURCE)"

updates: update

pull-archives:
	$(call print-start-time)
	@pipenv run python build/pull_archives.py --dest "$(SOURCE)"

# Full historical backfill; intentionally does not advance normal pull history.
.PHONY: backfill-ecs-archives backfill-ecs-metadata backfill-ecs-metadata-apply
backfill-ecs-archives:
	@pipenv run python build/pull_archives.py --backfill-non-aga --dest "$(SOURCE)/ecs-backfill"

backfill-ecs-metadata:
	@pipenv run python build/backfill_ecs_metadata.py --source "$(SOURCE)/ecs-backfill"

backfill-ecs-metadata-apply:
	@pipenv run python build/backfill_ecs_metadata.py --source "$(SOURCE)/ecs-backfill" --apply

import-notwhdl-demos:
	$(call print-start-time)
	@pipenv run python build/import_notwhdl_demos.py --source-root "$(SOURCE)" --apply

initial-downloads:
	$(call print-start-time)
	@pipenv run python build/fetch_archives_from_csv.py --dest "$(subst ",,${ARCHIVE_FETCH_DEST})"

index:
	$(call print-start-time)
	@pipenv run build/avs_index.py -v
	@pipenv run build/avs_index.py --make-csv

index-add-missing:
	$(call print-start-time)
	@pipenv run build/avs_index.py -v --append-missing-csv

prune-missing-archives:
	$(call print-start-time)
	@pipenv run build/avs_index.py -v --append-missing-csv --apply

manifests:
	$(call print-start-time)
	@pipenv run build/avs_index.py --make-manifests

missing-manifests:
	$(call print-start-time)
	@pipenv run build/avs_index.py --make-manifests --only-missing

verify-manifests:
	$(call print-start-time)
	@pipenv run build/avs_index.py --verify-manifests

prune-manifests:
	$(call print-start-time)
	@pipenv run build/avs_index.py --prune-manifests

prune-manifests-apply:
	$(call print-start-time)
	@pipenv run build/avs_index.py --prune-manifests --apply

sync-manifests:
	$(call print-start-time)
	@pipenv run build/avs_index.py --sync-manifests

sync-manifests-apply:
	$(call print-start-time)
	@pipenv run build/avs_index.py --sync-manifests --apply

promote-newer-archives:
	$(call print-start-time)
	@pipenv run python build/promote_newer_archives.py --apply "$(SOURCE)"

missing-images:
	$(call print-start-time)
	@pipenv run python build/sync_missing_images.py

sync-images:
	$(call print-start-time)
	@pipenv run python build/sync_missing_images.py --fetch-lemon-interactive --apply

listings:
	$(call print-start-time)
	@$(MAKE_LISTINGS_CMD)

sqlite:
	$(call print-start-time)
	@pipenv run build/avs_index.py -v --make-sqlite

csv:
	$(call print-start-time)
	@pipenv run build/avs_index.py -v --make-csv

screenshots:
	$(call print-start-time)
	@pipenv run build/make_screenshots.sh screenshots

invalidate-build-cache:
	$(call print-start-time)
	@$(PYTHON) build/invalidate_build_cache.py

prepare-image-temp:
	$(call print-start-time)
	@$(MAKE_MANIFESTS_CMD)
	@$(IMAGE_PREP_CMD)

image:
	$(call print-start-time)
	@$(MAKE_MANIFESTS_CMD)
	@$(IMAGE_PREP_CMD)
	@$(MAKE) clone-amiberry
	@$(FINALIZE_MAIN_IMAGE)
	@printf '\a'

.PHONY: ecs-artwork ecs-image ecs-dry
ecs-artwork:
	@pipenv run python build/ecs_artwork.py

ecs-dry: ecs-artwork
	@mkdir -p "$(ECS_TEMP)" "$(subst ",,${AVSDEST})"
	@AVSTEMP="$(ECS_TEMP)" AVSCACHEGEN=ecs $(ECS_IMAGE_PREP_CMD) --only-avs-tree

ecs-image: ecs-artwork
	@mkdir -p "$(ECS_TEMP)" "$(subst ",,${AVSDEST})"
	@$(MAKE_MANIFESTS_CMD)
	@AVSTEMP="$(ECS_TEMP)" AVSCACHEGEN=ecs $(ECS_IMAGE_PREP_CMD)
	@$(MAKE) clone-amiberry AVSTEMP="$(ECS_TEMP)"
	@test -f "$(subst ",,${AVSDEST})/AmigaVision-ECS.hdf"
	@echo "Removing completed ECS temp workspace..."
	@rm -rf "$(subst ",,$(ECS_TEMP))"
	@if [ "$(ECS_KEEP_CACHE)" != "1" ]; then \
		echo "Removing completed ECS build and image-update caches..."; \
		pipenv run python build/avs_image_update.py --clear-cache-for "$(subst ",,${AVSDEST})/AmigaVision-ECS.hdf" && \
		rm -rf "${HOME}/Library/Caches/AmigaVision/build/ecs"; \
	fi

clone-amiberry:
	$(call print-start-time)
	@echo "Running Amiberry..."
	@start=$$(date +%s); \
	if [ ! -d "$(subst ",,${AVSTEMP})" ]; then \
		echo "Preparing temp build tree..."; \
		$(MAKE) prepare-image-temp || exit $$?; \
	fi; \
	if [ ! -f "$(subst ",,${AVSTEMP})/cfg.uae" ]; then \
		echo "error: $(subst ",,${AVSTEMP})/cfg.uae not found after preparing the temp build tree."; \
		exit 1; \
	fi; \
	if [ ! -f "$(subst ",,${AVSTEMP})/clone" ]; then \
		echo "error: $(subst ",,${AVSTEMP})/clone not found after preparing the temp build tree."; \
		exit 1; \
	fi; \
	if [ ! -e "$(subst ",,${AVSTEMP})/target.hdf" ] && [ ! -f "$(subst ",,${AVSTEMP})/image-update-plan.json" ]; then \
		echo "error: $(subst ",,${AVSTEMP})/target.hdf not found after preparing the temp build tree."; \
		exit 1; \
	fi; \
	log="${AVSTEMP}/amiberry-image.log"; \
	if ! pipenv run python build/avs_image_update.py --workspace "$(subst ",,${AVSTEMP})" --emulator "${AMIBERRYBIN}" $(IMAGE_CLONE_ARGS) >"$$log" 2>&1; then \
		cat "$$log"; \
		exit 1; \
	fi; \
	end=$$(date +%s); \
	cat "$$log"; \
	elapsed=$$((end - start)); \
	if [ "$$elapsed" -lt 60 ]; then \
		printf 'Amiberry clone time: %ds\n' "$$elapsed"; \
	else \
		printf 'Amiberry clone time: %dm%02ds\n' "$$((elapsed / 60))" "$$((elapsed % 60))"; \
	fi
	@printf '\a'

image-amiberry:
	$(call print-start-time)
	@$(MAKE_MANIFESTS_CMD)
	@$(IMAGE_PREP_CMD)
	@$(MAKE) clone-amiberry
	@$(FINALIZE_MAIN_IMAGE)
	@printf '\a'

mini-image:
	$(call print-start-time)
	@$(MAKE_MANIFESTS_CMD)
	@$(MINI_IMAGE_PREP_CMD)
	@$(MAKE) clone-amiberry
	@$(MINI_FAT32_WARN)
	@printf '\a'

test-image:
	$(call print-start-time)
	@$(MAKE_MANIFESTS_CMD)
	@$(TEST_IMAGE_PREP_CMD)
	@$(MAKE) clone-amiberry
	@printf '\a'

test-dry:
	$(call print-start-time)
	@$(MAKE_MANIFESTS_CMD)
	@$(TEST_DRY_PREP_CMD)
	@printf '\a'

pi:
	$(call print-start-time)
	@$(DISTRO_PACKAGE_PROMPT) pi

cd32:
	$(call print-start-time)
	@$(DISTRO_PACKAGE_PROMPT) cd32-mister

distros:
	$(call print-start-time)
	@echo "Building all the distros will take around an hour on a MacBook M1."
	@$(DISTRO_PACKAGE_PROMPT) --build-all all

make-distros: distros

mister:
	$(call print-start-time)
	@$(MAKE_LISTINGS_CMD)
	@$(DISTRO_PACKAGE_PROMPT) mister

emulators:
	$(call print-start-time)
	@$(MAKE_LISTINGS_CMD)
	@$(DISTRO_PACKAGE_PROMPT) $(if $(filter 0,$(EMULATORS_ARCHIVE)),--skip-emulator-archive,$(if $(filter 1,$(EMULATORS_ARCHIVE)),--emulator-archive)) emulators

mini:
	$(call print-start-time)
	@$(DISTRO_PACKAGE_PROMPT) mini

amiga:
	$(call print-start-time)
	@$(DISTRO_PACKAGE_PROMPT) amiga

amiga-ecs:
	$(call print-start-time)
	@$(DISTRO_PACKAGE_PROMPT) amiga-ecs

clean-temp:
	$(call print-start-time)
	@echo "Removing main and ECS temp workspaces..."
	@rm -rf "$(subst ",,${AVSTEMP})" "$(subst ",,$(ECS_TEMP))"

clean-build:
	$(call print-start-time)
	@echo "Removing main and ECS temp workspaces, rotating current build cache, and clearing generated HDF outputs..."
	@rm -rf "$(subst ",,${AVSTEMP})" "$(subst ",,$(ECS_TEMP))"
	@cache_gen="$$(cat "${HOME}/Library/Caches/AmigaVision/build-cache-generation.txt" 2>/dev/null || echo current)"; \
	cache_dir="${HOME}/Library/Caches/AmigaVision/build/$$cache_gen"; \
	if [ -d "$$cache_dir" ]; then \
		trash_dir="$$cache_dir.trash.$$(date +%Y%m%d%H%M%S)"; \
		mv "$$cache_dir" "$$trash_dir"; \
		mkdir -p "$$cache_dir"; \
		nohup rm -rf "$$trash_dir" >/dev/null 2>&1 & \
		echo "Rotated build cache to $$trash_dir for background deletion."; \
	fi
	@rm -rf "$(subst ",,${AVSDEST})/AmigaVision-Mini"
	@rm -f "$(subst ",,${AVSDEST})/AmigaVision.hdf" \
		"$(subst ",,${AVSDEST})/AmigaVision-Mini.hdf" \
		"$(subst ",,${AVSDEST})/AmigaVision-Mini.uae"

# Keep experimental hardware images out of the normal release bundles.
pistorm-ecs: PISTORM_MODEL = pistorm
pistorm pistorm-ecs:
	$(call print-start-time)
	@pipenv run python build/pistorm_image.py --model "$(PISTORM_MODEL)" --hdf "$(subst ",,$(PISTORM_HDF))" --rom "$(subst ",,$(PISTORM_ROM))" --prompt --date-stamp "$(DISTRO_DATE)" --output-dir "$(subst ",,$(DISTRO_OUT))" $(if $(strip $(PISTORM_OUTPUT)),--output "$(subst ",,$(PISTORM_OUTPUT))") --amiberry "$(AMIBERRYBIN)"
