# Post build script
cp -R $AGSCONTENT/distro/* $AGSDEST/
mv $AGSDEST/Extras.md  $AGSDEST/Extras.txt
mv $AGSDEST/History.md $AGSDEST/History.txt
mv $AGSDEST/ReadMe.md  $AGSDEST/ReadMe.txt
