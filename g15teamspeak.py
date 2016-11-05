#!/usr/bin/python3

import os
import sys
import ts
import g15
import queue
from functools import partial
from enum import Enum
from PIL import Image, ImageFont, ImageDraw

ROOT_DIR = os.path.dirname(os.path.realpath(sys.argv[0]))

#accessed only in the main thread
state = {
  'hookId': None,
  'connected': False, # to a server
  'clid': None, #that's me
  'cid': None, #cid
  'channels': {}, #cid -> name
  'nicknames': {},
  'talking': []
}

#Events for the main loop
EVENT = Enum("Event", "TS_Hook TS_Unhook TS_Connect TS_DC TS_WhereWho TS_Channel TS_Nickname TS_Talk TS_ClientMoved")
eventQueue = queue.Queue()

def getNickname(clid):
  if clid in state['nicknames']:
    return state['nicknames'][clid]
  else:
    ts3.sendCmd(state['hookId'], 'clientgetuidfromclid', {'clid':clid})
    return '?'+clid+'?'

def getChannel(cid=None):
  if cid == None:
    if state['cid'] != None:
      cid = state['cid']
    else:
      return "?"
  if cid in state['channels']:
    return state['channels'][cid]
  else:
    onthischannelconnectinfo = partial(onchannelconnectinfo, cid)
    ts3.sendCmd(state['hookId'], 'channelconnectinfo', {'cid':cid}, unpacker=ts.unpackObject, callback=onthischannelconnectinfo, errback=checkForDC)
    return '?'+cid+'?'

def log(obj):
  print(obj)

def whoami():
  ts3.sendCmd(state['hookId'], 'whoami', unpacker=ts.unpackObject, callback=onwhoami, errback=checkForDC)

#TS3 callbacks. Beware, called in another thread!
#lifecysle
def onHook(id):
  eventQueue.put((EVENT.TS_Hook, id))
def onUnhook():
  eventQueue.put((EVENT.TS_Unhook,))
#notify
def notifytalkstatuschange(obj):
  eventQueue.put((EVENT.TS_Talk, obj['clid'], obj['status']=='1'))
#def notifyclientleftview(obj):
#  print("Left: ", getNickname(obj['clid']))
#def notifycliententerview(obj):
#  print("Enter: ", getNickname(obj['clid']))
def notifyclientuidfromclid(obj):
  eventQueue.put((EVENT.TS_Nickname, obj['clid'], obj['nickname']))
def notifyclientmoved(obj):
  eventQueue.put((EVENT.TS_ClientMoved, obj['clid'], obj['ctid']))
def notifyconnectstatuschange(obj):
  status = obj['status']
  if status == 'connection_established':
    eventQueue.put((EVENT.TS_Connect,))
  elif status == 'disconnected':
    eventQueue.put((EVENT.TS_DC,))

#cmd callbacks
def checkForDC(error):
  if error['id'] == '1794':
    eventQueue.put((EVENT.TS_DC,))
  else:
    print("Unknown error:", error)
def onchannelconnectinfo(cid, obj):
  eventQueue.put((EVENT.TS_Channel, cid, obj['path']))
def onwhoami(obj):
  eventQueue.put((EVENT.TS_WhereWho, obj['cid'], obj['clid']))

#g15
g15Daemon = g15.Daemon()

font = ImageFont.truetype("4x6.pcf.gz", 6)
bombImage = Image.open(ROOT_DIR+"/bomb.xbm")
disconnectImage = Image.open(ROOT_DIR+"/disconnected.xbm")
buttonImage = Image.open(ROOT_DIR+"/button.xbm")

def drawButton(screen, draw, index, text):
  screen.paste(buttonImage, (40*index, 35))
  textSize = draw.textsize(text, font=font)
  draw.text((40*index+20-textSize[0]/2, 36), text, font=font, fill=0)

def refreshDisplay():
  screen = Image.new("1", (160, 43), 0)
  draw = ImageDraw.Draw(screen)
  waitForOk = False
  
  if state['hookId'] == None:
    screen.paste(bombImage, (6, 5))
    draw.text((45, 3), "Could not connect to your\nTeamSpeak client.\n\nRetrying...", font=font, fill=1)
  elif not state['connected']:
    screen.paste(disconnectImage, (4, 2))
    draw.text((50, 15), "Disconnected", font=font, fill=1)
  elif False:  #if len(pokes) != 0:
    #pokes
    draw.text((0, 0), "From {0}:\n{1}".format(pokes[0][0], pokes[0][1]), font=font, fill=1)
    del pokes[0]
    drawButton(screen, draw, 0, "Ok")
    waitForOk = True
  #elif state['cid'] == None:
    #draw connected icon + message
  else:
    #channel
    title = "-= "+getChannel()+" =-"
    titleSize = draw.textsize(title, font=font)
    draw.text((80-titleSize[0]/2, 0), title, font=font, fill=1)
    #drawButton(screen, draw, 0, "Test 1")
    #drawButton(screen, draw, 1, "Test 2")
    #drawButton(screen, draw, 2, "Test 3")
    #drawButton(screen, draw, 3, "Test 4")
    #see who's talking
    i=0
    for clid in state['talking']:
      i += 6
      draw.text((0, i), getNickname(clid), font=font, fill=1)

  g15Daemon.draw(screen)
  #FIXME buggy
  if waitForOk:
    while waitForOk:
      keys = g15.getKeystate() #this is blocking, key pressed are buffered
      waitForOk = not (keys & g15.KEY_L2 == g15.KEY_L2)
    refreshDisplay()


#
# The fun begins
#
ts3 = ts.TS3(onHook, onUnhook, {
  'notifytalkstatuschange': notifytalkstatuschange,
#  'notifyclientleftview': notifyclientleftview,
#  'notifycliententerview': notifycliententerview,
  'notifyclientuidfromclid': notifyclientuidfromclid,
  'notifyclientmoved': notifyclientmoved,
  'notifyconnectstatuschange': notifyconnectstatuschange,
})
ts3.hook()

#main loop
while True:
  refreshDisplay()
  event = eventQueue.get()
  eventType = event[0]
  if eventType == EVENT.TS_Hook:
    print("Hook id: ", event[1])
    state['hookId'] = event[1]
    state['connected'] = True #we'll know soon enough otherwise
    state['clid'] = None
    state['cid'] = None
    state['channels'] = {}
    state['nicknames'] = {}
    state['talking'] = []
    whoami()
  elif eventType == EVENT.TS_Unhook:
    state['hookId'] = None
  elif eventType == EVENT.TS_Connect:
    state['connected'] = True
    state['clid'] = None
    state['cid'] = None
    state['channels'] = {}
    state['nicknames'] = {}
    state['talking'] = []
    whoami()
  elif eventType == EVENT.TS_DC:
    state['connected'] = False
  elif eventType == EVENT.TS_WhereWho:
    state['cid'] = event[1]
    if(len(event) == 3):
      state['clid'] = event[2]
  elif eventType == EVENT.TS_Channel:
    state['channels'][event[1]] = event[2]
  elif eventType == EVENT.TS_Nickname:
    state['nicknames'][event[1]] = event[2]
  elif eventType == EVENT.TS_Talk:
    if event[2]:
      state['talking'].append(event[1])
    elif state['talking'].count(event[1]) != 0:
      state['talking'].remove(event[1])
  elif eventType == EVENT.TS_ClientMoved:
    if event[1] == state['clid']: #that's us?
      state['cid'] = event[2]
      

