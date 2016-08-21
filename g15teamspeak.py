#!/usr/bin/python3

import os
import telnetlib
import time

TS3_HOST = "localhost"
TS3_PORT = 25639
CHARS_PER_LINE = 40

PIPE = '/tmp/g15-teamspeak-pipe'

nicknames = {}
talking = []

#FIXME foobar if a file with the same name exists or if g15composer fails to launch
g15id = os.spawnlp(os.P_NOWAIT, 'g15composer', 'g15composer', PIPE)
print("G15 screen pid = "+str(g15id))
#wait for g15compose to create the pipe (we should do it ourselves)
time.sleep(2)

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
  status = True if match.group(1)==b'1' else False
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

def refreshDisplay():
  if tn != None:
    status = 'TS "            -= TEAM SPEAK =-" '
    for clid in talking:
      status += '"'+getNickname(clid)+'" '
  else:
    status = 'TS "            !! NO TELNET !!" '
  print(status);
  g15 = open(PIPE, mode='w', buffering=1);
  g15.write(status+"\n")
  g15.close()

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
    print("EOF :-(")
    tn = None
