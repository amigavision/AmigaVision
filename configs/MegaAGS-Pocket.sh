# Post build script
rm -rf $AGSDEST/MegaAGS-Pocket
mkdir $AGSDEST/MegaAGS-Pocket
cp -R $AGSCONTENT/distro_pocket/* $AGSDEST/MegaAGS-Pocket
mv $AGSDEST/MegaAGS-Pocket/MegaAGS-Pocket-ReadMe.md $AGSDEST/MegaAGS-Pocket/MegaAGS-Pocket-ReadMe.txt
