import os
import re
from urllib.request import Request, urlopen

import wx

from Threads import Bs4Thread


class Page(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent)
        
    def pass_data(self, data):
        return None

    def return_data(self):
        return {}


class PageOne(Page):
    def __init__(self, parent, on_continue, on_back):
        Page.__init__(self, parent=parent)

        self.on_continue = on_continue
        
        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        horizontal_sizer = wx.BoxSizer(wx.HORIZONTAL)
        vertical_content_sizer = wx.BoxSizer(wx.VERTICAL)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.introduction_text = introduction_text = wx.StaticText(self, label="What website would you like to add?", style = wx.ALIGN_CENTRE_HORIZONTAL)
        self.input_box = input_box = wx.TextCtrl(self, -1, style=wx.TE_PROCESS_ENTER)
        self.continue_button = continue_button = wx.Button(self, label='Next >')
        
        continue_button.Disable()
        
        vertical_sizer.Add(horizontal_sizer, 1, wx.CENTRE | wx.EXPAND)
        horizontal_sizer.Add(vertical_content_sizer, 1, wx.CENTRE, wx.EXPAND)
        vertical_content_sizer.Add(introduction_text, 0, wx.CENTRE | wx.BOTTOM, 5)
        vertical_content_sizer.Add(input_box, 0, wx.EXPAND | wx.RIGHT | wx.LEFT, 80)
        vertical_sizer.Add(button_sizer, 0, wx.RIGHT | wx.ALIGN_RIGHT | wx.BOTTOM, 5)
        button_sizer.Add(continue_button)

        continue_button.Bind(wx.EVT_BUTTON, self.check_url)
        self.input_box.Bind(wx.EVT_TEXT, self.verify)
        self.input_box.Bind(wx.EVT_TEXT_ENTER, self.check_url)

        self.SetSizer(vertical_sizer)

    def verify(self, event):
        if self.input_box.GetValue() != "":
            self.continue_button.Enable()
        else:
            self.continue_button.Disable()

    def check_url(self, event):
        if not self.continue_button.IsEnabled():
            return
        
        self.introduction_text.SetLabel("Checking URL.")
        self.Disable()
        url = self.input_box.GetValue()
        if not url.startswith("https://"):
            if not url.startswith("http://"):
                url = "https://"+url
                self.input_box.SetValue(url)
        try:
            urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}))
            self.introduction_text.SetLabel("What website would you like to add?")
            self.on_continue(pass_data=url)
        except Exception:
            self.introduction_text.SetLabel("Oops. That URL could not be reached.")
        self.Enable()
        

