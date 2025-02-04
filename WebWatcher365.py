import glob
import os
import datetime
import wx
import wx.adv
import wx.lib.platebtn
import ast
import keyring
import importlib
import sys

import smtplib, ssl, imaplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from Threads import ReturnEvent, InlineCSS, GetStyles
from SetupFrame import SetupFrame
from WebsiteEditor import WebsiteEditor
from EmailDialog import EmailDialog
from EmailManager import *


class WebsiteManager(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
          
        page_sizer = wx.BoxSizer(wx.VERTICAL)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.websites = []
        
        self.website_list = website_list = wx.ListCtrl(self, style = wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_NONE) 
        website_list.InsertColumn(0, 'Website URL') 
        website_list.InsertColumn(1, 'Section', width=120)
        self.SetBackgroundColour(website_list.GetBackgroundColour())

        add_icon = wx.Bitmap(os.path.join("resources", "add.png"), wx.BITMAP_TYPE_ANY)
        remove_icon = wx.Bitmap(os.path.join("resources", "remove.png"), wx.BITMAP_TYPE_ANY)
        edit_icon = wx.Bitmap(os.path.join("resources", "edit.png"), wx.BITMAP_TYPE_ANY)
        add_button = wx.BitmapButton(self, -1, add_icon)
        self.remove_button = remove_button = wx.BitmapButton(self, -1, remove_icon)
        self.edit_button = edit_button = wx.BitmapButton(self, -1, edit_icon)

        remove_button.SetToolTip("Remove selected website")
        edit_button.SetToolTip("Edit selected website")
        add_button.SetToolTip("Add a new website")
        self.remove_button.Disable()
        self.edit_button.Disable()

        page_sizer.Add(website_list, 1, wx.EXPAND)
        page_sizer.Add(button_sizer, 0, wx.ALIGN_RIGHT)
        button_sizer.Add(add_button, 0, wx.ALL, 3)
        button_sizer.Add(remove_button, 0, wx.ALL, 3)
        button_sizer.Add(edit_button, 0, wx.ALL, 3)

        add_button.Bind(wx.EVT_BUTTON, self.on_add_button)
        remove_button.Bind(wx.EVT_BUTTON, self.on_remove_button)
        edit_button.Bind(wx.EVT_BUTTON, self.on_edit_button)
        website_list.Bind(wx.EVT_SIZE, self.on_resize)
        website_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_selection)
        website_list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.off_selection)
        website_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_edit_button)

        self.SetSizer(page_sizer)

        self.NEW_EVENT = NEW_EVENT = wx.NewEventType()
        self.EVT_CHANGE = wx.PyEventBinder(NEW_EVENT, 1)
        
    def on_resize(self, event):
        self.website_list.SetColumnWidth(0, ((self.website_list.GetSize()[0])-120))
        self.website_list.Layout()

    def on_add_button(self, event):
        website_adder = SetupFrame(self, title='WebWatcher365 - add a website')
        website_adder.SetIcon(wx.Icon(os.path.join("resources", "webwatcher_icon.ico")))
        website_adder.Bind(wx.EVT_CLOSE, lambda event, website_adder=website_adder: self.on_website_adder_close(event, website_adder))

    def on_remove_button(self, event):
        delete = wx.MessageDialog(None, "Are you sure you want to remove this website. This action cannot be undone.", "Confirm delete", wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION).ShowModal()
        if delete == wx.ID_YES:
            item = self.website_list.GetFocusedItem()
            if item != -1:
                settings_file = self.websites[item]["filename"]
                if os.path.exists(settings_file):
                    os.remove(settings_file)
                if os.path.exists(settings_file+".txt"):
                    os.remove(settings_file+".txt")
                    
                del self.websites[item]
                
                self.website_list.DeleteItem(item)
                if self.website_list.GetFocusedItem() == -1:
                    self.off_selection()
        else:
            return
    
    def on_edit_button(self, event):
        item = self.website_list.GetFocusedItem()
        if item != -1:
            editor = WebsiteEditor(self, self.websites[item]["email_addresses"], self.websites[item]["message"], title="WebWatcher365 - edit message")
            editor.SetIcon(wx.Icon(os.path.join("resources", "webwatcher_icon.ico")))
            data = editor.return_data()
            editor.Bind(wx.EVT_CLOSE, lambda event, editor=editor, data=data, filename=self.websites[item]["filename"]: self.on_editor_close(event, editor, data, filename))
            
    def on_selection(self, event=None):
        self.remove_button.Enable()
        self.edit_button.Enable()
    
    def off_selection(self, event=None):
        self.remove_button.Disable()
        self.edit_button.Disable()

    def on_editor_close(self, event, website_editor, data, filename):
        data_new = website_editor.return_data()
        if data_new != data:
            close = wx.MessageDialog(None, "Do you want to save your changes?", "Confirm save", wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION).ShowModal()
            if close == wx.ID_YES:
                for item in self.websites:
                    if item["filename"] == filename:
                        item.update(data_new)
                        with open(filename, "w+") as settings_file:
                            settings_file.write(str(item))
                        evt = ReturnEvent(self.NEW_EVENT, -1, item)
                        wx.PostEvent(self, evt)
        website_editor.Destroy()

    def on_website_adder_close(self, event, website_adder):
        data = website_adder.return_data()
        site_code = website_adder.return_site_code()
        if len(data) == 0:
            close = wx.MessageDialog(None, "Are you sure you want to close this window? Any changes you have made will be lost.", "Confirm close", wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION).ShowModal()
            if close == wx.ID_YES:
                website_adder.Destroy()
            else:
                return
        else:
            website_adder.Destroy()
            self.add_site(data, site_code)

    def add_site(self, data, site_code=None, filename=None):
        index = self.website_list.InsertItem(0, "")
        self.website_list.SetItem(index, 0, data["website"])
        if data["section_id"] == "":
            if data["section_nodeName"] == "":
                self.website_list.SetItem(index, 1, "[whole page]")
            else:
                self.website_list.SetItem(index, 1, str(data["section_id"]))
        else:
            self.website_list.SetItem(index, 1, str(data["section_id"]))

        if filename is None:
            filename = (str(data["website"])+"-"+str(data["section_id"])+"-"+str(datetime.datetime.now()))
            for char in ['<','>',':','"','/','\\','|','?','*', ' ']:
                filename = filename.replace(char, "-")
            filename = os.path.join("websites", (filename+".json"))
                
            
            with open(filename, "w+") as settings_file:
                settings_file.write(str(data))

            if site_code is not None:
                with open(filename+".txt", "w+") as settings_file:
                    settings_file.write(str(site_code))

        data["filename"] = filename
        self.websites.insert(0, data)


