-include .env
export
.DEFAULT_GOAL := default
.PHONY: default help env env-rm update updates pull-archives index index-add-missing manifests missing-manifests verify-manifests prune-manifests prune-manifests-apply sync-manifests sync-manifests-apply promote-newer-archives missing-images fetch-images fetch-images-interactive convert-images sync-images sync-images-interactive sqlite csv screenshots invalidate-build-cache prepare-image-temp image image-fsuae image-fuse clone-fsuae clone-fuse image-hst clone-hst image-amiberry clone-amiberry pocket-image mini-image test-image test-dry pi pi-only distros distro-mister distro-cd32-mister distro-emulators distro-pi distro-amiga clean clean-temp clean-build

PYTHON ?= python3.11
SOURCE ?= ${AGSCONTENT}/titles/manual-downloads
AMIFUSEBIN ?= ${HOME}/Library/Caches/AmigaVision/amifuse-venv/bin/amifuse
HSTAMIGABIN ?= ${HOME}/Developer/hst-amiga/src/Hst.Amiga.Pfs.ConsoleApp/bin/Release/net8.0/osx-arm64/publish/hst-amiga-pfs
AMIBERRYBIN ?= /Applications/Amiberry.app/Contents/MacOS/Amiberry

REPLAYOS_BASE_IMG ?= ${AGSCONTENT}/base
REPLAYOS_OUTPUT_IMG ?= ${AGSDEST}/AmigaVision-RPi.img
REPLAYOS_IMG_SIZE ?= 16g
AMIGAVISION_HDF ?= ${AGSDEST}/games/Amiga/AmigaVision.hdf
DISTRO_DATE ?= $(shell date +%Y.%m.%d)
DISTRO_OUT ?= ${AGSDEST}/distros
DISTRO_SAVES_HDF ?= ${AGSCONTENT}/distro/games/Amiga/AmigaVision-Saves.hdf
DISTRO_SHARED_DIR ?= ${AGSCONTENT}/distro/games/Amiga/shared
DISTRO_LISTINGS_DIR ?= ${AGSDEST}/games/Amiga/listings
MISTER_DISTRO_DIR ?= ${AGSCONTENT}/distro
CD32_DISTRO_DIR ?= ./cd32
DISTRO_PACKAGE = $(PYTHON) ./build/package_distros.py --date-stamp "$(DISTRO_DATE)" --output-dir "$(subst ",,${DISTRO_OUT})" --mister-root "$(subst ",,${MISTER_DISTRO_DIR})" --cd32-root "$(subst ",,${CD32_DISTRO_DIR})" --main-hdf "$(subst ",,${AMIGAVISION_HDF})" --saves-hdf "$(subst ",,${DISTRO_SAVES_HDF})" --listings-dir "$(subst ",,${DISTRO_LISTINGS_DIR})" --shared-dir "$(subst ",,${DISTRO_SHARED_DIR})" --pi-script "./build/pi_image.sh" --replay-base-img "$(subst ",,${REPLAYOS_BASE_IMG})" --replay-payload-dir "./replay" --replay-size "$(REPLAYOS_IMG_SIZE)"
DISTRO_PACKAGE_PROMPT = bash ./build/run_distros.sh --output-dir "$(subst ",,${DISTRO_OUT})" --mister-root "$(subst ",,${MISTER_DISTRO_DIR})" --cd32-root "$(subst ",,${CD32_DISTRO_DIR})" --main-hdf "$(subst ",,${AMIGAVISION_HDF})" --saves-hdf "$(subst ",,${DISTRO_SAVES_HDF})" --listings-dir "$(subst ",,${DISTRO_LISTINGS_DIR})" --shared-dir "$(subst ",,${DISTRO_SHARED_DIR})" --pi-script "./build/pi_image.sh" --replay-base-img "$(subst ",,${REPLAYOS_BASE_IMG})" --replay-payload-dir "./replay" --replay-size "$(REPLAYOS_IMG_SIZE)"

define print-start-time
	@printf 'Start time: %s\n' "$$(date '+%Y-%m-%d %H:%M:%S')"
endef

# Clone backends:
# - `make image` uses Amiberry as the default final cloner backend.
# - `make image-fsuae` keeps the legacy FS-UAE final clone path available as a fallback.
# - `*-fuse` targets are opt-in experiments using macFUSE + amifuse and may
#   require reduced macOS startup security settings.
# - `*-hst` targets use FS-UAE only for `pfsformat`, then copy files directly
#   with hst-amiga-pfs on the host.
# - `*-amiberry` targets are kept as explicit aliases around the Amiberry backend.
# Keep these paths separate from the default build flow.

default: help

IMAGE_PREP_CMD = pipenv run ./build/ags_imager.py -v -c configs/AmigaVision.yaml --all-games --all-demoscene -d ${AGSCONTENT}/extra_dirs/Music::DH1:Music -o ${AGSDEST}

help:
	@printf '%s\n' \
		'Available top-level make targets:' \
		'' \
		'  make env' \
		'    Set up the Python environment used by the build tools.' \
		'' \
		'  make updates' \
		'    Alias for make update.' \
		'' \
		'  make update' \
		'    Pull archives from the configured source, promote newer manual-downloads archives into the canonical tree, re-index the content database, and run the preferred image sync pipeline.' \
		'' \
		'  make index' \
		'    Index canonical WHDLoad archives in the $$AGSCONTENT path, update database references, and write the resulting state back to data/db/titles.csv.' \
		'' \
		'  make index-add-missing' \
		'    Run indexing, write the current SQLite state back to data/db/titles.csv, and then append or backfill missing fields in the CSV using an online Wikidata lookup.' \
		'' \
		'  make manifests' \
		'    Regenerate all archive manifests under $$AGSCONTENT/manifests.' \
		'' \
		'  make missing-manifests' \
		'    Generate manifests only for archives that do not already have one.' \
		'' \
		'  make verify-manifests' \
		'    Verify .lha archive contents against the manifests in $$AGSCONTENT/manifests.' \
		'' \
		'  make sync-manifests' \
		'    Generate missing manifests and report stale manifests whose archive no longer exists.' \
		'' \
		'  make sync-manifests-apply' \
		'    Generate missing manifests and remove stale manifests.' \
		'' \
		'  make prune-manifests' \
		'    Report stale manifests without deleting them.' \
		'' \
		'  make prune-manifests-apply' \
		'    Remove stale manifests whose archive no longer exists.' \
		'' \
		'  make promote-newer-archives [SOURCE=...]' \
		'    Promote newer .lha archives from the $${AGSCONTENT}/titles/manual-downloads directory into the canonical tree.' \
		'' \
		'  make missing-images' \
		'    Print how many titles still lack low-res screenshots.' \
		'' \
		'  make sync-images' \
		'    Preferred image pipeline. Import matching PNGs from data/img_highres/Unprocessed/, fetch missing demo screenshots from Demozoo, Pouet, and Exotica, fetch missing game screenshots from Lemon Amiga in Chrome and then itch.io, convert staged images into canonical low-res and high-res IFF screenshots, and print the remaining missing count.' \
		'' \
		'  make sync-images-interactive' \
		'    Alias for make sync-images.' \
		'' \
		'  make image' \
		'    Create the Amiga HDF image and filesystem specified in configs/AmigaVision.yaml using Amiberry as the final cloner.' \
		'' \
		'  make image-fsuae' \
		'    Run the legacy FS-UAE final clone path for configs/AmigaVision.yaml.' \
		'' \
		'  make pi' \
		'    Build AmigaVision.hdf, inject it and replay/ payload into a RePlayOS base image, and output a 16GB flashable .img.' \
		'' \
		'  make distros' \
		'    Prompt for the release date, then package all uploadable platform-specific release artifacts from the built image.' \
		'' \
		'  make screenshots' \
		'    Create scaled IFF images from arbitrary PNG files placed in screenshots.' \
		'' \
		'  make sqlite' \
		'    Create SQLite database from data/db/titles.csv (for easier viewing and editing).' \
		'' \
		'  make csv' \
		'    Output the contents of SQLite database to data/db/titles.csv (for committing to version control).'

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
	@pipenv run python ./build/pull_archives.py --dest "$(SOURCE)"
	@pipenv run python ./build/promote_newer_archives.py --apply "$(SOURCE)"
	@pipenv run ./build/ags_index.py -v --ingest
	@pipenv run python ./build/sync_missing_images.py --fetch-lemon-interactive --apply

updates: update

pull-archives:
	$(call print-start-time)
	@pipenv run python ./build/pull_archives.py --dest "$(SOURCE)"

index:
	$(call print-start-time)
	@pipenv run ./build/ags_index.py -v
	@pipenv run ./build/ags_index.py --make-csv

index-add-missing:
	$(call print-start-time)
	@pipenv run ./build/ags_index.py -v --append-missing-csv

manifests:
	$(call print-start-time)
	@pipenv run ./build/ags_index.py --make-manifests

missing-manifests:
	$(call print-start-time)
	@pipenv run ./build/ags_index.py --make-manifests --only-missing

verify-manifests:
	$(call print-start-time)
	@pipenv run ./build/ags_index.py --verify-manifests

prune-manifests:
	$(call print-start-time)
	@pipenv run ./build/ags_index.py --prune-manifests

prune-manifests-apply:
	$(call print-start-time)
	@pipenv run ./build/ags_index.py --prune-manifests --apply

sync-manifests:
	$(call print-start-time)
	@pipenv run ./build/ags_index.py --sync-manifests

sync-manifests-apply:
	$(call print-start-time)
	@pipenv run ./build/ags_index.py --sync-manifests --apply

promote-newer-archives:
	$(call print-start-time)
	@pipenv run python ./build/promote_newer_archives.py --apply "$(SOURCE)"

missing-images:
	$(call print-start-time)
	@pipenv run python ./build/sync_missing_images.py

sync-images:
	$(call print-start-time)
	@pipenv run python ./build/sync_missing_images.py --fetch-lemon-interactive --apply

sync-images-interactive:
	$(call print-start-time)
	@pipenv run python ./build/sync_missing_images.py --fetch-lemon-interactive --apply

sqlite:
	$(call print-start-time)
	@pipenv run ./build/ags_index.py -v --make-sqlite

csv:
	$(call print-start-time)
	@pipenv run ./build/ags_index.py -v --make-csv

screenshots:
	$(call print-start-time)
	@pipenv run ./build/make_screenshots.sh screenshots

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
	@mv ${AGSDEST}/AmigaVision.hdf ${AGSDEST}/games/Amiga
	@printf '\a'

image-fsuae:
	$(call print-start-time)
	@$(IMAGE_PREP_CMD)
	@$(MAKE) clone-fsuae
	@mv ${AGSDEST}/AmigaVision.hdf ${AGSDEST}/games/Amiga
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
	./build/hdf_fuse_clone.sh \
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
	@pipenv run ./build/ags_imager.py -v -c configs/AmigaVision.yaml --all-games --all-demoscene -d ${AGSCONTENT}/extra_dirs/Music::DH1:Music -o ${AGSDEST}
	@$(MAKE) clone-fuse

clone-hst:
	$(call print-start-time)
	@echo "Running FS-UAE format pass + hst-amiga-pfs import..."
	@start=$$(date +%s); \
	if [ ! -d "$(subst ",,${AGSTEMP})" ]; then \
		echo "Preparing temp build tree..."; \
		$(MAKE) prepare-image-temp || exit $$?; \
	fi; \
	hdf="$(subst ",,${AGSDEST})/AmigaVision.hdf"; \
	if [ ! -f "$$hdf" ]; then \
		hdf="$(subst ",,${AMIGAVISION_HDF})"; \
	fi; \
	clone_path="$(subst ",,${AGSTEMP})/clone"; \
	clone_backup="$$clone_path.hst-backup"; \
	cp "$$clone_path" "$$clone_backup"; \
	trap 'mv -f "$$clone_backup" "$$clone_path" >/dev/null 2>&1 || true' EXIT; \
	cp ./build/clone-format-only.clonescript "$$clone_path"; \
	log="${AGSTEMP}/fs-uae-format-hst.log"; \
	if ! ${FSUAEBIN} ${AGSTEMP}/cfg.fs-uae >"$$log" 2>&1; then \
		cat "$$log"; \
		exit 1; \
	fi; \
	mv -f "$$clone_backup" "$$clone_path"; \
	trap - EXIT; \
	./build/hdf_hst_clone.sh \
		--hdf "$$hdf" \
		--src-root "$(subst ",,${AGSTEMP})" \
		--hst-amiga "$(subst ",,${HSTAMIGABIN})" \
		--log-dir "$(subst ",,${AGSTEMP})"; \
	if [ -f "$(subst ",,${AGSDEST})/AmigaVision.hdf" ]; then \
		mv "$(subst ",,${AGSDEST})/AmigaVision.hdf" "$(subst ",,${AGSDEST})/games/Amiga"; \
	fi; \
	end=$$(date +%s); \
	echo "Hybrid clone time: $$((end - start))s"
	@printf '\a'

image-hst:
	$(call print-start-time)
	@pipenv run ./build/ags_imager.py -v -c configs/AmigaVision.yaml --all-games --all-demoscene -d ${AGSCONTENT}/extra_dirs/Music::DH1:Music -o ${AGSDEST}
	@$(MAKE) clone-hst

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
	@mv ${AGSDEST}/AmigaVision.hdf ${AGSDEST}/games/Amiga
	@printf '\a'

pocket-image:
	$(call print-start-time)
	@pipenv run ./build/ags_imager.py -v -c configs/AmigaVision-Pocket.yaml --all-demos --auto-lists -d ${AGSCONTENT}/extra_dirs/LessMusic::DH1:Music -o ${AGSDEST}
	@$(MAKE) clone-amiberry
	@mv ${AGSDEST}/AmigaVision-Pocket.hdf ${AGSDEST}/AmigaVision-Pocket
	@printf '\a'

mini-image:
	$(call print-start-time)
	@pipenv run ./build/ags_imager.py -v -c configs/AmigaVision-Mini.yaml --all-demos --auto-lists -d ${AGSCONTENT}/extra_dirs/LessMusic::DH1:Music -o ${AGSDEST}
	@$(MAKE) clone-amiberry
	@mv ${AGSDEST}/AmigaVision-Mini.hdf ${AGSDEST}/AmigaVision-Mini
	@printf '\a'

test-image:
	$(call print-start-time)
	@pipenv run ./build/ags_imager.py -v -c configs/Test.yaml --auto-lists -o ${AGSDEST}
	@$(MAKE) clone-amiberry
	@printf '\a'

test-dry:
	$(call print-start-time)
	@pipenv run ./build/ags_imager.py -v -c configs/Test.yaml --only-ags-tree --auto-lists -o ${AGSDEST}
	@printf '\a'

pi: image
	$(call print-start-time)
	@./build/pi_image.sh \
		--base-img "${REPLAYOS_BASE_IMG}" \
		--hdf "${AMIGAVISION_HDF}" \
		--output-img "${REPLAYOS_OUTPUT_IMG}" \
		--payload-dir "./replay" \
		--size "${REPLAYOS_IMG_SIZE}"
	@printf '\a'

pi-only:
	$(call print-start-time)
	@./build/pi_image.sh \
		--base-img "${REPLAYOS_BASE_IMG}" \
		--hdf "${AMIGAVISION_HDF}" \
		--output-img "${REPLAYOS_OUTPUT_IMG}" \
		--payload-dir "./replay" \
		--size "${REPLAYOS_IMG_SIZE}"
	@printf '\a'

distros:
	$(call print-start-time)
	@$(DISTRO_PACKAGE_PROMPT) all

distro-mister:
	$(call print-start-time)
	@$(DISTRO_PACKAGE_PROMPT) mister

distro-cd32-mister:
	$(call print-start-time)
	@$(DISTRO_PACKAGE_PROMPT) cd32-mister

distro-emulators:
	$(call print-start-time)
	@$(DISTRO_PACKAGE_PROMPT) emulators

distro-pi:
	$(call print-start-time)
	@$(DISTRO_PACKAGE_PROMPT) pi

distro-amiga:
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
