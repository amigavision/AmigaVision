# Post build script
rm -rf $AGSDEST/AmigaVision-Mini
mkdir $AGSDEST/AmigaVision-Mini
cp -R $AGSCONTENT/distro_mini/* $AGSDEST/AmigaVision-Mini
mv $AGSDEST/AmigaVision-Mini/AmigaVision-Mini-ReadMe.md $AGSDEST/AmigaVision-Mini/AmigaVision-Mini-ReadMe.txt
