# Deliberately does nothing. The MacroPad's previous firmware (Macropad
# Hotkeys) called storage.disable_usb_drive() here, which is why CIRCUITPY
# doesn't show up on the desktop right now. Wolfpunk Foam leaves the drive
# alone so it mounts normally, like any other CircuitPython board - once
# this boot.py is on the board, drag-and-drop editing just works again.
