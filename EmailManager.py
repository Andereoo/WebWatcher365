import email
import imaplib
import os
import threading
import webbrowser
from email.header import decode_header

import keyring
import wx
import wx.adv
import wx.html2
import wx.lib.platebtn

from Threads import SendEmailThread


class EmailComposer(wx.Frame):
    def __init__(self, parent, onsend, **kwargs):
        wx.Frame.__init__(self, parent, **kwargs)

        self.SetTitle("Compose message")

        panel = wx.Panel(self)
        page_sizer = wx.BoxSizer(wx.VERTICAL)
        to_sizer = wx.BoxSizer(wx.HORIZONTAL)
        subject_sizer = wx.BoxSizer(wx.HORIZONTAL)
        send_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.onsend = onsend
        self.to_ctrl = to_ctrl = wx.TextCtrl(panel)
        self.subject_ctrl = subject_ctrl = wx.TextCtrl(panel)
        self.body_ctrl = body_ctrl = wx.TextCtrl(panel, style=wx.TE_MULTILINE)
        cancel_btn = wx.Button(panel, label="Cancel")
        send_btn = wx.Button(panel, label="Send")

        page_sizer.Add(to_sizer, 0, wx.EXPAND | wx.ALL, 5)
        to_sizer.Add(wx.StaticText(panel, label="To: ", size=(60, -1)))
        to_sizer.Add(to_ctrl, 1)
        page_sizer.Add(subject_sizer, 0, wx.EXPAND | wx.ALL, 5)
        subject_sizer.Add(wx.StaticText(panel, label="Subject: ", size=(60, -1)))
        subject_sizer.Add(subject_ctrl, 11)
        page_sizer.Add(body_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        page_sizer.Add(send_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        send_sizer.Add(cancel_btn, 0, wx.RIGHT, 5)
        send_sizer.Add(send_btn)

        cancel_btn.Bind(wx.EVT_BUTTON, lambda event: self.Destroy())
        send_btn.Bind(wx.EVT_BUTTON, self.on_send)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        to_ctrl.Bind(wx.EVT_TEXT, lambda e: to_ctrl.SetBackgroundColour(wx.NullColour))
        subject_ctrl.Bind(wx.EVT_TEXT, lambda e: subject_ctrl.SetBackgroundColour(wx.NullColour))
        body_ctrl.Bind(wx.EVT_TEXT, lambda e: body_ctrl.SetBackgroundColour(wx.NullColour))

        panel.SetSizer(page_sizer)

    def on_close(self, event):
        to = self.to_ctrl.GetValue()
        subj = self.subject_ctrl.GetValue()
        text = self.body_ctrl.GetValue()

        if to != "":
            self.open_close_dialog()
        elif subj != "":
            self.open_close_dialog()
        elif text != "":
            self.open_close_dialog()
        else:
            self.Destroy()

    def on_send(self, event):
        to = self.to_ctrl.GetValue()
        subj = self.subject_ctrl.GetValue()
        text = self.body_ctrl.GetValue()
        can_cont = True
        if to == "":
            self.to_ctrl.SetBackgroundColour("red")
            can_cont = False
        elif subj == "":
            self.subject_ctrl.SetBackgroundColour("red")
            can_cont = False
        elif text == "":
            self.body_ctrl.SetBackgroundColour("red")
            can_cont = False
        if can_cont:
            self.Destroy()
            self.onsend(text.replace("\n", "</br>"), to, subj)

    def open_close_dialog(self):
        close_message = wx.MessageDialog(None, "Are you sure you want to close this? Your work will not be saved.", "Quit", wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION).ShowModal()
        if close_message == wx.ID_YES:
            self.Destroy()
        

class EmailViewer(wx.Panel):
    def __init__(self, parent, error_func, **kwargs):
        wx.Panel.__init__(self, parent, **kwargs)
        self.folders = []
        self.cmsg = None
        self.error_func = error_func
        page_sizer = wx.BoxSizer(wx.VERTICAL)
        horizontal_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.button_sizer = button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.msg_sizer = msg_sizer = wx.BoxSizer(wx.VERTICAL)
        self.folder_btn = folder_btn = wx.Button(self, label="Inbox", size=(300, -1))
        self.loading_wheel = loading_wheel = wx.adv.AnimationCtrl(self, -1, wx.adv.Animation(os.path.join("resources", 'loading.gif')), size=(20,20))
        moveto_btn = wx.Button(self, label="Move")
        delete_btn = wx.Button(self, label="Delete")
        refresh_btn = wx.Button(self, label="Refresh")
        compose_btn = wx.Button(self, label="Compose")
        self.button_container = button_container = wx.ScrolledWindow(self, size=(300, -1))
        self.preview_win = preview_win = wx.html2.WebView.New(self)
        horizontal_sizer.Add(button_container, 0, wx.EXPAND | wx.ALL, 5)
        horizontal_sizer.Add(preview_win, 1, wx.EXPAND | wx.ALL, 5)
        button_container.SetSizer(msg_sizer)
        page_sizer.Add(button_sizer, 0, wx.EXPAND)
        page_sizer.Add(horizontal_sizer, 1, wx.EXPAND)
        self.SetSizer(page_sizer)
        button_sizer.Add(folder_btn, 0, wx.ALL, 5)
        button_sizer.Add((0,0), 1)
        button_sizer.Add(loading_wheel, 0, wx.ALL | wx.ALIGN_CENTRE_VERTICAL, 5)
        button_sizer.Add(moveto_btn, 0, wx.ALL, 5)
        button_sizer.Add(delete_btn, 0, wx.ALL, 5)
        button_sizer.Add(refresh_btn, 0, wx.ALL, 5)
        button_sizer.Add(compose_btn, 0, wx.ALL, 5)
        button_container.SetScrollbars(1, 1, 1, 1)
        preview_win.Bind(wx.html2.EVT_WEBVIEW_NEWWINDOW, self.on_new_win)
        folder_btn.Bind(wx.EVT_BUTTON, self.choose_folder)
        moveto_btn.Bind(wx.EVT_BUTTON, self.move_message)
        delete_btn.Bind(wx.EVT_BUTTON, self.delete_message)
        refresh_btn.Bind(wx.EVT_BUTTON, self.refresh_message)
        compose_btn.Bind(wx.EVT_BUTTON, self.compose_message)
        self.NEW_EVENT = NEW_EVENT = wx.NewEventType()
        self.EVT_UNREAD_MESSAGES = wx.PyEventBinder(NEW_EVENT, 1)
        self.SetBackgroundColour(self.GetBackgroundColour())
        self.lw_stop()
        self.Disable()
        
    def lw_go(self):
        self.loading_wheel.Play()
        self.loading_wheel.Show()
        self.button_sizer.Layout()

    def lw_stop(self):
        self.loading_wheel.Stop()
        self.loading_wheel.Hide()
        
    def on_new_win(self, event):
        webbrowser.open(event.URL)
        
    def choose_folder(self, event):
        choose = wx.Dialog(self, style=wx.NO_BORDER | wx.CAPTION, size=(300,300))
        page_sizer = wx.BoxSizer(wx.VERTICAL)
        panel = wx.ScrolledWindow(choose)
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetScrollbars(1, 1, 1, 1)
        panel.SetSizer(panel_sizer)
        closebtn = wx.Button(choose, label="Close")
        closebtn.Bind(wx.EVT_BUTTON, lambda event: choose.Close())

        for folder in self.folders:
            button = wx.lib.platebtn.PlateButton(panel, label=folder, style=wx.lib.platebtn.PB_STYLE_SQUARE, size=(-1, 45))
            panel_sizer.Add(button, 0, wx.EXPAND | wx.ALIGN_CENTRE_HORIZONTAL)
            button.Bind(wx.EVT_BUTTON, lambda event, dialog=choose, folder=folder: self.select_folder(event, dialog, folder))

        page_sizer.Add(panel, 1, wx.EXPAND)
        page_sizer.Add(closebtn, 0, wx.CENTRE)
        choose.SetSizer(page_sizer)
        choose.ShowModal()

    def move_message(self, event):
        choose = wx.Dialog(self, style=wx.NO_BORDER | wx.CAPTION, size=(300,300))
        page_sizer = wx.BoxSizer(wx.VERTICAL)
        panel = wx.ScrolledWindow(choose)
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetScrollbars(1, 1, 1, 1)
        panel.SetSizer(panel_sizer)
        closebtn = wx.Button(choose, label="Cancel")
        closebtn.Bind(wx.EVT_BUTTON, lambda event: choose.Close())

        for folder in self.folders:
            button = wx.lib.platebtn.PlateButton(panel, label=folder, style=wx.lib.platebtn.PB_STYLE_SQUARE, size=(-1, 45))
            panel_sizer.Add(button, 0, wx.EXPAND | wx.ALIGN_CENTRE_HORIZONTAL)
            button.Bind(wx.EVT_BUTTON, lambda event, dialog=choose, folder=folder: self.cont_move_message(event, dialog, folder))

        page_sizer.Add(wx.StaticText(choose, label="Please select the mailbox."), 0, wx.ALIGN_CENTRE_HORIZONTAL | wx.CENTRE)
        page_sizer.Add(panel, 1, wx.EXPAND)
        page_sizer.Add(closebtn, 0, wx.CENTRE)
        choose.SetSizer(page_sizer)
        choose.ShowModal()

    def logout(self):
        try:
            self.imap.select("INBOX")
            self.imap.close()
            self.imap.logout()
        except:
            pass

    def cont_move_message(self, event, dialog, folder):
        try:
            message = self.cmsg
            result = self.imap.uid('COPY', message, folder)
            if result[0] == 'OK':
                mov, data = self.imap.uid('STORE', message, '+FLAGS', '(\Deleted)')
                self.imap.expunge()

            self.select_folder(event, dialog, self.folder_btn.GetLabel())
        except Exception as e:
            self.error_func("file://"+__file__, "Error moving message: "+str(e))
        
    def delete_message(self, event):
        cfolder = self.folder_btn.GetLabel()
        if ("Bin" in cfolder) or ("Trash" in cfolder):
            mov, data = self.imap.uid('STORE', self.cmsg , '+FLAGS', '(\Deleted)')
            self.imap.expunge()
            self.select_folder(None, None, cfolder)
        else:
            for folder in self.folders:
                if ("Bin" in folder) or ("Trash" in folder):
                    self.cont_move_message(None, None, folder)
                    break

    def refresh_message(self, event):
        try:
            self.search_for_messages(None, None, self.folder_btn.GetLabel())
        except AttributeError:
            self.login()

    def select_folder(self, event, dialog, folder):
        self.lw_go()
        thread = threading.Thread(target=lambda event=event, dialog=dialog, folder=folder: self.search_for_messages(event, dialog, folder))
        thread.start()
        
    def search_for_messages(self, event, dialog, folder):
        wx.CallAfter(lambda dialog=dialog, folder=folder: self.refresh_widgets(dialog, folder))
        x, y = self.imap.select(folder)
            
        result2, data2 = self.imap.uid('search', None, "UNSEEN")#self.imap.search(None, '(UNSEEN)')
        messages2 = data2[0].split()
        if len(messages2) != 0:
            wx.CallAfter(self.post_unseen_evt)
        result, data = self.imap.uid('search', None, "(SEEN)")
        messages = data[0].split()
        col1, col2, col3, col4 = (self.GetBackgroundColour())
        if (len(messages) == 0):
            if (len(messages2) == 0):
                self.preview_win.SetPage("""<html><body style="background-color:rgb"""+str((col1,col2,col3))+""""><div style="position: fixed; bottom: 0; right: 10; "><h5 style="text-align:right;">You're all caught up!</h5></div></body></html>""", "")
            else:
                self.preview_win.SetPage("""<html><body style="background-color:rgb"""+str((col1,col2,col3))+""""></body></html>""", "")
        else:
            self.preview_win.SetPage("""<html><body style="background-color:rgb"""+str((col1,col2,col3))+""""></body></html>""", "")
        self.show_messages(messages2, False)
        self.show_messages(messages, True)
        wx.CallAfter(self.finish_search)

    def finish_search(self):
        self.Enable()
        self.lw_stop()

    def post_unseen_evt(self):
        evt = wx.PyCommandEvent(self.NEW_EVENT)
        wx.PostEvent(self, evt)

    def refresh_widgets(self, dialog, folder, *args):
        if dialog:
            dialog.Close()
        for widget in self.msg_sizer.GetChildren():
            widget = widget.GetWindow()
            widget.Destroy()
        col1, col2, col3, col4 = (self.GetBackgroundColour())
        self.msg_sizer.Layout()
        self.folder_btn.SetLabel(folder)

    def set_credentials(self, uname, passwd):
        self.lw_go()
        self.uname = uname
        self.passwd = passwd
        thread = threading.Thread(target=self.login)
        thread.start()

    def login(self):
        try:
            self.imap = imap = imaplib.IMAP4_SSL("imap.gmail.com")
            imap.login(self.uname, self.passwd)
            self.get_folders()
            self.search_for_messages(None, None, self.folder_btn.GetLabel())
        except Exception as e:
            self.error_func("file://"+__file__, "Error logging in: "+str(e))
            self.lw_stop()
            self.Enable()
            col1, col2, col3, col4 = (self.GetBackgroundColour())
            self.preview_win.SetPage("""<html><body style="background-color:rgb"""+str((col1,col2,col3))+""""><div style="position: fixed; bottom: 0; right: 10; "><h5 style="text-align:right;">Can't login...</h5><p style="text-align:right;">Please check your network connection and refresh.</p></div></body></html>""", "")
    
    def get_folders(self):
        imap = self.imap
        self.folders = []
        for i in imap.list()[1]:
            l = i.decode().split(' "/" ')
            l1 = l[1].replace('"', "")
            try:
                if (not l1.startswith("[")) or (not l1.endswith("]")):
                    if not "Drafts" in l1:
                        imap.select(l1)
                        self.folders.append(l1)
            except:
                continue

    def send_msg(self, html, recipients, subject):
        self.lw_go()
        worker = SendEmailThread(self, html, [recipients], subject, self.uname, self.passwd)
        worker.start()
        self.Bind(worker.EVT_SENT, self.on_sent)

    def on_sent(self, event):
        error = event.GetError()
        if error:
            self.error_func("file://"+__file__, "Error sending email: "+str(error))
        else:
            self.error_func("file://"+__file__, "Successfully sent message", error=False)
        self.lw_stop()
        
    def compose_message(self, event):
        compose = EmailComposer(self, self.send_msg)
        compose.Show()

    def create_message_button(self, subject, from_, message, message_uid, attachment, seen):   
        button = wx.Button(self.button_container, label=subject+"\n"+from_, style=wx.BORDER_NONE | wx.BU_LEFT)
        button.Bind(wx.EVT_BUTTON, lambda event, message=message, message_uid=message_uid, button=button: self.on_button_press(event, message, message_uid, button))
        self.msg_sizer.Add(button, flag=wx.EXPAND)
        self.msg_sizer.Layout()
        if seen:
            button.SetForegroundColour(wx.Colour(120, 120, 120))
        else:
            button.SetForegroundColour(wx.Colour(0, 0, 0))

    def on_button_press(self, event, message, message_uid, button):
        self.imap.uid('STORE', message_uid, '+FLAGS', '\SEEN')
        
        self.cmsg = message_uid
        for widget in self.button_container.GetChildren():
            widget.SetBackgroundColour(wx.Colour("white"))
        button.SetBackgroundColour(wx.Colour(191, 191, 191))
        button.SetForegroundColour(wx.Colour(120, 120, 120))
        self.preview_win.SetPage(message, "")

    def show_messages(self, messages, seen):
        imap = self.imap
        for i in range(len(messages)):
            message_uid = (messages[i])
            i = i+1
            if i == 0:
                break
            res, msg1 = imap.fetch(str(i), "(BODY.PEEK[])")
            for response in msg1:
                if isinstance(response, tuple):
                    msg = email.message_from_bytes(response[1])        
                    subject = decode_header(msg["Subject"])[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode()
                    from_ = msg.get("From")
                    attachment = None
                    
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            try:
                                body = part.get_payload(decode=True).decode()
                            except:
                                pass
                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                message = body
                                message_text = body
                            elif "attachment" in content_disposition:
                                attachment = part
                                """filename = part.get_filename()
                                print(filename, part)
                                open(filename, "wb").write(part.get_payload(decode=True))"""
                    else:
                        content_type = msg.get_content_type()
                        body = msg.get_payload(decode=True).decode()
                        if content_type == "text/plain":
                            message = body
                            message_text = body
                    if content_type == "text/html":
                        message = body
                    wx.CallAfter(lambda subject=subject,
                                 from_=from_,
                                 message=message,
                                 message_uid=message_uid,
                                 attachment=attachment,
                                 seen=seen: self.create_message_button(subject, from_, message, message_uid, attachment, seen))



def main():
    app = wx.App()
    win = wx.Frame(None)
    def efunc(file, file2, error=None):
        print(file)
        print(file2)
        print(error)
    email_viewer = EmailViewer(win, efunc)
    win.Show()
    email_viewer.set_credentials("WebWatcherNotifier365@gmail.com", "p6JQvpX4RxrBuuj")
    def onclose(e):
        win.Hide()
        email_viewer.logout()
        app.Destroy()
    win.Bind(wx.EVT_CLOSE, onclose)
    app.MainLoop()

if __name__ == "__main__":
    main()
