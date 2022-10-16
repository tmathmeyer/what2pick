'''

Pays Hoff Circle Database

field        | type         | desc
-------------|--------------|----------------------------------------
gameid       | str          | identifying uuid for the game
userlist     | str          | comma separated list of users, in order
nextuser     | str          | uuid of the user who is next
noaddyet     | str          | CSL of users who havent added yet
choices      | str          | TSL of string choices
lockedin     | bool         | is the |choices| locked? game over.
lastaccess   | number       | last timestamp this game was accessed

'''

import time
import uuid

from dataclasses import dataclass

from what2pick import sql_storage


@dataclass
class PaysHoff:
  gameid: str
  admin: str
  users: [str]
  nextuser: str
  must_add: [str]
  options: [str]
  decided: bool


class PaysHoffDAO(sql_storage.SQLStorageBase):
  _name = 'payshoff'

  def __init__(self, dbfile:str):
    super().__init__(dbfile)
    self.Cursor(on_connect_db=self._CreateTable)

  def _CreateTable(self, _):
    cols = ','.join([
      'gameid TEXT PRIMARY KEY',
      'admin TEXT',
      'userlist TEXT',
      'nextuser TEXT',
      'noaddyet TEXT',
      'choices TEXT',
      'lockedin INTEGER',
      'access INTEGER',
    ])
    self.Cursor().execute(f'create table IF NOT EXISTS {self._name} ({cols})')

  def _GetTimestamp(self):
    return int(time.time())

  def CreateGame(self, player:str):
    now = self._GetTimestamp()
    gameid = uuid.uuid4()
    cols = 'gameid,userlist,nextuser,noaddyet,choices,lockedin,admin'
    vals = f'"{gameid}","{player}","{player}","{player}","",0,{now}'
    self.Cursor().execute(
      f'insert into {self._name} ({cols}) values ({vals})')
    return PaysHoff(gameid, [player], player, [player], [], False)

  def GetGameById(self, gameid:str):
    cols = 'userlist,nextuser,noaddyet,choices,lockedin,admin'
    maybe_game = self.Cursor().execute(
      f'select {cols} from {self._name} where gameid is {gameid}').fetchall()
    if not maybe_game:
      return None
    return PaysHoff(
      gameid=gameid,
      admin=maybe_game[0][5],
      users=maybe_game[0][0].split(','),
      nextuser=maybe_game[0][1],
      must_add=maybe_game[0][2].split(','),
      options=maybe_game[0][3].split('\t'),
      decided=maybe_game[0][4])

    def JoinGame(self, gameid:str, player:str):
      game = GetGameById(gameid)
      if not game:
        return CreateGame(player)
      now = self._GetTimestamp()
      game.users = list(set(game.users) + set([player]))
      users = ','.join(game.users)
      access = f'access = {now}'
      userlist = f'userlist = "{users}"'
      self.Cursor().execute(
        f'update {self._name} {access},{userlist} where gameid is {gameid}')
      return game

    def AddOption(self, gameid:str, player:str, option:str):
      game = GetGameById(gameid)
      if not game:
        raise ValueError('Invalid Game')
      if game.nextuser != player:
        raise ValueError('Invalid User')
      if game.decided:
        raise ValueError('Game Over')
      game.options.append(option[:32].replace('"', "`"))
      choices = '\t'.join(game.options)
      now = self._GetTimestamp()
      access = f'access = {now}'
      options = f'choices = "{choices}"'
      self.Cursor().execute(
        f'update {self._name} {access},{options} where gameid is {gameid}')
      return game

    def RemoveOption(self, gameid:str, player:str, option:int):
      game = GetGameById(gameid)
      if not game:
        raise ValueError('Invalid Game')
      if game.decided:
        raise ValueError('Game Over')
      if player not in (game.nextuser, game.admin):
        raise ValueError('Invalid User')
      if option >= len(game.options):
        raise ValueError('Invalid Option')
      if game.nextuser in game.must_add:
        raise ValueError('Must add before removing')
      game.options = game.options[:option] + game.options[option+1:]
      choices = '\t'.join(game.options)
      now = self._GetTimestamp()
      access = f'access = {now}'
      options = f'choices = "{choices}"'
      self.Cursor().execute(
        f'update {self._name} {access},{options} where gameid is {gameid}')
      return game

    def Select(self, gameid:str, player:str):
      game = GetGameById(gameid)
      if not game:
        raise ValueError('Invalid Game')
      if game.decided:
        raise ValueError('Game Over')
      if game.nextuser != player:
        raise ValueError('Invalid User')
      if game.must_add:
        raise ValueError('Everyone Must Add')
      if len(game.options) != 1:
        raise ValueError('Invalid Selection')
      now = self._GetTimestamp()
      access = f'access = {now}'
      decided = 'decided = TRUE'
      self.Cursor().execute(
        f'update {self._name} {access},{decided} where gameid is {gameid}')
      return game