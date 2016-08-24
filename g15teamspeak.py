#!/usr/bin/python3

from PIL import Image, ImageFont, ImageDraw
import telnetlib
import time

import g15daemon

TS3_HOST = "localhost"
TS3_PORT = 25639
CHARS_PER_LINE = 40

PIPE = '/tmp/g15-teamspeak-pipe'

nicknames = {}
talking = []

g15 = g15daemon.G15daemon()

def getTelnet():
  telnet = telnetlib.Telnet(TS3_HOST, TS3_PORT)
  telnet.write(b'clientnotifyregister schandlerid=1 event=notifyclientuidfromclid\n')
  telnet.write(b'clientnotifyregister schandlerid=1 event=notifytalkstatuschange\n')
  telnet.write(b'clientnotifyregister schandlerid=1 event=notifyclientpoke\n')
  return telnet

tn = None

def getNickname(clid):
  if clid in nicknames:
    return nicknames[clid]
  else:
    tn.write(b'clientgetuidfromclid clid='+str(clid).encode()+b'\n')
    return '???'

def decodeTsString(bstring):
  return bstring.decode().replace('\\s', ' ').replace('\\/', '/')

notifyTalkStatusChangeRegexp = b"notifytalkstatuschange schandlerid=1 status=(.) isreceivedwhisper=. clid=(.*)\n"
def onNotifyTalkStatusChange(match):
  status = match.group(1)==b'1'
  clid = int(match.group(2))
  if status:
    talking.append(clid)
  elif talking.count(clid) != 0:
    talking.remove(clid)
  #print(('+' if status else '-')+" "+str(clid)+ " " + getNickname(clid))

notifyClientuidFromClidRegexp = b"notifyclientuidfromclid schandlerid=1 clid=(.+) cluid=.* nickname=(.+)\n"
def onNotifyClientuidFromClid(match):
  clid = int(match.group(1))
  nickname = decodeTsString(match.group(2))
  nicknames[clid] = nickname
  #print(str(clid)+" is "+nickname)

notifyClientPokeRegexp = b"notifyclientpoke schandlerid=1 invokerid=.+ invokername=(.+) invokeruid=.+ msg=(.+)\n"
def onNotifyClientPoke(match):
  invoker = decodeTsString(match.group(1))
  msg = decodeTsString(match.group(2))
  print(invoker+": "+msg)

font = ImageFont.truetype("4x6.pcf.gz", 6)
bombImage = Image.open("bomb.xbm")
buttonImage = Image.open("button.xbm")

def drawButton(screen, draw, index, text):
  screen.paste(buttonImage, (40*index, 35))
  textSize = draw.textsize(text, font=font)
  draw.text((40*index+20-textSize[0]/2, 36), text, font=font, fill=0)

def refreshDisplay():
  screen = Image.new("1", (160, 43), 0)
  draw = ImageDraw.Draw(screen)
  if tn != None:
    draw.text((0, 0), "            -= TEAM SPEAK =-", font=font, fill=1)
    #drawButton(screen, draw, 0, "Test 1")
    #drawButton(screen, draw, 1, "Test 2")
    #drawButton(screen, draw, 2, "Test 3")
    #drawButton(screen, draw, 3, "Test 4")
    i=0
    for clid in talking:
      i += 6
      draw.text((0, i), getNickname(clid), font=font, fill=1)
  else:
    #TODO better explanation of the real issue
    screen.paste(bombImage, (6, 5))
    draw.text((45, 3), "Could not connect to your\nTeamSpeak client.\n\nRetrying...", font=font, fill=1)
  g15.draw(screen)
  
while(True):
  try:
    refreshDisplay()
    if tn == None:
      tn = getTelnet()
    else:
      msg = tn.expect([notifyTalkStatusChangeRegexp, notifyClientuidFromClidRegexp, notifyClientPokeRegexp])
      index = msg[0]
      match = msg[1]
      bytes = msg[2] #who cares
      if index == 0: #notifytalkstatuschange
        onNotifyTalkStatusChange(match)
      elif index == 1: #notifyclientuidfromclid
        onNotifyClientuidFromClid(match)
      elif index == 2: #notifyClientPokeRegexp
        onNotifyClientPoke(match)
  except EOFError:
    print(":-( EOF")
    tn = None
  except (ConnectionRefusedError, ConnectionResetError):
    print(":-( No TS?")
    tn = None
    refreshDisplay()
    time.sleep(5) #wait a little bit

