# Post build script
rm -rf $AGSDEST/MegaAGS-Mini
mkdir $AGSDEST/MegaAGS-Mini
cp -R $AGSCONTENT/distro_mini/* $AGSDEST/MegaAGS-Mini
mv $AGSDEST/MegaAGS-Mini/MegaAGS-Mini-ReadMe.md $AGSDEST/MegaAGS-Mini/MegaAGS-Mini-ReadMe.txt
