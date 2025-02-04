import difflib
import smtplib
import ssl
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import re
import wx
import wx.adv
import wx.html2
from bs4 import BeautifulSoup

import requests
from premailer import transform


class ReturnEvent(wx.PyCommandEvent):
    def __init__(self, etype, eid, value=None, error=None):
        wx.PyCommandEvent.__init__(self, etype, eid)
        self._value = value
        self._error = error
        
    def GetValue(self):
        return self._value

    def GetError(self):
        return self._error
    
class Bs4Thread(threading.Thread):
    def __init__(self, parent, url, elm_params, id_params, content=None):
        threading.Thread.__init__(self, daemon=True)
        self._parent = parent
        self._url = url
        self._content = content
        self._elm_params = elm_params
        self._id_params = id_params

        self.NEW_EVENT = NEW_EVENT = wx.NewEventType()
        self.EVT_COUNT = wx.PyEventBinder(NEW_EVENT, 1)

    def run(self):
        try:
            if self._content:
                source = self._content
            else:
                source = Request(self._url, headers={"User-Agent": "Mozilla/5.0"})
                source = urlopen(source).read()
                source = source.decode('utf-8')
        except Exception as error:
            evt = ReturnEvent(self.NEW_EVENT, -1, None, error)
            wx.PostEvent(self._parent, evt)
        else:            
            if self._elm_params is None:
                if self._id_params is None:
                    try:
                        evt = ReturnEvent(self.NEW_EVENT, -1, source)
                        wx.PostEvent(self._parent, evt)
                    except RuntimeError:
                        pass
                    return

            soup = BeautifulSoup(source, "lxml")
            for img in soup.find_all("img"): 
                img.decompose()
            source = soup.find(self._elm_params, self._id_params)
            try:
                evt = ReturnEvent(self.NEW_EVENT, -1, source)
                wx.PostEvent(self._parent, evt)
            except RuntimeError:
                pass

class InlineCSS(threading.Thread):
    def __init__(self, parent, data_old, data_new, whole_page, style):
        threading.Thread.__init__(self, daemon=True)
        self._parent = parent
        self.data_old = data_old
        self.data_new = data_new
        self.whole_page = whole_page
        self.style = style

        self.NEW_EVENT = NEW_EVENT = wx.NewEventType()
        self.EVT_DONE = wx.PyEventBinder(NEW_EVENT, 1)

    def run(self):
        data = self.show_diff(difflib.SequenceMatcher(None, self.data_old, self.data_new))
        if self.whole_page:
            html_new_msg = str(data)
        else:
            html_new_msg = """<html><head>"""+self.style+"""</head><body><table width=100%>"""+(str(data))+"""</table></body></html>"""
        try:
            html_new_msg = transform(html_new_msg)
        except Exception as error:
            evt = ReturnEvent(self.NEW_EVENT, -1, html_new_msg, error)
            wx.PostEvent(self._parent, evt)
            
        """try:
            # this section replaces heading and body with table element.
            #Works well for Area notifications.
            #TODO - check if it has issues with other sites
            html_new_msg = html_new_msg.replace("\n", "")
            html_new_msg = re.sub('<html.*?<body', '<table style="width: 100%;"', html_new_msg)
            html_new_msg = re.sub('</body.*?</html>', '</table>', html_new_msg)
        except Exception as error:
            evt = ReturnEvent(self.NEW_EVENT, -1, html_new_msg, error)
            wx.PostEvent(self._parent, evt)"""
        
        try:
            evt = ReturnEvent(self.NEW_EVENT, -1, html_new_msg)
            wx.PostEvent(self._parent, evt)
        except RuntimeError:
            pass
            
    def show_diff(self, seqm):
        output = []
        append_mark = False
        for opcode, a0, a1, b0, b1 in seqm.get_opcodes():
            if opcode == 'equal':
                appd = list(seqm.b[b0:b1])
                if append_mark:
                    for index, item in enumerate(appd):
                        if item == ">":
                            appd[index+1:index+1] = ["<","/","m","a","r","k",">"] 
                            append_mark = False
                            break
                output.extend(appd)
            elif (opcode == 'replace') or (opcode == 'delete') or (opcode == 'insert'):
                appd = list(seqm.b[b0:b1])
                if append_mark:
                    for index, item in enumerate(appd):
                        if item == ">":
                            appd[index+1:index+1] = ["<","/","m","a","r","k",">"] 
                            append_mark = False
                            break
                output.extend(appd)
                out = (''.join(output))
                new_out = (list(reversed(out)))
                for index, item in enumerate(new_out):
                    if item == "<":
                        #if the change is inside a tag, don't mark it
                        break
                    if item == ">":
                        new_out[index:index] = [">","k","r","a","m","<"]
                        append_mark = True
                        break
                new_out = (list(reversed(new_out)))
                output = new_out
            else:
                pass
        if append_mark:
            output.extend(["<", "/", "m", "a", "r", "k", ">"])
        return ''.join(output)

