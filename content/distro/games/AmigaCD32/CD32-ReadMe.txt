== Amiga CD32 setup for MiSTer ==

This is a convenience package that will allow you to load CD32 games using the MiSTer Amiga core.


== Adding games ==

Put your CD32 disc images in the games/AmigaCD32 directory. CHD and BIN/CUE as well as ISO images are supported.


== Usage ==

* Navigate to Consoles -> Amiga CD32 and start it.
* You will be presented with a UI, but don't click anything yet.
* Open the MiSTer menu (F12), and navigate to the Drives section.
* Navigate to the Slave section, and select the CD32 disc image you want to play. (If you are using bin/cue files, select the cue file here)
* Navigate back to the main menu, and select "Reset". Because of the way the core works, you *HAVE* to do a reset every time you change a disc image.
* The system boots again, and you get the UI
* Select "Boot"
* Enjoy your game!


== A note on compatibility ==

This is not a *real* CD32 core for the MiSTer. It uses the CD Audio support that was recently added to the Amiga (Minimig) core, and uses a program called CD32-Emulator to run CD32 games. 

Compatibility is not perfect, and not all games will work or necessarily have their CD soundtracks. 

The MiSTer developers are always improving the cores, so do check if official CD32 support has been added by the time you read this, the "emulator" program may no longer be necessary.
