import socket

DISPLAY_WIDTH = 160
DISPLAY_HEIGHT = 43

class G15daemon:

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
