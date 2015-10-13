import sublime
import sublime_plugin
from urllib import request,parse
import json
import threading
import sys,os
import socket 

__version__ = '2.0.1'
REDIS_SERVER = '192.168.2.4'
SETTINGS_FILE = 'WorkBot.sublime-settings'
SETTINGS = {}
PLUGIN_DIR = os.path.dirname(os.path.realpath(__file__))
# add redis package to path
sys.path.insert(0, os.path.join(PLUGIN_DIR, 'packages'))
import redis


# Log Levels
DEBUG = 'DEBUG'
INFO = 'INFO'
WARNING = 'WARNING'
ERROR = 'ERROR'
def log(lvl, message, *args, **kwargs):
    try:
        if lvl == DEBUG and not SETTINGS.get('debug'):
            return
        msg = message
        if len(args) > 0:
            msg = message.format(*args)
        elif len(kwargs) > 0:
            msg = message.format(**kwargs)
        print('[WorkBot] [{lvl}] {msg}'.format(lvl=lvl, msg=msg))
    except RuntimeError:
        sublime.set_timeout(lambda: log(lvl, message, *args, **kwargs), 0)

class ApiThread(threading.Thread):
    def __init__(self, cmd,text, edit):
        threading.Thread.__init__(self)
        self.cmd = cmd
        self.text = text
        self.edit = edit

    def run(self):
        for chunk in self.text.splitlines():
            apiRes = apiGet('bot', cmd=chunk.strip())
            if apiRes:
                if 'out' in apiRes:
                    print("---------------------------------")
                    for r in apiRes['out']:
                        print(r)

        #sublime.set_timeout(self.callback, 1) ovc

class Listener(threading.Thread):
    def __init__(self, r, channels):
        threading.Thread.__init__(self)
        self.redis = r
        self.pubsub = self.redis.pubsub()
        self.pubsub.subscribe(channels)
    
    def work(self, item):
        log(INFO,item['data'])
        # print(item['channel'], ":", item['data'])
    
    def run(self):
        for item in self.pubsub.listen():
            if item['data'] == "KILL":
                self.pubsub.unsubscribe()
                log(WARNING,'Killed!')
                #print(self, "unsubscribed and finished")
                break
            else:
                self.work(item)

def apiGet(api, **kwargs):
    if kwargs:
        data = parse.urlencode(kwargs)
        binary_data = data.encode("utf-8")
        #req = request.Request("http://192.168.2.2/api/%s/" % (api),binary_data)
        result = request.urlopen("http://192.168.2.2/api/%s/" % (api),binary_data)
    else:
        #req = request.Request("http://192.168.2.2/api/%s/" % (api),None)
        result = request.urlopen("http://192.168.2.2/api/%s/")
    try:
        return json.loads(result.readall().decode('utf-8'))
    except Exception as e:
        print(e)
        return None


class MecomWorkSendToBotCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        sublime.active_window().run_command("show_panel", {"panel": "console", "toggle": True})

        for selection in self.view.sel():
            # if the user didn't select anything, search the currently highlighted word
            if selection.empty():
                text = self.view.word(selection)

            text = self.view.substr(selection)
            print("invio comandi al bot...")
            apiT = ApiThread(self, text, edit)
            apiT.start()

class MecomWorkKillRedis(sublime_plugin.TextCommand):
    def run(self, edit):
        log(INFO, "Kill Connection")
        r = redis.Redis(REDIS_SERVER)
        r.publish('sublime_%s' % socket.gethostname(), 'KILL')

class MecomWorkTestRedis(sublime_plugin.TextCommand):
    def run(self, edit):
        log(INFO, "Test Connection")
        r = redis.Redis(REDIS_SERVER)
        r.publish('sublime_%s' % socket.gethostname(), 'Test')



def plugin_loaded():
    global SETTINGS
    log(INFO, 'Initializing MecomWork plugin v%s' % __version__)
    
    r = redis.Redis(REDIS_SERVER)
    client = Listener(r, ['sublime_%s' % socket.gethostname()])
    client.start()

    SETTINGS = sublime.load_settings(SETTINGS_FILE)

    #r.publish('sublime_%s' % socket.gethostname(), 'this will reach the listener')

    


