# Post build script
rm -rf $AGSDEST/AmigaVision-Pocket
mkdir $AGSDEST/AmigaVision-Pocket
cp -R $AGSCONTENT/distro_pocket/* $AGSDEST/AmigaVision-Pocket
mv $AGSDEST/AmigaVision-Pocket/AmigaVision-Pocket-ReadMe.md $AGSDEST/AmigaVision-Pocket/AmigaVision-Pocket-ReadMe.txt
