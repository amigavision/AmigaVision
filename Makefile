include .env
.PHONY: default env env-rm index image test-image screenshots sqlite clean

default:
	@echo No default action

env:
	@pipenv install

env-rm:
	@pipenv --rm

index:
	@pipenv run ./ags_index.py -v

image:
	@pipenv run ./ags_imager.py -v -c configs/MegaAGS.yaml --all_games --all_demos -d ${AGSCONTENT}/extra_dirs/Music::DH2 -o ${AGSDEST}
	@${FSUAEBIN} ${AGSTEMP}/cfg.fs-uae

test-image:
	@pipenv run ./ags_imager.py -v -c configs/Test.yaml -o ${AGSDEST}
	@${FSUAEBIN} ${AGSTEMP}/cfg.fs-uae

screenshots:
	@pipenv run ./make_screenshots.sh screenshots

sqlite:
	@pipenv run ./ags_index.py -v --make-sqlite