class PageTwo(Page):
    def __init__(self, parent, on_continue, on_back):
        Page.__init__(self, parent=parent)

        self.on_continue = on_continue 
        self.site_code = None
        
        page_sizer = wx.BoxSizer(wx.VERTICAL)
        setup_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.preview_sizer = preview_sizer = wx.BoxSizer(wx.VERTICAL)
        inputs_sizer = wx.BoxSizer(wx.VERTICAL)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.browser_text = browser_text = wx.StaticText(self, label="", style = wx.ALIGN_CENTRE_HORIZONTAL | wx.ST_ELLIPSIZE_MIDDLE | wx.ST_NO_AUTORESIZE)
        self.browser = browser = wx.html2.WebView.New(self)
        self.id_textctrl = id_textctrl = wx.TextCtrl(self, size=(200, -1))
        self.elm_textctrl = elm_textctrl = wx.TextCtrl(self, size=(200, -1))
        self.whole_page = whole_page = wx.CheckBox(self, label="Monitor whole page")
        self.loading_wheel = loading_wheel = wx.adv.AnimationCtrl(self, -1, wx.adv.Animation(os.path.join(os.path.dirname(os.path.realpath(__file__)), "resources", 'loading.gif')), size=(20,20))
        self.continue_button = continue_button = wx.Button(self, label='Next >')
        back_button = wx.Button(self, label='< Back')
        browser_text.SetBackgroundColour((230, 230, 230))
        browser.EnableContextMenu(False)
        loading_wheel.Hide()
        
        page_sizer.Add(wx.StaticText(self, label="Please select the section of the website you would like to monitor."), 0, wx.CENTRE)
        link = wx.adv.HyperlinkCtrl(self, label="More info >>")
        page_sizer.Add(link, 0, wx.CENTRE)
        page_sizer.Add(setup_sizer, 1, wx.EXPAND | wx.TOP, 30)
        setup_sizer.Add(preview_sizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)
        setup_sizer.Add(inputs_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)
        preview_sizer.Add(browser_text, 0, wx.EXPAND)
        preview_sizer.Add(browser, 1, wx.EXPAND)
        inputs_sizer.Add(whole_page, 0, wx.CENTRE)
        inputs_sizer.AddSpacer(50)
        inputs_sizer.Add(wx.StaticText(self, label="Id: "), 0, wx.CENTRE)
        inputs_sizer.Add(id_textctrl, 0, wx.EXPAND)
        inputs_sizer.AddSpacer(50)
        inputs_sizer.Add(wx.StaticText(self, label="Element: "), 0, wx.CENTRE)
        inputs_sizer.Add(elm_textctrl, 0, wx.EXPAND)
        
        inputs_sizer.Add(wx.StaticText(self), 1)
        inputs_sizer.Add(button_sizer, 0, wx.EXPAND, wx.CENTER)
        button_sizer.Add(loading_wheel, 0, wx.CENTRE | wx.RIGHT, 5)
        button_sizer.Add(back_button, 1)
        button_sizer.Add(continue_button, 1)

        browser.Bind(wx.html2.EVT_WEBVIEW_LOADED, self.on_load)
        browser.Bind(wx.html2.EVT_WEBVIEW_TITLE_CHANGED, self.on_title_change)
        link.Bind(wx.adv.EVT_HYPERLINK, self.open_dialog)
        continue_button.Bind(wx.EVT_BUTTON, self.check_entries)
        back_button.Bind(wx.EVT_BUTTON, on_back)
        id_textctrl.Bind(wx.EVT_TEXT, lambda e: id_textctrl.SetBackgroundColour(wx.NullColour))
        elm_textctrl.Bind(wx.EVT_TEXT, lambda e: elm_textctrl.SetBackgroundColour(wx.NullColour))
        whole_page.Bind(wx.EVT_CHECKBOX, self.on_whole_page_click)
        self.SetSizer(page_sizer)

    def on_whole_page_click(self, event):
        if self.whole_page.GetValue():
            self.browser.Disable()
            self.id_textctrl.Disable()
            self.elm_textctrl.Disable()
        else:
            self.browser.Enable()
            self.id_textctrl.Enable()
            self.elm_textctrl.Enable()
        
    def pass_data(self, data):
        self.browser.LoadURL(data)

    def on_load(self, event):
        url = self.browser.GetCurrentURL()
        self.browser_text.SetLabel(url)
        if url == "about:blank":
            self.browser_text.SetLabel("Loading...")
            self.continue_button.Disable()
        else:
            self.continue_button.Enable()
            
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "resources", "jsitemselector"), "r") as handle:
            self.browser.RunScript(handle.read())

    def on_title_change(self, event):
        title = self.browser.GetCurrentTitle()
        try:
            title = title.split(":")
            if title[0] == "WebWatcher365_website_monitor":
                self.id_textctrl.SetValue(title[1])
                self.elm_textctrl.SetValue(title[2])
        except:
            pass

    def open_dialog(self, event):
        message = """WebWatcher365 requires the id and nodeName of the section of the website you want in order to monitor it.
Not all items in a website have a unique id. When you hover over an item, it will be highlighted in yellow.
The nearest section with a valid id will be highlighted in red.
This is what WebWatcher365 will monitor.

Please note that some websites generate sections on the fly. This means that certain sections may be highlighted but cannot be monitored.
If that is the case, The input boxes on the right will turn red when you press 'Next >'. You will have to select a different section.

If you want to monitor the entire webpage instead of a section, click the 'Monitor whole page' checkbutton.

When you are hovering over the appropriate section, press Ctrl+Enter to save it.
You may need to click somewhere in the website for this to work.
Press Ctrl+Enter a second time to select a different section.
When the section is saved, its id and nodeName will be shown in the input boxes.
Only edit these boxes if you want to manually edit the values.
Once you have picked your section, press 'Next >' to go to the next step."""
        wx.MessageDialog(None, message, caption="WebWatcher365 Help Dialog",
              style=wx.OK | wx.CENTRE).ShowModal()

    def check_entries(self, event):
        can_continue = True
        if not self.whole_page.GetValue():
            if self.id_textctrl.GetValue() == "":
                can_continue = False
                self.id_textctrl.SetBackgroundColour((255, 11, 0))
            if self.elm_textctrl.GetValue() == "":
                can_continue = False
                self.elm_textctrl.SetBackgroundColour((255, 11, 0))
        if can_continue:
            self.loading_wheel.Show()
            self.loading_wheel.Play()
            self.Layout()
            self.Disable()
            url = self.browser_text.GetLabel()
            elm = self.elm_textctrl.GetValue().lower()
            id_params = {"id": self.id_textctrl.GetValue()}
            if self.whole_page.GetValue():
                worker = Bs4Thread(self, url, None, None)
            else:
                worker = Bs4Thread(self, url, elm, id_params)
            worker.start()
            self.Bind(worker.EVT_COUNT, self.on_thread_return)

    def on_thread_return(self, evt):
        val = evt.GetValue()
        self.loading_wheel.Hide()
        self.loading_wheel.Stop()
        self.Enable()
        self.site_code = val
        if val is None:
            self.id_textctrl.SetBackgroundColour((255, 11, 0))
            self.elm_textctrl.SetBackgroundColour((255, 11, 0))
        else:
            self.on_continue()

    def return_data(self):
        sectid = self.id_textctrl.GetValue()
        sectnode = self.elm_textctrl.GetValue().lower()
        if self.whole_page.GetValue():
            sectid = None
            sectnode = None
        settings_dict = {
            "website":self.browser_text.GetLabel(),   
            "section_id": sectid,
            "section_nodeName": sectnode
            }
        return settings_dict
        
            
