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
	@pipenv run ./ags_build.py -v -c configs/MegaAGS.yaml --all_games --all_demos -d ../AGSImager-Content/extra_dirs/Music::DH2 -o ~/Temp/AGSImager
	../fs-uae/fs-uae ~/Temp/AGSImager/tmp/cfg.fs-uae

test-image:
	@pipenv run ./ags_build.py -v -c configs/Test.yaml -o ~/Temp/AGSImager
	../fs-uae/fs-uae ~/Temp/AGSImager/tmp/cfg.fs-uae

screenshots:
	@pipenv run ./make_screenshots.sh screenshots

sqlite:
	@pipenv run ./ags_index.py -v --make-sqlite

clean:
	@rm -rf ~/Temp/AGSImager/tmp/
