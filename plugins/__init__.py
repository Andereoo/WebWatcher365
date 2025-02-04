"""
Plugins:

Drop python files into this directory to have them loaded as plugins.
Plugins will show as an extra page in the WebWatcher365 application.

All plugin files must follow the same basic format:

---

#WebWatcher365 plugin base class.
#Add to this as needed, but do not rename or remove
#the WebWatcherPlugin class or mentioned variables.

import wx
class WebWatcherPlugin(wx.Panel):
    def __init__(self, parent, error_func):
        wx.Panel.__init__(self, parent)
        self.image = # path to default icon
        self.image_active = # path to active icon
        self.evt_active = # wx pyeventbinder (i.e. wx.PyEventBinder(NEW_EVENT, 1))
        self.name = # name of this plugin        

"""
