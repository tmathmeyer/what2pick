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
    self.Connection().commit()

  def _GetTimestamp(self):
    return int(time.time())

  def CreateGame(self, player:str):
    now = self._GetTimestamp()
    gameid = uuid.uuid4()
    cols = 'gameid,admin,userlist,nextuser,noaddyet,choices,lockedin,access'
    vals = f'"{gameid}","{player}","{player}","{player}","{player}","",0,{now}'
    self.Cursor().execute(f'insert into {self._name} ({cols}) values ({vals})')
    self.Connection().commit()
    return PaysHoff(
      gameid=gameid,
      admin=player,
      users=[player],
      nextuser=player,
      must_add=[player],
      options=[],
      decided=False)

  def GetGameById(self, gameid:str):
    cols = 'userlist,nextuser,noaddyet,choices,lockedin,admin'
    maybe_game = self.Cursor().execute(
      f'select {cols} from {self._name} where gameid is "{gameid}"').fetchall()
    self.Connection().commit()
    if not maybe_game:
      return None
    options = maybe_game[0][3].split('\t') if maybe_game[0][3] else []
    must_add = maybe_game[0][2].split(',') if maybe_game[0][2] else []
    return PaysHoff(
      gameid=gameid,
      admin=maybe_game[0][5],
      users=maybe_game[0][0].split(','),
      nextuser=maybe_game[0][1],
      must_add=must_add,
      options=options,
      decided=maybe_game[0][4])

  def JoinGame(self, gameid:str, player:str):
    game = self.GetGameById(gameid)
    if not game:
      return self.CreateGame(player)
    now = self._GetTimestamp()
    if player in game.users:
      return game
    game.users.append(player)
    game.must_add.append(player)
    users = ','.join(game.users)
    must_add = ','.join(game.users)
    setters = ','.join([
      f'access = {now}',
      f'userlist = "{users}"',
      f'noaddyet = "{must_add}"',
    ])
    self.Cursor().execute(
      f'update {self._name} set {setters} where gameid is "{gameid}"')
    self.Connection().commit()
    return game

  def AddOption(self, gameid:str, player:str, option:str):
    game = self.GetGameById(gameid)
    if not game:
      raise ValueError('Invalid Game')
    if game.nextuser != player:
      raise ValueError('Invalid User')
    if game.decided:
      raise ValueError('Game Over')
    game.options.append(option[:32].replace('"', "`"))
    choices = '\t'.join(game.options)
    now = self._GetTimestamp()
    nextuser = game.users[(game.users.index(player) + 1) % len(game.users)]
    must_add = game.must_add
    if player in must_add:
      must_add.remove(player)
    mustadd = ','.join(must_add)
    setters = ','.join([
      f'access = {now}',
      f'choices = "{choices}"',
      f'nextuser = "{nextuser}"',
      f'noaddyet = "{mustadd}"'
    ])
    query = f'update {self._name} set {setters} where gameid is "{gameid}"'
    self.Cursor().execute(query)
    self.Connection().commit()
    return game

  def RemoveOption(self, gameid:str, player:str, option:int):
    game = self.GetGameById(gameid)
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
    nextuser = game.nextuser
    if player == game.nextuser:
      nextuser = game.users[(game.users.index(player) + 1) % len(game.users)]
    setters = ','.join([
      f'access = {now}',
      f'choices = "{choices}"',
      f'nextuser = "{nextuser}"',
    ])
    self.Cursor().execute(
      f'update {self._name} set {setters} where gameid is "{gameid}"')
    self.Connection().commit()
    return game

  def Select(self, gameid:str, player:str):
    game = self.GetGameById(gameid)
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
    setters = ','.join([
      f'access = {now}',
      f'lockedin = TRUE'
    ])
    self.Cursor().execute(
      f'update {self._name} set {setters} where gameid is "{gameid}"')
    self.Connection().commit()
    return game