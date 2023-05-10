# Post build script
mkdir $AGSDEST/docs
cp $AGSCONTENT/distro/*.md $AGSDEST/docs
cp $AGSCONTENT/distro/games/Amiga/MegaAGS-Kickstart.rom $AGSDEST/
cp $AGSCONTENT/distro/games/Amiga/MegaAGS-Saves.hdf $AGSDEST/
mv $AGSDEST/docs/MegaAGS-Extras.md $AGSDEST/docs/MegaAGS-Extras.txt
mv $AGSDEST/docs/MegaAGS-History.md $AGSDEST/docs/MegaAGS-History.txt
mv $AGSDEST/docs/MegaAGS-ReadMe.md $AGSDEST/docs/MegaAGS-ReadMe.txt
