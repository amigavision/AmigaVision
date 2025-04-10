include .env
.PHONY: default env env-rm index manifests manifests-check sqlite csv screenshots image pocket-image test-image test-dry clean

default:
	@echo No default action

env:
	-@pipenv --rm
	-@pipenv --clear
	@pipenv install

env-rm:
	-@pipenv -v --rm
	-@pipenv -v --clear

index:
	@pipenv run ./build/ags_index.py -v

manifests:
	@pipenv run ./build/ags_index.py --make-manifests

missing-manifests:
	@pipenv run ./build/ags_index.py --make-manifests --only-missing

verify-manifests:
	@pipenv run ./build/ags_index.py --verify-manifests

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