class PageThree(Page):
    def __init__(self, parent, on_continue, on_back):
        Page.__init__(self, parent=parent)
        
        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        horizontal_sizer = wx.BoxSizer(wx.HORIZONTAL)
        add_or_remove_sizer = wx.BoxSizer(wx.HORIZONTAL)
        vertical_content_sizer = wx.BoxSizer(wx.VERTICAL)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.introduction_text = introduction_text = wx.StaticText(self, label="Who do you want to send the e-mails to?", style = wx.ALIGN_CENTRE_HORIZONTAL)
        self.list_box = list_box = wx.ListBox(self, size=(-1, 150))
        self.email_input = email_input = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        height = (email_input.GetSize()[1])
        add_icon = wx.Bitmap(os.path.join(os.path.dirname(os.path.realpath(__file__)), "resources", "add.png"), wx.BITMAP_TYPE_ANY)
        remove_icon = wx.Bitmap(os.path.join(os.path.dirname(os.path.realpath(__file__)), "resources", "remove.png"), wx.BITMAP_TYPE_ANY)
        add_button = wx.BitmapButton(self, -1, add_icon, size=(height,height))
        self.remove_button = remove_button = wx.BitmapButton(self, -1, remove_icon, size=(height,height))
        self.continue_button = continue_button = wx.Button(self, label='Next >')
        back_button = wx.Button(self, label='< Back')
        
        continue_button.Disable()
        remove_button.Disable()

        vertical_sizer.Add(horizontal_sizer, 1, wx.EXPAND)
        horizontal_sizer.Add(vertical_content_sizer, 1, wx.CENTER | wx.EXPAND | wx.ALL, 50)
        vertical_content_sizer.Add(introduction_text, 0, wx.CENTRE | wx.BOTTOM, 15)
        vertical_content_sizer.Add(add_or_remove_sizer, 0, wx.CENTRE | wx.EXPAND | wx.BOTTOM, 5)
        vertical_content_sizer.Add(list_box, 1, wx.EXPAND)
        add_or_remove_sizer.Add(email_input, 1)
        add_or_remove_sizer.Add(add_button, 0, wx.CENTRE)
        add_or_remove_sizer.Add(remove_button, 0, wx.CENTRE)
        vertical_sizer.Add(button_sizer, 0, wx.RIGHT | wx.ALIGN_RIGHT | wx.BOTTOM, 5)
        button_sizer.Add(back_button)
        button_sizer.Add(continue_button)

        continue_button.Bind(wx.EVT_BUTTON, on_continue)
        back_button.Bind(wx.EVT_BUTTON, on_back)
        list_box.Bind(wx.EVT_LISTBOX, self.on_selection_change)
        add_button.Bind(wx.EVT_BUTTON, self.add_email)
        remove_button.Bind(wx.EVT_BUTTON, self.remove_email)
        email_input.Bind(wx.EVT_TEXT_ENTER, self.add_email)
        email_input.Bind(wx.EVT_TEXT, lambda e: email_input.SetBackgroundColour(wx.NullColour))
        
        self.SetSizer(vertical_sizer)

    def on_selection_change(self, event):
        self.remove_button.Enable()

    def add_email(self, event):
        val = self.email_input.GetValue()
        if re.match("[^@]+@[^@]+\.[^@]+", val):
            if val not in self.list_box.GetStrings():
                self.email_input.SetValue("")
                self.list_box.InsertItems([val], 0)
            else:
                self.email_input.SetBackgroundColour((255, 11, 0)) 
        else:
            self.email_input.SetBackgroundColour((255, 11, 0))

        if len(self.list_box.GetStrings()) > 0:
            self.continue_button.Enable()
        else:
            self.continue_button.Disable()

    def remove_email(self, event):
        item = self.list_box.GetSelection()
        delete = wx.MessageDialog(None, "Are you sure you want to remove the email address '"+self.list_box.GetString(item)+"'?", "Confirm delete", wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION).ShowModal()
        if delete == wx.ID_YES:
            self.list_box.Delete(item)

        if len(self.list_box.GetStrings()) > 0:
            self.continue_button.Enable()
        else:
            self.continue_button.Disable()

    def return_data(self):
        settings_dict = {
            "email_addresses":self.list_box.GetStrings()   
            }
        return settings_dict

