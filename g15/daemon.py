import socket
import struct

DISPLAY_WIDTH = 160
DISPLAY_HEIGHT = 43


CMD_KEY_HANDLER = b'\x10'
CMD_MKEYLEDS = b'\x20'
CMD_CONTRAST = b'\x40'
CMD_BACKLIGHT = b'\x80'
CMD_GET_KEYSTATE = b'k'
CMD_SWITCH_PRIORITIES = b'p'
CMD_IS_FOREGROUND = b'v'
CMD_IS_USER_SELECTED = b'u'
CMD_NEVER_SELECT = b'n'

class Daemon:

  # move keys elsewhere
  KEY_G1  = 1<<0
  KEY_G2  = 1<<1
  KEY_G3  = 1<<2
  KEY_G4  = 1<<3
  KEY_G5  = 1<<4
  KEY_G6  = 1<<5
  KEY_G7  = 1<<6
  KEY_G8  = 1<<7
  KEY_G9  = 1<<8
  KEY_G10 = 1<<9
  KEY_G11 = 1<<10
  KEY_G12 = 1<<11
  KEY_G13 = 1<<12
  KEY_G14 = 1<<13
  KEY_G15 = 1<<14
  KEY_G16 = 1<<15
  KEY_G17 = 1<<16
  KEY_G18 = 1<<17
  KEY_G19 = 1<<28
  KEY_G20 = 1<<29
  KEY_G21 = 1<<30
  KEY_G22 = 1<<31

  KEY_M1  = 1<<18
  KEY_M2  = 1<<19
  KEY_M3  = 1<<20
  KEY_MR  = 1<<21

  KEY_L1  = 1<<22
  KEY_L2  = 1<<23
  KEY_L3  = 1<<24
  KEY_L4  = 1<<25
  KEY_L5  = 1<<26

  KEY_LIGHT = 1<<27


  def __init__(self):
    self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_OOBINLINE, 1)
    self._socket.connect(("localhost", 15550))
    greeting = self._socket.recv(16)
    if greeting != b"G15 daemon HELLO":
      raise Exception("Communication error with daemon")
    self._socket.send(b"GBUF") #only supported screen type

  #TODO make use of "with" 
  def _close(self):
    self._socker.close()

  def draw(self, image):
    if image.size != (DISPLAY_WIDTH, DISPLAY_HEIGHT):
      raise Exception("Wrong image size")
    self._socket.send(image.convert("L").tobytes())
    
  def _cmd(self, cmd, respFormat):
    self._socket.sendall(cmd, socket.MSG_OOB)
    respSize = struct.calcsize(respFormat)
    resp = self._socket.recv(10*respSize)
    print(len(resp), ' ', resp)
    return struct.unpack(respFormat, resp)[0]
    
  def getKeystate(self):
    return self._cmd(CMD_GET_KEYSTATE, "Ixxxx")
    
    
