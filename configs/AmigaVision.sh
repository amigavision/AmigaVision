# Post build script
cp -R ./content/distro/* "$AGSDEST"/
[ -d "$AGSCONTENT"/distro/games/Amiga ] && cp -R "$AGSCONTENT"/distro/games/Amiga/* "$AGSDEST"/games/Amiga/
[ -f "$AGSDEST"/Extras.md ] && mv "$AGSDEST"/Extras.md "$AGSDEST"/Extras.txt
[ -f "$AGSDEST"/History.md ] && mv "$AGSDEST"/History.md "$AGSDEST"/History.txt
cp ./ReadMe.md "$AGSDEST"/ReadMe.txt
