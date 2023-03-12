# Post build script
cp -R $AGSCONTENT/distro/* $AGSDEST/
mv $AGSDEST/MegaAGS-Extras.md $AGSDEST/MegaAGS-Extras.txt
mv $AGSDEST/MegaAGS-History.md $AGSDEST/MegaAGS-History.txt
mv $AGSDEST/MegaAGS-ReadMe.md $AGSDEST/MegaAGS-ReadMe.txt
