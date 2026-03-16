include .env
.PHONY: default env env-rm index index-add-missing manifests missing-manifests verify-manifests prune-manifests prune-manifests-apply sync-manifests sync-manifests-apply promote-newer-archives sqlite csv screenshots image pocket-image mini-image test-image test-dry pi pi-only clean

PYTHON ?= python3.11
SOURCE ?= ${AGSCONTENT}/titles/manual-downloads

REPLAYOS_BASE_IMG ?= ${AGSCONTENT}/base/RePlayOS.img
REPLAYOS_OUTPUT_IMG ?= ${AGSDEST}/AmigaVision-RPi.img
REPLAYOS_IMG_SIZE ?= 16g
AMIGAVISION_HDF ?= ${AGSDEST}/games/Amiga/AmigaVision.hdf

default:
	@echo No default action

env:
	-@pipenv --rm
	-@pipenv --clear
	@pipenv --python "$$(command -v $(PYTHON) || command -v python3 || command -v python)"
	@pipenv install

env-rm:
	-@pipenv -v --rm
	-@pipenv -v --clear

index:
	@pipenv run ./build/ags_index.py -v
	@pipenv run ./build/ags_index.py --make-csv

index-add-missing:
	@pipenv run ./build/ags_index.py -v --append-missing-csv

manifests:
	@pipenv run ./build/ags_index.py --make-manifests

missing-manifests:
	@pipenv run ./build/ags_index.py --make-manifests --only-missing

verify-manifests:
	@pipenv run ./build/ags_index.py --verify-manifests

prune-manifests:
	@pipenv run ./build/ags_index.py --prune-manifests

prune-manifests-apply:
	@pipenv run ./build/ags_index.py --prune-manifests --apply

sync-manifests:
	@pipenv run ./build/ags_index.py --sync-manifests

sync-manifests-apply:
	@pipenv run ./build/ags_index.py --sync-manifests --apply

promote-newer-archives:
	@pipenv run python ./build/promote_newer_archives.py --apply "$(SOURCE)"

sqlite:
	@pipenv run ./build/ags_index.py -v --make-sqlite

csv:
	@pipenv run ./build/ags_index.py -v --make-csv

screenshots:
	@pipenv run ./build/make_screenshots.sh screenshots

image:
	@pipenv run ./build/ags_imager.py -v -c configs/AmigaVision.yaml --all-games --all-demoscene -d ${AGSCONTENT}/extra_dirs/Music::DH1:Music -o ${AGSDEST}
	@${FSUAEBIN} ${AGSTEMP}/cfg.fs-uae
	@mv ${AGSDEST}/AmigaVision.hdf ${AGSDEST}/games/Amiga
	@echo -e "\a"

pocket-image:
	@pipenv run ./build/ags_imager.py -v -c configs/AmigaVision-Pocket.yaml --all-demos --auto-lists -d ${AGSCONTENT}/extra_dirs/LessMusic::DH1:Music -o ${AGSDEST}
	@${FSUAEBIN} ${AGSTEMP}/cfg.fs-uae
	@mv ${AGSDEST}/AmigaVision-Pocket.hdf ${AGSDEST}/AmigaVision-Pocket
	@echo -e "\a"

mini-image:
	@pipenv run ./build/ags_imager.py -v -c configs/AmigaVision-Mini.yaml --all-demos --auto-lists -d ${AGSCONTENT}/extra_dirs/LessMusic::DH1:Music -o ${AGSDEST}
	@${FSUAEBIN} ${AGSTEMP}/cfg.fs-uae
	@mv ${AGSDEST}/AmigaVision-Mini.hdf ${AGSDEST}/AmigaVision-Mini
	@echo -e "\a"

test-image:
	@pipenv run ./build/ags_imager.py -v -c configs/Test.yaml --auto-lists -o ${AGSDEST}
	@${FSUAEBIN} ${AGSTEMP}/cfg.fs-uae
	@echo -e "\a"

test-dry:
	@pipenv run ./build/ags_imager.py -v -c configs/Test.yaml --only-ags-tree --auto-lists -o ${AGSDEST}
	@echo -e "\a"

pi: image
	@./build/pi_image.sh \
		--base-img "${REPLAYOS_BASE_IMG}" \
		--hdf "${AMIGAVISION_HDF}" \
		--output-img "${REPLAYOS_OUTPUT_IMG}" \
		--payload-dir "./replay" \
		--size "${REPLAYOS_IMG_SIZE}"

pi-only:
	@./build/pi_image.sh \
		--base-img "${REPLAYOS_BASE_IMG}" \
		--hdf "${AMIGAVISION_HDF}" \
		--output-img "${REPLAYOS_OUTPUT_IMG}" \
		--payload-dir "./replay" \
		--size "${REPLAYOS_IMG_SIZE}"