class PageFour(Page):
    def __init__(self, parent, on_continue, on_back):
        Page.__init__(self, parent=parent)
        
        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        horizontal_sizer = wx.BoxSizer(wx.HORIZONTAL)
        input_sizer = wx.FlexGridSizer(8, 2, 5, 5)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.introduction_text = introduction_text = wx.StaticText(self, label="What do you want the message to say?", style = wx.ALIGN_CENTRE_HORIZONTAL)
        self.title_input = title_input = wx.TextCtrl(self)
        self.caption_input = caption_input = wx.TextCtrl(self)
        self.body_1_input = body_1_input = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        self.body_2_input = body_2_input = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        self.additional_input = additional_input = wx.TextCtrl(self)
        self.html = html = wx.html2.WebView.New(self) 
        self.continue_button = continue_button = wx.Button(self, label='Finish')
        back_button = wx.Button(self, label='< Back')

        title_input.SetValue("This is the subject of the e-mail")
        caption_input.SetValue("This is the message's heading.")
        body_1_input.SetValue("This is some text. \n <i>HTML is also supported here.</i> \n \nThis is the updated website snippet; changes are highlighted in yellow:")
        body_2_input.SetValue("This is some other info")
        additional_input.SetValue("Courtesy of John Doe")

        vertical_sizer.Add(introduction_text, 0, wx.CENTER)
        vertical_sizer.Add(horizontal_sizer, 1, wx.EXPAND)
        horizontal_sizer.Add(input_sizer, 1, wx.CENTER | wx.EXPAND | wx.ALL, 30)
        horizontal_sizer.Add(html, 1, wx.CENTER | wx.EXPAND | wx.ALL, 30)
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
        vertical_sizer.Add(button_sizer, 0, wx.RIGHT | wx.ALIGN_RIGHT | wx.BOTTOM, 5)
        button_sizer.Add(back_button)
        button_sizer.Add(continue_button)

        title_input.Bind(wx.EVT_TEXT, self.text_change)
        caption_input.Bind(wx.EVT_TEXT, self.text_change)
        body_1_input.Bind(wx.EVT_TEXT, self.text_change)
        body_2_input.Bind(wx.EVT_TEXT, self.text_change)
        additional_input.Bind(wx.EVT_TEXT, self.text_change)
        continue_button.Bind(wx.EVT_BUTTON, on_continue)
        back_button.Bind(wx.EVT_BUTTON, on_back)

        self.text_change()
        
        self.SetSizer(vertical_sizer)

    def text_change(self, event=None):
        html = """\
                    <html>
                        <head>
                        </head>
                        <body>
                            <b><p>"""+self.caption_input.GetValue()+"""</p></b>
                            <p>"""+self.body_1_input.GetValue().replace("\n", "</br>")+"""</p>
                            <div style="background-color: coral;"><p>Updated website snippet preview</p></div>
                            <p>"""+self.body_2_input.GetValue().replace("\n", "</br>")+"""</p>
                            <h6>"""+self.additional_input.GetValue()+"""</h6>
                        </body>
                    </html>
                    """
        self.html.SetPage(html, "")

    def return_data(self):
        settings_dict = {
            "message":[self.title_input.GetValue(),
                       self.caption_input.GetValue(),
                       self.body_1_input.GetValue().replace("\n", "</br>"),
                       self.body_2_input.GetValue().replace("\n", "</br>"),
                       self.additional_input.GetValue()]
            }
        return settings_dict


