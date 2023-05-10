include .env
.PHONY: default env env-rm index image pocket-image test-image test-dry screenshots sqlite clean

default:
	@echo No default action

env:
	@pipenv install

env-rm:
	@pipenv --rm

index:
	@pipenv run ./ags_index.py -v

image:
	@pipenv run ./ags_imager.py -v -c configs/MegaAGS.yaml --all-games --all-demos -d ${AGSCONTENT}/extra_dirs/Music::DH2 -o ${AGSDEST}
	@${FSUAEBIN} ${AGSTEMP}/cfg.fs-uae

pocket-image:
	@pipenv run ./ags_imager.py -v -c configs/MegaAGS-Pocket.yaml --auto-lists -d ${AGSCONTENT}/extra_dirs_pocket/Music::DH2 -o ${AGSDEST}
	@${FSUAEBIN} ${AGSTEMP}/cfg.fs-uae

test-image:
	@pipenv run ./ags_imager.py -v -c configs/Test.yaml --auto-lists -o ${AGSDEST}
	@${FSUAEBIN} ${AGSTEMP}/cfg.fs-uae

test-dry:
	@pipenv run ./ags_imager.py -v -c configs/Test.yaml --only-ags-tree --auto-lists -o ${AGSDEST}

screenshots:
	@pipenv run ./make_screenshots.sh screenshots

sqlite:
	@pipenv run ./ags_index.py -v --make-sqlite

csv:
	@pipenv run ./ags_index.py -v --make-csv
