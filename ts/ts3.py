import queue
import socket
import threading
import time
import uuid
from enum import Enum
from .unpacker import *

TS3_HOST = "localhost"
TS3_PORT = 25639

STATUS = Enum("TS Status", "Handshake1 Handshake2 Handshake3 Hooked")

TS3_GREETING = "TS3 Client"


EVENT_UNPACKER = {
  'notifyclientleftview': unpackObject,
  'notifycliententerview': unpackObject,
  'notifytalkstatuschange': unpackObject,
  'notifyclientupdated': unpackObject,
  'notifyclientuidfromclid': unpackObject,
  'notifyclientmoved': unpackObject,
  'notifyclientpoke': unpackObject,
  'notifyconnectstatuschange': unpackObject #status=connecting/connected/connection_establishing/connection_established/disconnected
}


class TS3:

  #callbacks will be called in the read thread
  def __init__(self, onHook, onUnhook, callbacks):
    print("New TS3 connection")
    self._onHook = onHook
    self._onUnhook = onUnhook
    self._callbacks = callbacks
    self._hookId = 0
    self._cmdQueue = queue.Queue()
    self._acceptingCmd = threading.Event()
    self._currentCmdNeedsResponse = False

  def hook(self):
    #TODO loop when connection is lost
    threading.Thread(name="TS3_READ", target=self._run, daemon=True).start()
    threading.Thread(name="TS3_CMD", target=self._runCmd, daemon=True).start()

    
  def sendCmd(self, connId, cmd, args={}, unpacker=None, callback=None, errback=None):
    cmdstr = cmd
    for key in args:
      cmdstr += ' '+key+'='+args[key]
    print("Cmd: ", cmdstr)
    self._cmdQueue.put((connId, cmdstr.encode(), unpacker, callback, errback))

  def _runCmd(self):
    while True:
      hookId, cmd, unpacker, callback, errback = self._cmdQueue.get()
      self._acceptingCmd.wait()
      if hookId == self._hookId:
        #print("=>", cmd)
        self._currentCmdUnpacker = unpacker
        self._currentCmdCallback = callback
        self._currentCmdErrback = errback
        self._acceptingCmd.clear()
        self._socket.sendall(cmd)
        self._socket.sendall(b'\n')
      else:
        print("Wrong hookId, got ", hookId, " but expected ", self._hookId)
      

  def _run(self):
    print("running")
    while True:
      try:
        print("Opening TS socket")
        self._acceptingCmd.clear() #useful?
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((TS3_HOST, TS3_PORT))
        self._status = STATUS.Handshake1
        buff = b""
        while True:
          data = self._socket.recv(128)
          if(len(data) == 0):
            #connection closed
            print("TS3 Socket closed")
            break
          buff += data
          while True:
            p = buff.partition(b"\n\r")
            if(p[1] == b""):
              break
            buff = p[2]
            self._handleLine(p[0].decode())
        #so the connection closed...
        if self._onUnhook != None:
          self._onUnhook()
      except (ConnectionRefusedError, ConnectionResetError):
        if self._onUnhook != None:
          self._onUnhook()
        time.sleep(5) #wait a little bit before trying again
  
  def _handleLine(self, line):
    #print("<=", line)
    if self._status == STATUS.Handshake1:
      self._handleHandshake1(line)
    elif self._status == STATUS.Handshake2:
      self._handleHandshake2(line)
    elif self._status == STATUS.Handshake3:
      self._handleHandshake3(line)
    else:
      self._handleHooked(line)
      
  def _handleHandshake1(self, line):
    if(line != TS3_GREETING):
      #FIXME error!
      print("Wrong greeting")
    self._status = STATUS.Handshake2

  def _handleHandshake2(self, line):
    self._status = STATUS.Handshake3

  def _handleHandshake3(self, line):
    self._status = STATUS.Hooked
    self._hookId = uuid.uuid4().hex
    for key in self._callbacks:
      if not key in EVENT_UNPACKER:
        raise Exception("Don't know how do unpack "+key.decode())
      self.sendCmd(self._hookId, 'clientnotifyregister', {'schandlerid':'1', 'event':key})
    self._acceptingCmd.set()
    if self._onHook != None:
      self._onHook(self._hookId)
    
  def _handleHooked(self, line):
    parts = line.partition(' ')
    if parts[1]!="" and parts[0] in self._callbacks:
      unpacked = EVENT_UNPACKER[parts[0]](parts[2])
      self._callbacks[parts[0]](unpacked)
    elif not self._acceptingCmd.is_set() and parts[0]=="error":
      self._handleError(parts[2])
    elif not self._acceptingCmd.is_set() and self._currentCmdUnpacker != None:
      #must be a response from a command
      if self._currentCmdCallback != None:
        self._currentCmdCallback(self._currentCmdUnpacker(line))
      self._currentCmdUnpacker = None
    else:
      #I have no idea what I just received!
      print("Unknown msg: ", line)
      
  def _handleError(self, data):
    error = unpackObject(data)
    #print(error)
    if error['id']!='0':
      print("Error: ", error['msg'])
      if self._currentCmdErrback != None:
        self._currentCmdErrback(error)
    self._acceptingCmd.set()