class GetStyles(threading.Thread):
    def __init__(self, parent, url, elm_params, id_params):
        threading.Thread.__init__(self, daemon=True)
        self._parent = parent
        self._url = url
        self._elm_params = elm_params
        self._id_params = id_params
        self.csssource = ""

        self.NEW_EVENT = NEW_EVENT = wx.NewEventType()
        self.EVT_COUNT = wx.PyEventBinder(NEW_EVENT, 1)
        
    def _load_external(self, url):
        response = requests.get(url)
        response.raise_for_status()    
        return response.text

    def run(self):
        try:
            sourcem = Request(self._url, headers={"User-Agent": "Mozilla/5.0"})
            sourcem = urlopen(sourcem).read()
            sourcem = sourcem.decode('utf-8')
        except Exception as error:
            evt = ReturnEvent(self.NEW_EVENT, -1, [None, None], error)
            wx.PostEvent(self._parent, evt)
        else:
            soup = BeautifulSoup(sourcem, "lxml")          
            for styletag in soup.find_all('link', type="text/css"):
                if styletag.attrs.get("href"):
                    url = urljoin(self._url, styletag.attrs.get("href"))
                    data = self._load_external(url)
                    imports = re.findall('@import url(.*?)', data)
                    for item in imports:
                        item = item.replace("@import url(", "")[0:-1]
                        self.csssource += "<style>"+self._load_external(urljoin(url, item))+"</style>"
                    self.csssource += "<style>"+data+"</style>"
            for styletag in soup.find_all('style'):
                self.csssource += str(styletag)
            
            worker = Bs4Thread(self._parent, self._url, self._elm_params, self._id_params, content=sourcem)
            worker.start()
            self._parent.Bind(worker.EVT_COUNT, self.on_thread_return)

    def on_thread_return(self, event):
        val = event.GetValue()
        error = event.GetError()
        if error is not None:
            evt = ReturnEvent(self.NEW_EVENT, -1, [None, None], error)
            wx.PostEvent(self._parent, evt)
        else:
            try:
                evt = ReturnEvent(self.NEW_EVENT, -1, [val, self.csssource])
                wx.PostEvent(self._parent, evt)
            except RuntimeError:
                pass


class SendEmailThread(threading.Thread):
    def __init__(self, parent, html, recipients, subject, uname, passwd):
        threading.Thread.__init__(self, daemon=True)
        self.html = html
        self.recipients = recipients
        self.subject = subject
        self.passwd = passwd
        self.uname = uname
        self._parent = parent
        
        self.NEW_EVENT = NEW_EVENT = wx.NewEventType()
        self.EVT_SENT = wx.PyEventBinder(NEW_EVENT, 1)

    def run(self):
        try:
            for you in self.recipients:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = self.subject
                msg['From'] = self.uname
                msg['To'] = you

                text = ""
                html = str(self.html)
                part1 = MIMEText(text, 'plain')
                part2 = MIMEText(html, 'html')

                msg.attach(part1)
                msg.attach(part2)

                with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as server:
                    server.login(self.uname, self.passwd)
                    server.sendmail(self.uname, you, msg.as_string())

            evt = ReturnEvent(self.NEW_EVENT, -1)
            wx.PostEvent(self._parent, evt)
            
        except Exception as error:
            evt = ReturnEvent(self.NEW_EVENT, -1, error=error)
            wx.PostEvent(self._parent, evt)



