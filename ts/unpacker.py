def unpackObject(string):
  result = {}
  for attr in string.split(' '):
    kv = attr.partition('=')
    result[kv[0]] = unpackString(kv[2])
  return result
  
def unpackString(string):
  #TODO incomplete
  return string.replace('\\s', ' ').replace('\\/', '/')