class SetupFrame(wx.Frame):
    def __init__(self, parent, pages=[PageOne,PageTwo,PageThree,PageFour], **kwargs):
        wx.Frame.__init__(self, parent, **kwargs)

        self.SetMinSize((400, 400))

        vertical_sizer = wx.BoxSizer(wx.VERTICAL)
        self.panels = panels = []
        self.settings = {}

        count = 0
        for page in pages:
            page = page(self, self.go_to_next_page, self.go_to_prev_page)
            panels.append(page)
            vertical_sizer.Add(page, 1, wx.EXPAND)
            if count == 0:
                self.current_page = page
            else:
                page.Hide()
            count += 1
            #page.return_data()
        self.SetSizer(vertical_sizer)

        self.Show()

    def go_to_next_page(self, event=None, pass_data=None):
        self.current_page.Hide()
        try:
            next_page_num = self.panels.index(self.current_page)+1
            self.current_page = self.panels[next_page_num]
            if pass_data:
                self.current_page.pass_data(pass_data)
            self.show_current_page()
        except:
            for page in self.panels:
                self.settings.update(page.return_data())
            self.Close()
        
    def go_to_prev_page(self, event=None):
        self.current_page.Hide()
        
        try:
            next_page_num = self.panels.index(self.current_page)-1
        except:
            next_page_num = -1
        self.current_page = self.panels[next_page_num]

        self.show_current_page()
            
    def show_current_page(self):
        self.current_page.Show()
        self.Layout()

    def return_data(self):
        return self.settings

    def return_site_code(self):
        for page in self.panels:
            try:
                return page.site_code
            except:
                pass
        return None


def main():
    app = wx.App()
    websitepicker = SetupFrame(None, pages=[PageOne,PageTwo,PageThree,PageFour], title='WebWatcher365')
    def on_close(event):
        data = websitepicker.return_data()
        if len(data) == 0:
            close = wx.MessageDialog(None, "Are you sure you want to close this window? Any changes you have made will be lost.", "Confirm close", wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION).ShowModal()
            if close == wx.ID_YES:
                websitepicker.Destroy()
            else:
                return
        else:
            websitepicker.Destroy()
        
    websitepicker.Bind(wx.EVT_CLOSE, on_close)
    app.MainLoop()


if __name__ == '__main__':
    main()

