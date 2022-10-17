
import random


NAMELIST = []


def PrimeNameList():
  global NAMELIST
  with open('/usr/share/dict/words') as f:
    words = f.read().splitlines()
    def nameword(word):
      if not word:
        return False
      if not word[0].isupper():
        return False
      if word.isupper():
        return False
      if '\'' in word:
        return False
      return True
    NAMELIST = [word for word in words if nameword(word)]


def GetRandomName():
  global NAMELIST
  if not NAMELIST:
    PrimeNameList()
  return NAMELIST[random.randint(0, len(NAMELIST) - 1)]


def GetRandomFullName():
  return f'{GetRandomName()} {GetRandomName()}'