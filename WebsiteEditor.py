import os
import re

import wx
import wx.adv
import wx.html2

from SetupFrame import Page


class AddressesEditor(Page):
    def __init__(self, parent, addresses):
        Page.__init__(self, parent=parent)
        
        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        horizontal_sizer = wx.BoxSizer(wx.HORIZONTAL)
        add_or_remove_sizer = wx.BoxSizer(wx.HORIZONTAL)
        vertical_content_sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.list_box = list_box = wx.ListBox(self, size=(-1, 150))
        self.email_input = email_input = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        height = (email_input.GetSize()[1])
        add_icon = wx.Bitmap(os.path.join(os.path.dirname(os.path.realpath(__file__)), "resources", "add.png"), wx.BITMAP_TYPE_ANY)
        remove_icon = wx.Bitmap(os.path.join(os.path.dirname(os.path.realpath(__file__)), "resources", "remove.png"), wx.BITMAP_TYPE_ANY)
        add_button = wx.BitmapButton(self, -1, add_icon, size=(height,height))
        self.remove_button = remove_button = wx.BitmapButton(self, -1, remove_icon, size=(height,height))

        remove_button.Disable()

        vertical_sizer.Add(horizontal_sizer, 1, wx.EXPAND)
        horizontal_sizer.Add(vertical_content_sizer, 1, wx.CENTER | wx.EXPAND | wx.ALL, 50)
        vertical_content_sizer.Add(add_or_remove_sizer, 0, wx.CENTRE | wx.EXPAND | wx.BOTTOM, 5)
        vertical_content_sizer.Add(list_box, 1, wx.EXPAND)
        add_or_remove_sizer.Add(email_input, 1)
        add_or_remove_sizer.Add(add_button, 0, wx.CENTRE)
        add_or_remove_sizer.Add(remove_button, 0, wx.CENTRE)

        list_box.Bind(wx.EVT_LISTBOX, self.on_selection_change)
        add_button.Bind(wx.EVT_BUTTON, self.add_email)
        remove_button.Bind(wx.EVT_BUTTON, self.remove_email)
        email_input.Bind(wx.EVT_TEXT_ENTER, self.add_email)
        email_input.Bind(wx.EVT_TEXT, lambda e: email_input.SetBackgroundColour((-1, -1, -1)))
        
        self.SetSizer(vertical_sizer)

        list_box.InsertItems(addresses, 0)

    def on_selection_change(self, event):
        self.remove_button.Enable()

    def add_email(self, event=None):
        val = self.email_input.GetValue()
        if re.match("[^@]+@[^@]+\.[^@]+", val):
            if val not in self.list_box.GetStrings():
                self.email_input.SetValue("")
                self.list_box.InsertItems([val], 0)
            else:
                self.email_input.SetBackgroundColour((255, 11, 0)) 
        else:
            self.email_input.SetBackgroundColour((255, 11, 0))

    def remove_email(self, event):
        item = self.list_box.GetSelection()
        delete = wx.MessageDialog(None, "Are you sure you want to remove the email address '"+self.list_box.GetString(item)+"'?", "Confirm delete", wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION).ShowModal()
        if delete == wx.ID_YES:
            self.list_box.Delete(item)

    def return_data(self):
        settings_dict = {
            "email_addresses":self.list_box.GetStrings()   
            }
        return settings_dict


class MessageEditor(Page):
    def __init__(self, parent, messages):
        Page.__init__(self, parent=parent)
        
        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        horizontal_sizer = wx.BoxSizer(wx.HORIZONTAL)
        input_sizer = wx.FlexGridSizer(8, 2, 5, 5)
        self.title_input = title_input = wx.TextCtrl(self)
        self.caption_input = caption_input = wx.TextCtrl(self)
        self.body_1_input = body_1_input = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        self.body_2_input = body_2_input = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        self.additional_input = additional_input = wx.TextCtrl(self)
        title_input.SetValue(messages[0])
        caption_input.SetValue(messages[1])
        body_1_input.SetValue(messages[2])
        body_2_input.SetValue(messages[3])
        additional_input.SetValue(messages[4])

        vertical_sizer.Add(horizontal_sizer, 1, wx.EXPAND)
        horizontal_sizer.Add(input_sizer, 1, wx.CENTER | wx.EXPAND | wx.ALL, 30)
        input_sizer.AddGrowableRow(2, 1)
        input_sizer.AddGrowableRow(4, 1)
        input_sizer.AddGrowableRow(6, 1)
        input_sizer.AddGrowableCol(1, 2)
        input_sizer.Add(wx.StaticText(self, label="Subject"))
        input_sizer.Add(title_input, 1, wx.EXPAND)
        input_sizer.Add(wx.StaticText(self, label="Heading"))
        input_sizer.Add(caption_input, 1, wx.EXPAND)
        input_sizer.Add(wx.StaticText(self, label="Text"))
        input_sizer.Add(body_1_input, 1, wx.EXPAND)
        input_sizer.Add(wx.StaticText(self, label="Website snippet (updated)"))
        input_sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)
        input_sizer.Add(wx.StaticText(self, label="Text"))
        input_sizer.Add(body_2_input, 1, wx.EXPAND)
        input_sizer.Add(wx.StaticText(self, label="Additional details"))
        input_sizer.Add(additional_input, 1, wx.EXPAND)        
        self.SetSizer(vertical_sizer)

    def return_data(self):
        settings_dict = {
            "message":[self.title_input.GetValue(),
                       self.caption_input.GetValue(),
                       self.body_1_input.GetValue().replace("\n", "</br>"),
                       self.body_2_input.GetValue().replace("\n", "</br>"),
                       self.additional_input.GetValue()]
            }
        return settings_dict


class WebsiteEditor(wx.Frame):
    def __init__(self, parent, addresses, messages, **kwargs):
        wx.Frame.__init__(self, parent, **kwargs)
        page = wx.Panel(self)
        page_sizer = wx.BoxSizer(wx.VERTICAL)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        notebook = wx.Notebook(page)
        self.page1 = page1 = AddressesEditor(notebook, addresses)
        self.page2 = page2 = MessageEditor(notebook, messages)
        save_button = wx.Button(page, -1, "Save")
        notebook.AddPage(page1, "Recipents")
        notebook.AddPage(page2, "Message")
        page_sizer.Add(notebook, 1, wx.EXPAND | wx.ALL, 5)
        page_sizer.Add(button_sizer, 0, wx.ALIGN_RIGHT)
        button_sizer.Add(save_button, 0, wx.ALL, 5)

        save_button.Bind(wx.EVT_BUTTON, self.on_save)
        page.SetSizer(page_sizer)
        self.Show()

    def on_save(self, event):
        if len(self.page1.return_data()["email_addresses"]) == 0:
            self.page1.add_email()
        else:
            self.Close()

    def return_data(self):
        settings = {}
        settings.update(self.page1.return_data())
        settings.update(self.page2.return_data())
        return settings
