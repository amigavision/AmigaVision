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
	@pipenv run ./ags_index.py -v

manifests:
	@pipenv run ./ags_index.py --make-manifests

missing-manifests:
	@pipenv run ./ags_index.py --make-manifests --only-missing

verify-manifests:
	@pipenv run ./ags_index.py --verify-manifests

sqlite:
	@pipenv run ./ags_index.py -v --make-sqlite

csv:
	@pipenv run ./ags_index.py -v --make-csv

screenshots:
	@pipenv run ./make_screenshots.sh screenshots

image:
	@pipenv run ./ags_imager.py -v -c configs/MegaAGS.yaml --all-games --all-demoscene -d ${AGSCONTENT}/extra_dirs/Music::DH1:Music -o ${AGSDEST}
	@${FSUAEBIN} ${AGSTEMP}/cfg.fs-uae
	@mv ${AGSDEST}/MegaAGS.hdf ${AGSDEST}/games/Amiga/MegaAGS.hdf

pocket-image:
	@pipenv run ./ags_imager.py -v -c configs/MegaAGS-Pocket.yaml --all-demos --auto-lists -d ${AGSCONTENT}/extra_dirs/LessMusic::DH1:Music -o ${AGSDEST}
	@${FSUAEBIN} ${AGSTEMP}/cfg.fs-uae

test-image:
	@pipenv run ./ags_imager.py -v -c configs/Test.yaml --auto-lists -o ${AGSDEST}
	@${FSUAEBIN} ${AGSTEMP}/cfg.fs-uae

test-dry:
	@pipenv run ./ags_imager.py -v -c configs/Test.yaml --only-ags-tree --auto-lists -o ${AGSDEST}
