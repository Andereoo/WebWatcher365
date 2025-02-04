from imaplib import IMAP4_SSL

import wx
import wx.adv


class FinishEvent(wx.PyCommandEvent):
    def __init__(self, etype, eid, value=None):
        wx.PyCommandEvent.__init__(self, etype, eid)
        self._value = value
        
    def GetValue(self):
        return self._value

class CredentialsPage(wx.Panel):
    def __init__(self, parent, firsttime):
        wx.Panel.__init__(self, parent=parent)
        
        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        horizontal_sizer = wx.BoxSizer(wx.HORIZONTAL)
        vertical_content_sizer = wx.BoxSizer(wx.VERTICAL)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.NEW_EVENT = wx.NewEventType()
        self.EVT_FINISH = wx.PyEventBinder(self.NEW_EVENT, 1)

        if firsttime:
            self.introduction_text = introduction_text = wx.StaticText(self, label="""Let us get to know you.""", style = wx.ALIGN_CENTRE_HORIZONTAL)
            link = wx.adv.HyperlinkCtrl(self, label="More info >>")
            self.continue_button = continue_button = wx.Button(self, label='Start')
            vertical_sizer.Add(introduction_text, 0, wx.CENTRE | wx.TOP, 5)
            vertical_sizer.Add(link, 0, wx.CENTRE | wx.TOP, 5)
            link.Bind(wx.adv.EVT_HYPERLINK, self.open_dialog)
        else:
            self.continue_button = continue_button = wx.Button(self, label='Save')
        self.username = username = wx.TextCtrl(self)
        self.password = password = wx.TextCtrl(self, style=wx.TE_PASSWORD)
        self.keep_logged_in = keep_logged_in = wx.CheckBox(self, label="Keep me logged in")
        
        vertical_sizer.Add(horizontal_sizer, 1, wx.CENTRE | wx.EXPAND)
        horizontal_sizer.Add(vertical_content_sizer, 1, wx.CENTRE, wx.EXPAND)
        vertical_content_sizer.Add(wx.StaticText(self, label="Email account:"), 0, wx.CENTRE | wx.BOTTOM, 5)
        vertical_content_sizer.Add(username, 0, wx.EXPAND | wx.RIGHT | wx.LEFT, 80)
        #vertical_content_sizer.AddSpacer(40)
        vertical_content_sizer.Add(wx.StaticText(self, label="Email password:"), 0, wx.CENTRE | wx.BOTTOM, 5)
        vertical_content_sizer.Add(password, 0, wx.EXPAND | wx.RIGHT | wx.LEFT, 80)
        vertical_sizer.Add(button_sizer, 0, wx.RIGHT | wx.ALIGN_RIGHT | wx.BOTTOM, 5)
        button_sizer.Add(keep_logged_in, 0, wx.RIGHT | wx.CENTER, 10)
        button_sizer.Add(continue_button)

        continue_button.Bind(wx.EVT_BUTTON, self.on_continue_press)
        username.Bind(wx.EVT_TEXT, lambda e: username.SetBackgroundColour(wx.NullColour))
        password.Bind(wx.EVT_TEXT, lambda e: password.SetBackgroundColour(wx.NullColour))

        self.SetSizer(vertical_sizer)

    def open_dialog(self, event):
        message = """
WebWatcher365 requires a valid email account and password in order to send email notifications to other people.
This information is stored securely on your computer - it is NOT shared with anyone.

Note that on some accounts (eg. gmail accounts) , you will need to allow less-secure apps in your account's settings."""
        wx.MessageDialog(None, message, caption="WebWatcher365 Help Dialog",
              style=wx.OK | wx.CENTRE).ShowModal()

    def set_credentials(self, uname, passwd, keep_logged):
        self.username.SetValue(uname)
        self.password.SetValue(passwd)
        self.keep_logged_in.SetValue(keep_logged)

    def on_continue_press(self, event):
        try:
            self.Disable()
            imap = imap = IMAP4_SSL("imap.gmail.com")
            imap.login(self.username.GetValue(), self.password.GetValue())
            imap.select("INBOX")
            imap.close()
            imap.logout()
            evt = FinishEvent(self.NEW_EVENT, -1, self.return_data())
            wx.PostEvent(self, evt)
        except Exception:
            self.username.SetBackgroundColour((255,0,0))
            self.password.SetBackgroundColour((255,0,0))
        finally:
            self.Enable()
            
    def return_data(self):
        uname = self.username.GetValue()
        paswd = self.password.GetValue()
        login = self.keep_logged_in.GetValue()

        return [uname, paswd, login]
    
        
class EmailDialog(wx.Dialog):
    def __init__(self, parent, *args, firsttime=True, **kwargs):
        wx.Dialog.__init__(self, parent, *args, **kwargs)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.contents = contents = CredentialsPage(self, firsttime)
        sizer.Add(contents, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.NEW_EVENT = wx.NewEventType()
        self.EVT_FINISH = wx.PyEventBinder(self.NEW_EVENT, 1)
        contents.Bind(contents.EVT_FINISH, self.on_finish)

    def set_credentials(self, uname, passwd, keep_logged):
        self.contents.set_credentials(uname, passwd, keep_logged)

    def on_finish(self, event):
        evt = FinishEvent(self.NEW_EVENT, -1, event.GetValue())
        wx.PostEvent(self, evt)
