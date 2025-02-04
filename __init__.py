### WebWatcher365, 2020
### Checks for changes to websites and generates+sends emails that outlines the changes
### Ships with an error console and a simple mail client
### Supports plugins that can be added as seperate pages

import os
import wx
from WebWatcher365 import WebWatcher365

if __name__ == "__main__":
    if os.name == "nt":
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    app = wx.App(redirect = False)
    frame = WebWatcher365(None, title='WebWatcher365')
    app.MainLoop()
