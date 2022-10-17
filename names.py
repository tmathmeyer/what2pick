
import random

from impulse.util import resources


NAMELIST = []


def PrimeNameList():
  global NAMELIST
  with resources.Resources.Open('what2pick/names.txt') as f:
    NAMELIST = f.read().splitlines()


def GetRandomName():
  global NAMELIST
  if not NAMELIST:
    PrimeNameList()
  return NAMELIST[random.randint(0, len(NAMELIST) - 1)]


def GetRandomFullName():
  return f'{GetRandomName()} {GetRandomName()}'
