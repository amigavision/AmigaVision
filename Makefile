.PHONY: default env index image clean

default:
	@echo No default action

env:
	@pip2 install -e dependencies/amitools-0.1.0
	@pipenv install

env-rm:
	@pipenv --rm
	@pip2 uninstall amitools

index:
	@pipenv run ./ags_index.py -v

image:
	@pipenv run ./ags_build.py -v -c configs/MegaAGS.yaml --all_games -d data/extra_dirs/Music::DH2 -o ~/Temp/AGSImager

image-ntsc:
	@pipenv run ./ags_build.py -v -c configs/MegaAGS.yaml --all_games --force_ntsc -d data/extra_dirs/Music::DH2 -o ~/Temp/AGSImager

test-image:
	@pipenv run ./ags_build.py -v -c configs/Test.yaml -o ~/Temp/AGSImager

clean:
	@pipenv --rm