class SettingsManager(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.uname = None
        self.passwd = None
        self.keep_logged = None
        self.page_sizer = page_sizer = wx.BoxSizer(wx.VERTICAL)
        window_box = wx.StaticBoxSizer(wx.VERTICAL, self, "Open window:")
        window_1 = wx.RadioButton(self, label="Always")
        self.window_2 = window_2 = wx.RadioButton(self, label="When action is needed")
        send_box = wx.StaticBoxSizer(wx.VERTICAL, self, "On Send (all):")
        send_1 = wx.RadioButton(self, label="Send", style=wx.RB_GROUP)
        self.send_2 = send_2 = wx.RadioButton(self, label="Close, then send")
        account_box = wx.StaticBoxSizer(wx.VERTICAL, self, "Account:")
        self.account = account = wx.lib.platebtn.PlateButton(self, label="", style=wx.lib.platebtn.PB_STYLE_SQUARE)
                
        page_sizer.Add(window_box, 0, wx.TOP | wx.BOTTOM | wx.RIGHT | wx.EXPAND, 10)
        window_box.Add(window_1, 0, wx.LEFT, 8)
        window_box.Add(window_2, 0, wx.LEFT | wx.BOTTOM, 8)
        page_sizer.Add(send_box, 0, wx.BOTTOM | wx.RIGHT | wx.EXPAND, 10)
        send_box.Add(send_1, 0, wx.LEFT, 8)
        send_box.Add(send_2, 0, wx.LEFT | wx.BOTTOM, 8)
        page_sizer.Add(account_box, 0,  wx.RIGHT | wx.EXPAND, 10)
        account_box.Add(account, 0, wx.LEFT | wx.RIGHT | wx.EXPAND | wx.BOTTOM, 8)


        window_1.Bind(wx.EVT_RADIOBUTTON, self.open_change)
        window_2.Bind(wx.EVT_RADIOBUTTON, self.open_change)
        send_1.Bind(wx.EVT_RADIOBUTTON, self.send_change)
        send_2.Bind(wx.EVT_RADIOBUTTON, self.send_change)
        account.Bind(wx.EVT_BUTTON, self.change_account)
        self.SetBackgroundColour(self.GetBackgroundColour())
        self.SetSizer(page_sizer)
        self.config()

        self.NEW_EVENT = NEW_EVENT = wx.NewEventType()
        self.EVT_EMAIL_CHANGE = wx.PyEventBinder(NEW_EVENT, 1)

    def add_panel(self, panel, text):
        window_box = wx.StaticBoxSizer(wx.VERTICAL, self, text)
        window_box.Add(panel, 1, wx.EXPAND)
        self.page_sizer.Add(window_box, 0, wx.TOP | wx.BOTTOM | wx.RIGHT | wx.EXPAND, 10)

    def send_change(self, event):
        if self.send_2.GetValue():
            send = False
        else:
            send = True
            
        with open(os.path.join("resources", "settings.json"), "r") as f:
            settings = ast.literal_eval(f.read())
        settings.update({"send_and_stay": send})
        with open(os.path.join("resources", "settings.json"), "w+") as f:
            f.write(str(settings))

    def open_change(self, event):
        if self.window_2.GetValue():
            _open = False
        else:
            _open = True
            
        with open(os.path.join("resources", "settings.json"), "r") as f:
            settings = ast.literal_eval(f.read())
        settings.update({"always_open": _open})
        with open(os.path.join("resources", "settings.json"), "w+") as f:
            f.write(str(settings))

    def set_credentials(self, uname, passwd, keep_logged=True):
        if keep_logged:
            keyring.set_password("WebWatcher365", uname, passwd)
            self.account.SetLabel(uname)
            self.uname = uname
            self.passwd = passwd
            self.keep_logged = keep_logged
            with open(os.path.join("resources", "settings.json"), "r") as f:
                settings = ast.literal_eval(f.read())
            settings.update({"uname":uname})
            with open(os.path.join("resources", "settings.json"), "w+") as f:
                f.write(str(settings))

    def config(self):
        try:
            with open(os.path.join("resources", "settings.json"), "r") as f:
                settings = ast.literal_eval(f.read())
            uname = settings["uname"]
            always_open = settings["always_open"]
            if not always_open:
                self.window_2.SetValue(True)
            on_send = settings["send_and_stay"]
            if not on_send:
                self.send_2.SetValue(True)
        except:
            pass

    def change_account(self, event):
        dialog = EmailDialog(self, firsttime=False, title="WebWatcher365")
        dialog.SetIcon(wx.Icon(os.path.join("resources", "webwatcher_icon.ico")))
        dialog.set_credentials(self.uname, self.passwd, self.keep_logged)
        dialog.Bind(wx.EVT_CLOSE, lambda event, dialog=dialog: self.on_dialog_close(event, dialog))
        dialog.Bind(dialog.EVT_FINISH, lambda event, dialog=dialog: self.on_email_finish(event, dialog))
        dialog.ShowModal()

    def on_email_finish(self, event, dialog):
        try:
            keyring.delete_password("WebWatcher365", self.uname)
        except keyring.errors.PasswordDeleteError():
            pass

        credentials = event.GetValue()
        self.set_credentials(*credentials)
        evt = ReturnEvent(self.NEW_EVENT, -1, event.GetValue())
        wx.PostEvent(self, evt)
        dialog.Destroy()

    def on_dialog_close(self, event, dialog):
        close_message = wx.MessageDialog(None, "Are you sure you want to close this window? Any changes you've made will not be saved.", "Quit", wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION).ShowModal()
        if close_message == wx.ID_YES:
            dialog.Destroy()


class SendManager(wx.Panel):
    def __init__(self, parent, error_func):
        wx.Panel.__init__(self, parent)

        self.start_checking = True
        self.threads_done = 0
        self.error_func = error_func
        self.uname = None
        self.passwd = None
        self.current = None
        self.can_close = True
        self.is_styling_site = False
        self.after_sent = 0
        
        page_sizer = wx.BoxSizer(wx.VERTICAL)
        horizontal_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.vertical_content_sizer = vertical_content_sizer = wx.BoxSizer(wx.VERTICAL)
        self.loading_sizer = loading_sizer = wx.BoxSizer(wx.HORIZONTAL)
        plane_icon = wx.Bitmap(os.path.join("resources", "plane.png"), wx.BITMAP_TYPE_ANY)
        self.plane = plane = wx.StaticBitmap(self, bitmap=plane_icon)
        self.caught_up_label = caught_up_label = wx.StaticText(self, label="There's nothing to monitor. \n Head over to the websites manager to add a site.", style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.loading_wheel = loading_wheel = wx.adv.AnimationCtrl(self, -1, wx.adv.Animation(os.path.join("resources", 'loading.gif')), size=(20,20))
        self.loading_text = loading_text = wx.StaticText(self, label="Checking")

        self.top_panel = top_panel = wx.Panel(self)
        send_panel_top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.send_panel = send_panel = wx.Panel(self)
        send_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        send_panel_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.send_label = send_label = wx.StaticText(top_panel, label="WebWatcher365 would like to send the following e-mails.")
        refresh_icon = wx.Bitmap(os.path.join("resources", "reload.png"), wx.BITMAP_TYPE_ANY)
        self.refresh_button = refresh_button = wx.BitmapButton(top_panel, -1, refresh_icon)
        refresh_button.SetToolTip("Refresh")

        cancel_button = wx.Button(send_panel, label="Don't send")
        send_one_button = wx.Button(send_panel, label="Send")
        send_all_button = wx.Button(send_panel, label=" Send all")
        send_all_button.SetBitmap(wx.Bitmap(os.path.join("resources", "send_small.png")),wx.LEFT)
        self.notebook = notebook = wx.Notebook(send_panel)
        send_panel_sizer.Add(notebook, 1, wx.ALL | wx.EXPAND, 5)
        send_panel_sizer.Add(send_panel_button_sizer, 0, wx.ALL | wx.EXPAND, 5)
        send_panel_top_sizer.Add(send_label, 0, wx.ALIGN_CENTER_VERTICAL)
        send_panel_top_sizer.Add((0,0), 1)
        send_panel_top_sizer.Add(refresh_button)
        send_panel_button_sizer.Add((0,0), 1)
        send_panel_button_sizer.Add(cancel_button, 0)
        send_panel_button_sizer.Add(send_one_button, 0, wx.LEFT, 3)
        send_panel_button_sizer.AddSpacer(30)
        send_panel_button_sizer.Add(send_all_button, 0, wx.LEFT, 3)
        top_panel.SetSizer(send_panel_top_sizer)
        send_panel.SetSizer(send_panel_sizer)

        page_sizer.Add(top_panel, 0, wx.ALL | wx.EXPAND, 5)
        page_sizer.Add(send_panel, 1, wx.EXPAND | wx.ALL, 5)
        page_sizer.Add(horizontal_sizer, 1, wx.CENTRE | wx.EXPAND)
        horizontal_sizer.Add(vertical_content_sizer, 1, wx.CENTRE, wx.EXPAND)
        vertical_content_sizer.Add(plane, 0, wx.CENTRE)
        vertical_content_sizer.Add(caught_up_label, 0, wx.CENTRE)
        page_sizer.Add(loading_sizer, 0, wx.RIGHT | wx.ALIGN_RIGHT | wx.BOTTOM, 5)
        loading_sizer.Add(loading_text)
        loading_sizer.Add(loading_wheel)
        self.SetSizer(page_sizer)
        self.SetBackgroundColour(self.GetBackgroundColour())
        send_panel.Hide()
        send_label.Hide()
        loading_wheel.Hide()
        loading_text.Hide()

        refresh_button.Bind(wx.EVT_BUTTON, self.refresh)
        cancel_button.Bind(wx.EVT_BUTTON, self.cancel)
        send_one_button.Bind(wx.EVT_BUTTON, self.send_one)
        send_all_button.Bind(wx.EVT_BUTTON, self.send_all)

        self.NEW_EVENT = NEW_EVENT = wx.NewEventType()
        self.EVT_ACTION_NEEDED = wx.PyEventBinder(NEW_EVENT, 1)
        self.NEW_EVENT2 = NEW_EVENT2 = wx.NewEventType()
        self.EVT_SENT = wx.PyEventBinder(NEW_EVENT2, 1)
        self.NEW_EVENT3 = NEW_EVENT3 = wx.NewEventType()
        self.EVT_DONE_CHECKING = wx.PyEventBinder(NEW_EVENT3, 1)
        self.NEW_EVENT4 = NEW_EVENT4 = wx.NewEventType()
        self.EVT_DONE_SENDING_ALL = wx.PyEventBinder(NEW_EVENT4, 1)

    def refresh(self, event):
        self.start_checking = True
        self.notebook.DeleteAllPages()
        files = []
        self.error_func("file://"+__file__, "Send manager refreshed", error=False)
        for file in glob.glob("websites/*.json"):
            files.append(file)
            self.error_func("file://"+(os.path.join(os.getcwd(), file)), "File found in "+(os.path.join(os.getcwd(), "websites")), error=False)
        files_len = len(files)
        for file in files:
            with open(file, 'r') as f:
                websites = ast.literal_eval(f.read())
                self.check(websites, file, files_len)
        if files_len == 0:
            self.send_panel.Hide()
            self.send_label.Hide()
            self.plane.Show()
            self.caught_up_label.SetLabel("There's nothing to monitor. \n Head over to the websites manager to add a site.")
            self.caught_up_label.Show()
            self.Layout()
        else:
            self.caught_up_label.SetLabel("...")
        self.Layout()

    def cancel(self, event):
        selected = self.notebook.GetSelection()
        page = self.notebook.GetPage(selected)
        close_message = wx.MessageDialog(None, "Do you want to update the local copy of this website first?", "Quit", wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION | wx.CANCEL).ShowModal()
        if close_message == wx.ID_YES:
            with open(page.webwatcher_filename+".txt", "w+") as file:
                file.write(str(page.webwatcher_new))
            self.notebook.DeletePage(selected)
        elif close_message == wx.ID_NO:
            self.notebook.DeletePage(selected)
        if len(self.notebook.GetChildren()) == 0:
            self.send_panel.Hide()
            self.plane.Show()
            self.send_label.Hide()
            self.caught_up_label.Show()
            self.caught_up_label.SetLabel("You're all caught up!")
            self.caught_up_label.Layout()
            self.Layout()

    def send_one(self, event):
        self.after_sent = None
        selected = self.notebook.GetSelection()
        page = self.notebook.GetPage(selected)
        self.current = page
        self.notebook.DeletePage(selected)
        self.loading_wheel.Play()
        self.loading_text.Show()
        self.loading_text.SetLabel("Sending")
        self.loading_wheel.Show()
        with open(page.webwatcher_filename+".txt", "w+") as file:
            file.write(str(page.webwatcher_new))
        if len(self.notebook.GetChildren()) == 0:
            self.send_panel.Hide()
            self.send_label.Hide()
            self.plane.Show()
            self.caught_up_label.Show()
            self.caught_up_label.SetLabel("You're all caught up!")
            self.caught_up_label.Layout()
        self.Layout()
        message = page.webwatcher_message
        html = """
                    <html>
                        <head>
                        </head>
                        <body>
                            <b><p>"""+message[1]+"""</p></b>
                            <p>"""+message[2].replace("\n", "</br>")+"""</p>
                            <div style="width:100%;">"""+page.webwatcher_val+"""</div>
                            <p>"""+message[3].replace("\n", "</br>")+"""</p>
                            <h6>"""+message[4]+"""</h6>
                        </body>
                    </html>
                """
        worker = SendEmailThread(self, html, page.webwatcher_recipients, page.webwatcher_subject, self.uname, self.passwd)
        worker.start()
        self.Bind(worker.EVT_SENT, lambda event, page=page, subject=message[0]: self.on_sent(event, page, subject))

    def on_sent(self, event, page, subject):
        if self.current == page:
            self.loading_wheel.Stop()
            self.loading_text.Hide()
            self.loading_wheel.Hide()
            self.Layout()

        error = event.GetError()
        if error is not None:
            self.error_func("file://"+__file__, "Error sending e-mail: "+str(error))
        else:
            self.error_func("file://"+__file__, "Successfully sent e-mail '"+str(subject)+"'", error=False)

        if self.after_sent is not None:
            self.after_sent -= 1
            if self.after_sent == 0:
                evt = wx.PyCommandEvent(self.NEW_EVENT4)
                wx.PostEvent(self, evt)
             
    def send_all(self, event):
        self.after_sent = len(self.notebook.GetChildren())
        evt = wx.PyCommandEvent(self.NEW_EVENT2)
        wx.PostEvent(self, evt)
        for page_num, page in enumerate(self.notebook.GetChildren()):
            self.current = page
            with open(page.webwatcher_filename+".txt", "w+") as file:
                file.write(str(page.webwatcher_new))
            self.loading_wheel.Play()
            self.loading_text.Show()
            self.loading_text.SetLabel("Sending")
            self.loading_wheel.Show()
            self.Layout()
            message = page.webwatcher_message
            html = """
                        <html>
                            <head>
                            </head>
                            <body>
                                <b><p>"""+message[1]+"""</p></b>
                                <p>"""+message[2].replace("\n", "</br>")+"""</p>
                                <div style="width:100%;">"""+page.webwatcher_val+"""</div>
                                <p>"""+message[3].replace("\n", "</br>")+"""</p>
                                <h6>"""+message[4]+"""</h6>
                            </body>
                        </html>
                    """
            worker = SendEmailThread(self, html, page.webwatcher_recipients, page.webwatcher_subject, self.uname, self.passwd)
            worker.start()
            self.Bind(worker.EVT_SENT, lambda event, page=page, subject=message[0]: self.on_sent(event, page, subject))
        self.notebook.DeleteAllPages()
        self.send_panel.Hide()
        self.send_label.Hide()
        self.plane.Show()
        self.caught_up_label.Show()
        self.caught_up_label.SetLabel("You're all caught up!")
        self.caught_up_label.Layout()
        self.Layout()
        
    def check(self, old_info, filename, files_len):
        if self.start_checking:
            self.loading_wheel.Play()
            self.loading_text.Show()
            self.loading_wheel.Show()
            self.loading_text.SetLabel("Checking")
            self.send_panel.Hide()
            self.refresh_button.Hide()
            self.send_label.Hide()
            self.plane.Show()
            self.caught_up_label.Show()
            self.Layout()
            self.Disable()
            self.threads_done = 0
            self.start_checking = False
            self.can_close = True
            self.is_styling_site = False
        if files_len == 0:
            self.caught_up_label.SetLabel("There's nothing to monitor. \n Head over to the websites manager to add a site.")
        else:
            self.caught_up_label.SetLabel("...")
        section_name = old_info["section_nodeName"]
        website = old_info["website"]
        id_params = {"id": old_info["section_id"]}
        worker = GetStyles(self, website, section_name, id_params)
        worker.start()
        self.Bind(worker.EVT_COUNT, lambda event, data=old_info, filename=filename, files_len=files_len: self.on_thread_return(event, data, filename, files_len))

    def on_thread_return(self, event, data, filename, files_len):
        done = False
        val = event.GetValue()[0]
        error = event.GetError()
        style = event.GetValue()[1]
        self.Layout()
        visited = False
        if (self.threads_done+1) == files_len:
            done = True
        if error:
            self.error_func(data["website"], "Error fetching website: "+str(error))
            self.can_close = False
            if done:
                self.on_finish_check()
        else:
            if val is None:
                self.error_func(data["website"], "Error fetching website: "+"Bs4 search returned None")
                self.can_close = False
            else:
                try:
                    with open(filename+".txt", "r") as file:
                        file_data = file.read()
                        file_data = file_data.rstrip('\n')
                except:
                    self.error_func(data["website"], "Old site file missing")
                    self.can_close = False
                    if done:
                        self.on_finish_check()
                    if not os.path.exists(filename):
                        return
                    else:
                        with open(filename+".txt", "w+") as file:
                            file.write(str(val))
                        return
                val = str(val)
                if val != file_data:
                    visited = False
                    self.can_close = False
                    self.is_styling_site = True
                    self.error_func(data["website"], "Site has changed", error=False)
                    self.loading_text.SetLabel("Styling")
                    highlight = InlineCSS(self, file_data, val, val.endswith("</html>"), style)
                    highlight.start()
                    self.Bind(highlight.EVT_DONE, lambda event, data=data, val=val, filename=filename,  done=done: self.finish_check(event, data, val, filename, files_len))
                    
                else:
                    visited = True
                    self.error_func(data["website"], "Site has not changed", error=False)
                    if done:
                        self.on_finish_check()
                    self.threads_done += 1
        if not visited:
            self.threads_done += 1
        
        if (self.threads_done >= files_len) and self.can_close:
            evt = wx.PyCommandEvent(self.NEW_EVENT3)
            wx.PostEvent(self, evt)
            
    def on_finish_check(self):
        self.loading_wheel.Stop()
        self.loading_text.Hide()
        self.loading_wheel.Hide()
        self.refresh_button.Show()
        if self.can_close == False:
            self.caught_up_label.SetLabel("Oops. Something went wrong. \n Check the error console for more information.")
        else:
            self.caught_up_label.SetLabel("You're all caught up!")
        self.loading_text.SetLabel("Checking")
        self.Enable()
        self.start_checking = True
        self.Layout()
            
    def finish_check(self, event, data, val, filename, files_len):
        self.threads_done += 1
        message = data["message"]
        html_new_msg = event.GetValue()
        error = event.GetError()
        if error:
            self.error_func(data["website"], "Error styling website: "+str(error))
        html = """
                    <html>
                        <head>
                        </head>
                        <body>
                            <div style="height:3px; width:100%; background-color:black;"></div>
                            <h5><b>Subject: """+message[0]+"""</b></h5>
                            <h5><b>To: """+str(data["email_addresses"]).replace("[", "").replace("]", "")+"""</b></h5>
                            <h5><b>From: """+str(self.uname)+"""</b></h5>
                            <div style="height:3px; width:100%; background-color:black;"></div>
                            <b><p>"""+message[1]+"""</p></b>
                            <p>"""+message[2].replace("\n", "</br>")+"""</p>
                            <div style="width:100%;">"""+html_new_msg+"""</div>
                            <p>"""+message[3].replace("\n", "</br>")+"""</p>
                            <h6>"""+message[4]+"""</h6>
                        </body>
                    </html>
                """
        message_preview = wx.html2.WebView.New(self.notebook)
        message_preview.EnableContextMenu(False)
        message_preview.webwatcher_message = message
        message_preview.webwatcher_subject = message[0]
        message_preview.webwatcher_recipients = data["email_addresses"]
        message_preview.webwatcher_val = html_new_msg
        message_preview.webwatcher_new = val
        message_preview.webwatcher_filename = filename
        message_preview.SetPage(html, "")
        num = []
        message_preview.Bind(wx.html2.EVT_WEBVIEW_LOADED, lambda event, message_preview=message_preview, num=num: self.on_webview_loaded(event, message_preview, num))
        self.notebook.AddPage(message_preview, message[0])
        self.plane.Hide()
        self.caught_up_label.Hide()
        self.send_panel.Show()
        self.send_label.Show()
        self.Layout()
        if (self.threads_done >= files_len):
            self.on_finish_check()
        evt = wx.PyCommandEvent(self.NEW_EVENT)
        wx.PostEvent(self, evt)

    def on_webview_loaded(self, event, message_preview, num):
        num.append("")
        if len(num) > 1:
            message_preview.Bind(wx.html2.EVT_WEBVIEW_NAVIGATING, lambda event: event.Veto())

    def update_preview(self, data):
        for num, page in enumerate(self.notebook.GetChildren()):
            if page.webwatcher_filename == data["filename"]:
                message = data["message"]
                page.webwatcher_message = message
                page.webwatcher_subject = message[0]
                page.webwatcher_recipients = data["email_addresses"]
                html = """
                                <html>
                                    <head>
                                    </head>
                                    <body>
                                        <div style="height:3px; width:100%; background-color:black;"></div>
                                        <h5><b>Subject: """+message[0]+"""</b></h5>
                                        <h5><b>To: """+str(page.webwatcher_recipients).replace("[", "").replace("]", "")+"""</b></h5>
                                        <h5><b>From: """+str(self.uname)+"""</b></h5>
                                        <div style="height:3px; width:100%; background-color:black;"></div>
                                        <b><p>"""+message[1]+"""</p></b>
                                        <p>"""+message[2].replace("\n", "</br>")+"""</p>
                                        <div style="width:100%;">"""+page.webwatcher_val+"""</div>
                                        <p>"""+message[3].replace("\n", "</br>")+"""</p>
                                        <h6>"""+message[4]+"""</h6>
                                    </body>
                                </html>
                            """
                page.SetPage(html, "")
                self.notebook.SetPageText(num, message[0])
                self.error_func(data["website"], "Updated SendManager page "+str(page)+" because the message or recipients has changed.", error=False)
                
    def set_credentials(self, uname, passwd):
        self.uname = uname
        self.passwd = passwd

        for page in self.notebook.GetChildren():
            message = page.webwatcher_message
            html = """
                        <html>
                            <head>
                            </head>
                            <body>
                                <div style="height:3px; width:100%; background-color:black;"></div>
                                <h5><b>Subject: """+message[0]+"""</b></h5>
                                <h5><b>To: """+str(page.webwatcher_recipients).replace("[", "").replace("]", "")+"""</b></h5>
                                <h5><b>From: """+str(self.uname)+"""</b></h5>
                                <div style="height:3px; width:100%; background-color:black;"></div>
                                <b><p>"""+message[1]+"""</p></b>
                                <p>"""+message[2].replace("\n", "</br>")+"""</p>
                                <div style="width:100%;">"""+page.webwatcher_val+"""</div>
                                <p>"""+message[3].replace("\n", "</br>")+"""</p>
                                <h6>"""+message[4]+"""</h6>
                            </body>
                        </html>
            """
            page.SetPage(html, "")

class WarningsManager(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
            
        page_sizer = wx.BoxSizer(wx.VERTICAL)
        self.error_list = error_list = wx.ListCtrl(self, style = wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_NONE)
        error_list.InsertColumn(0, 'Warning')
        error_list.InsertColumn(1, 'Url', width=300) 
        self.SetBackgroundColour(error_list.GetBackgroundColour())
        page_sizer.Add(error_list, 1, wx.EXPAND)

        self.SetSizer(page_sizer)

        self.img_list = wx.ImageList(16,16)
        self.error_list.SetImageList(self.img_list, wx.IMAGE_LIST_SMALL)
        image = os.path.join("resources", "warning.png")
        img=wx.Image(image, wx.BITMAP_TYPE_ANY)
        img=wx.Bitmap(img)
        self.browserimg = self.img_list.Add(img)
        image = os.path.join("resources", "error.png")
        img=wx.Image(image, wx.BITMAP_TYPE_ANY)
        img=wx.Bitmap(img)
        self.browserimg2 = self.img_list.Add(img)

        error_list.Bind(wx.EVT_SIZE, self.on_resize)
        error_list.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_right_click)

        self.NEW_EVENT = NEW_EVENT = wx.NewEventType()
        self.EVT_ERROR = wx.PyEventBinder(NEW_EVENT, 1)

    def on_right_click(self, event):
        item = event.GetIndex()
        msg = self.error_list.GetItemText(item, 0)
        url = self.error_list.GetItemText(item, 1)
        
        popupmenu = wx.Menu()
        msg_item = popupmenu.Append(-1, "Copy message")
        url_item = popupmenu.Append(-1, "Copy url")
        
        popupmenu.Bind(wx.EVT_MENU, lambda event: self.copy(event, msg), msg_item)
        popupmenu.Bind(wx.EVT_MENU, lambda event: self.copy(event, url), url_item)

        self.PopupMenu(popupmenu, event.GetPoint())
        
    def copy(self, event, data):
        clipdata = wx.TextDataObject()
        clipdata.SetText(data)
        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(clipdata)
        wx.TheClipboard.Close()
    
    def on_resize(self, event):
        self.error_list.SetColumnWidth(0, ((self.error_list.GetSize()[0])-300))
        self.error_list.Layout()

    def add_warning(self, website, warning, error=True):
        index = self.error_list.GetItemCount()
        if error:
            self.error_list.InsertItem(index, 0)
            self.error_list.SetItem(index, 1, website)
            self.error_list.SetItem(index, 0, warning, self.browserimg2)
            evt = wx.PyCommandEvent(self.NEW_EVENT)
            wx.PostEvent(self, evt)
            
        else:
            self.error_list.InsertItem(index, 0)
            self.error_list.SetItem(index, 1, website)
            self.error_list.SetItem(index, 0, warning, self.browserimg)

    def get_bg(self):
        return self.GetBackgroundColour()


class WebWatcher365(wx.Frame):
    def __init__(self, parent, **kwargs):
        wx.Frame.__init__(self, parent, **kwargs)

        self.cpath = os.path.join(os.path.realpath(os.path.dirname(__file__)))
        os.chdir(self.cpath)

        self.SetMinSize((600,400))
        self.Maximize()
        self.SetIcon(wx.Icon(os.path.join("resources", "webwatcher_icon.ico")))
        
        self.page = page = wx.Panel(self)
        self.sidebar_container = sidebar_container = wx.Panel(page)
        self.sidebar = sidebar = wx.Panel(sidebar_container)
        sidebar2 = wx.Panel(sidebar_container)  
        settings_img = wx.Bitmap(os.path.join("resources", "settings.png"), wx.BITMAP_TYPE_ANY)
        self.send_img = send_img = wx.Bitmap(os.path.join("resources", "send.png"), wx.BITMAP_TYPE_ANY)
        self.send_active_img = send_active_img = wx.Bitmap(os.path.join("resources", "send_active.png"), wx.BITMAP_TYPE_ANY)
        websites_img = wx.Bitmap(os.path.join("resources", "internet.png"), wx.BITMAP_TYPE_ANY)
        self.warnings_img = warnings_img = wx.Bitmap(os.path.join("resources", "warnings.png"), wx.BITMAP_TYPE_ANY)
        self.warnings_active_img = warnings_active_img = wx.Bitmap(os.path.join("resources", "warnings_active.png"), wx.BITMAP_TYPE_ANY)
        self.email_img = email_img = wx.Bitmap(os.path.join("resources", "email.png"), wx.BITMAP_TYPE_ANY)
        self.email_active_img = email_active_img = wx.Bitmap(os.path.join("resources", "email_active.png"), wx.BITMAP_TYPE_ANY)
        quit_img = wx.Bitmap(os.path.join("resources", "quit.png"), wx.BITMAP_TYPE_ANY)
        
        self.settings = settings = wx.BitmapButton(sidebar, bitmap=settings_img, style=wx.BORDER_NONE)
        self.send = send = wx.BitmapButton(sidebar, bitmap=send_img, style=wx.BORDER_NONE)
        self.websites = websites = wx.BitmapButton(sidebar, bitmap=websites_img, style=wx.BORDER_NONE)
        self.warnings = warnings = wx.BitmapButton(sidebar, bitmap=warnings_img, style=wx.BORDER_NONE)
        self.email = email = wx.BitmapButton(sidebar, bitmap=email_img, style=wx.BORDER_NONE)
        self.quit_button = quit_button = wx.BitmapButton(sidebar, bitmap=quit_img, style=wx.BORDER_NONE)

        self.warnings_manager = warnings_manager = WarningsManager(page)
        self.website_manager = website_manager = WebsiteManager(page)
        self.settings_manager = settings_manager = SettingsManager(page)
        self.error_func = warnings_manager.add_warning
        self.send_manager = send_manager = SendManager(page, self.error_func)
        self.email_manager = email_manager = EmailViewer(page, self.error_func)

        self.buttons = {}
        self.buttons[warnings] = {"icon-active":warnings_active_img, "icon-inactive":warnings_img, "page":warnings_manager}
        self.buttons[websites] = {"icon-active":websites_img, "icon-inactive":websites_img, "page":website_manager}
        self.buttons[settings] = {"icon-active":settings_img, "icon-inactive":settings_img, "page":settings_manager}
        self.buttons[send] = {"icon-active":send_active_img, "icon-inactive":send_img, "page":send_manager}
        self.buttons[email] = {"icon-active":email_active_img, "icon-inactive":email_img, "page":email_manager}
        
        settings.SetToolTip("Preferences") 
        send.SetToolTip("Webpage updates") 
        websites.SetToolTip("Webpage manager")
        warnings.SetToolTip("Warnings")
        email.SetToolTip("Messages") 
        quit_button.SetToolTip("Quit") 
        
        page_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sidebar_sizer = sidebar_sizer = wx.BoxSizer(wx.VERTICAL)
        self.page_content_sizer = page_content_sizer = wx.BoxSizer(wx.VERTICAL)
        sidebar_container_sizer = wx.BoxSizer(wx.HORIZONTAL)
        page_sizer.Add(sidebar_container, 0, wx.EXPAND)
        sidebar_container_sizer.Add(sidebar, 0, wx.CENTER)
        sidebar_container_sizer.Add(sidebar2, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 70)
        sidebar_container_sizer.Add((0,0), 0, wx.RIGHT, 10)
        page_sizer.Add(page_content_sizer, 1, wx.EXPAND)
        sidebar_sizer.Add(send, 0, wx.RIGHT | wx.LEFT | wx.TOP | wx.CENTER, 7)
        sidebar_sizer.Add(websites, 0, wx.RIGHT | wx.LEFT | wx.TOP, 7)
        sidebar_sizer.Add(settings, 0, wx.RIGHT | wx.LEFT | wx.TOP, 7)
        sidebar_sizer.Add(warnings, 0, wx.RIGHT | wx.LEFT | wx.TOP, 7)
        sidebar_sizer.Add(email, 0, wx.RIGHT | wx.LEFT | wx.TOP, 7)
       
        page_content_sizer.Add(website_manager, 1, wx.EXPAND)
        page_content_sizer.Add(settings_manager, 1, wx.EXPAND)
        page_content_sizer.Add(warnings_manager, 1, wx.EXPAND)
        page_content_sizer.Add(send_manager, 1, wx.EXPAND)
        page_content_sizer.Add(email_manager, 1, wx.EXPAND)
        
        self.load_plugins()

        sidebar_sizer.Add(quit_button, 0, wx.ALL, 7)

        sidebar2.SetBackgroundColour((0,0,0))

        settings.Bind(wx.EVT_BUTTON, self.on_sidebar_click, settings)
        website_manager.Bind(website_manager.EVT_CHANGE, self.on_site_settings_change)
        send.Bind(wx.EVT_BUTTON, self.on_sidebar_click, send)
        websites.Bind(wx.EVT_BUTTON, self.on_sidebar_click, websites)
        warnings.Bind(wx.EVT_BUTTON, self.on_sidebar_click, warnings)
        email.Bind(wx.EVT_BUTTON, self.on_sidebar_click, email)
        quit_button.Bind(wx.EVT_BUTTON, self.on_close)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        warnings_manager.Bind(warnings_manager.EVT_ERROR, lambda event, btn=warnings: self.action_needed(event, btn))
        send_manager.Bind(send_manager.EVT_ACTION_NEEDED, lambda event, btn=send: self.action_needed(event, btn))
        send_manager.Bind(send_manager.EVT_SENT, self.on_send_all)
        send_manager.Bind(send_manager.EVT_DONE_CHECKING, self.on_send_done_checking)
        send_manager.Bind(send_manager.EVT_DONE_SENDING_ALL, self.on_send_all_done)
        settings_manager.Bind(settings_manager.EVT_EMAIL_CHANGE, self.on_email_change)
        email_manager.Bind(email_manager.EVT_UNREAD_MESSAGES, lambda event, btn=email: self.action_needed(event, btn))
        
        self.selectpage(send)
        
        sidebar_container.SetSizer(sidebar_container_sizer)
        sidebar.SetSizer(sidebar_sizer)
        page.SetSizer(page_sizer)
        self.load_websites_from_disk()
        self.load_settings_from_disk()

    def load_plugins(self):
        sys.path.append(os.path.join(self.cpath, "plugins"))
        plugins = []
        for file in os.listdir("plugins"):
            if os.path.isfile(os.path.join(self.cpath, "plugins", file)):
                if file != "__init__.py":
                    if file.endswith(".py"):
                        self.error_func("file://"+(os.path.join(self.cpath, "plugins")), "Found plugin: "+str(file), error=False)
                        plugins.append(os.path.splitext(file)[0])

        for plugin_name in plugins:
            try:
                module = importlib.import_module(plugin_name)

                plugin = module.WebWatcherPlugin(self.page, self.settings_manager, self.error_func)

                self.settings_manager.add_panel(plugin.webwatcher_settings_box, plugin.name)
                
                plugin_image = wx.Bitmap(plugin.image, wx.BITMAP_TYPE_ANY)
                plugin_button = wx.BitmapButton(self.sidebar, bitmap=plugin_image, style=wx.BORDER_NONE)
                plugin_image_active = wx.Bitmap(plugin.image_active, wx.BITMAP_TYPE_ANY)
                self.buttons[plugin_button] = {"icon-active":plugin_image_active, "icon-inactive":plugin_image, "page":plugin}
                plugin_button.SetToolTip(plugin.name)
                self.sidebar_sizer.Add(plugin_button, 0, wx.RIGHT | wx.LEFT | wx.TOP, 7)
                self.page_content_sizer.Add(plugin, 1, wx.EXPAND)
                plugin_button.Bind(wx.EVT_BUTTON, self.on_sidebar_click, plugin_button)
                plugin.Bind(plugin.evt_active, lambda event, btn=plugin_button: self.action_needed(event, btn))
                self.error_func("file://"+(module.__file__), "Successfully loaded plugin "+str(plugin.name)+"", error=False)
            except Exception:
                self.error_func("file://"+(os.path.join(self.cpath, "plugins", (str(plugin_name)+".py"))), "Error loading plugin '"+str(plugin_name)+"'")

    def selectpage(self, btn):
        evt = wx.CommandEvent(wx.EVT_BUTTON.typeId)
        evt.SetEventObject(btn)
        evt.SetId(btn.GetId())
        btn.GetEventHandler().ProcessEvent(evt)

    def action_needed(self, event, btn):
        if not self.buttons[btn]["page"].IsShown():
            btn.SetBitmap(self.buttons[btn]["icon-active"])
        if not self.IsShown():
            self.Show()
            self.selectpage(btn)

    def on_send_done_checking(self, event):
        if not self.IsShown():
            self.Destroy()

    def on_send_all(self, event):
        send_and_stay = True
        try:
            with open(os.path.join("resources", "settings.json"), "r") as f:
                settings = ast.literal_eval(f.read())
            send_and_stay = settings["send_and_stay"]
        except Exception as e:
            self.error_func("file://"+(os.path.join(self.cpath, "resources", "settings.json")), "Error reading settings file: "+str(e))
        if not send_and_stay:
            self.Hide()

    def on_send_all_done(self, event):
        send_and_stay = True
        try:
            with open(os.path.join("resources", "settings.json"), "r") as f:
                settings = ast.literal_eval(f.read())
            send_and_stay = settings["send_and_stay"]
        except Exception as e:
            self.error_func("file://"+(os.path.join(self.cpath, "resources", "settings.json")), "Error reading settings file: "+str(e))
            self.Show()
        if not send_and_stay:
            self.Destroy()

    def load_websites_from_disk(self):
        files = []
        for file in glob.glob("websites/*.json"):
            files.append(file)
            self.error_func("file://"+(os.path.join(self.cpath, file)), "File found in "+(os.path.join(self.cpath, "websites")), error=False)
        files_len = len(files)
        if files_len == 0:
            self.Show()
        for file in files:
            with open(file, 'r') as f:
                websites = ast.literal_eval(f.read())
                self.website_manager.add_site(websites, filename=file)
                self.send_manager.check(websites, file, files_len)

    def load_settings_from_disk(self):
        try:
            with open(os.path.join("resources", "settings.json"), "r") as f:
                settings = ast.literal_eval(f.read())
            uname = settings["uname"]
            can_show = bool(settings["always_open"])
            if can_show:
                self.Show()
            send_and_stay = bool(settings["send_and_stay"])
            if uname is not None:
                passwd = keyring.get_password("WebWatcher365", uname)
                if passwd is not None:
                    self.send_manager.set_credentials(uname, passwd)
                    self.settings_manager.set_credentials(uname, passwd)
                    self.email_manager.set_credentials(uname, passwd)
                else:
                    self.open_email_dialog()                    
            else:
                self.open_email_dialog()
        except Exception as e:
            self.Show()
            self.error_func("file://"+(os.path.join(self.cpath, "resources", "settings.json")), "Error reading settings file: "+str(e))
            settings = {"uname":None, "always_open":True, "send_and_stay":True}
            with open(os.path.join("resources", "settings.json"), "w+") as f:
                f.write(str(settings))
            self.open_email_dialog()
            self.settings_manager.config()

    def on_site_settings_change(self, event):
        self.send_manager.update_preview(event.GetValue())
                             
    def open_email_dialog(self):
        dialog = EmailDialog(self, title="WebWatcher365")
        dialog.SetIcon(wx.Icon(os.path.join("resources", "webwatcher_icon.ico")))
        dialog.Bind(wx.EVT_CLOSE, self.on_close)
        dialog.Bind(dialog.EVT_FINISH, lambda event, dialog=dialog: self.on_email_finish(event, dialog))
        dialog.ShowModal()
        
    def on_email_finish(self, event, dialog):
        credentials = event.GetValue()
        self.send_manager.set_credentials(credentials[0], credentials[1])
        self.settings_manager.set_credentials(*credentials)
        self.email_manager.set_credentials(credentials[0], credentials[1])
        dialog.Destroy()
        
    def on_email_change(self, event):
        credentials = event.GetValue()
        self.send_manager.set_credentials(credentials[0], credentials[1])
        self.email_manager.set_credentials(credentials[0], credentials[1])
            
    def on_sidebar_click(self, event):
        name = event.GetEventObject()
        
        for widget in self.sidebar_sizer.GetChildren():
            widget = widget.GetWindow()
            if widget != name:
                if widget != self.quit_button:
                    widget.Enable()
                    self.buttons[widget]["page"].Hide()

        name.Disable()
        self.buttons[name]["page"].Show()
        self.sidebar_container.SetBackgroundColour(self.buttons[name]["page"].GetBackgroundColour())

        if name != self.quit_button:
            name.SetBitmap(self.buttons[name]["icon-inactive"])

        self.page.Layout()
        
    def on_close(self, event):
        close_message = wx.MessageDialog(None, "Are you sure you want to quit?", "Quit", wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION).ShowModal()
        if close_message == wx.ID_YES:
            self.email_manager.logout()
            self.Destroy()