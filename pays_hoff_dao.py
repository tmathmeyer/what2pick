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

  def __init__(self, dbfile:str):
    super().__init__(dbfile)
    self.Cursor(on_connect_db=self._CreateTable)

  def _CreateTable(self, _):
    self.Cursor().execute('''CREATE table IF NOT EXISTS payshoff (
      gameid TEXT PRIMARY KEY,
      admin TEXT,
      userlist TEXT,
      nextuser TEXT,
      noaddyet TEXT,
      choices TEXT,
      lockedin INTEGER,
      access INTEGER)''')
    self.Connection().commit()

  def _GetTimestamp(self):
    return int(time.time())

  def CreateGame(self, player:str):
    gameid = str(uuid.uuid4())
    query = '''INSERT into payshoff (
                 gameid, admin, userlist, nextuser,
                 noaddyet, choices, lockedin, access)
               values (
                 :gameid, :player, :player, :player, :player, "", 0, :now)'''
    self.Cursor().execute(query, {
      'gameid': gameid, 'player': player, 'now': self._GetTimestamp()})
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
    query = 'SELECT * FROM payshoff WHERE gameid is :gameid'
    maybe_game = self.Cursor().execute(query, {'gameid': gameid}).fetchall()
    self.Connection().commit()
    if not maybe_game:
      return None
    _, admin, users, nextuser, noaddyet, choices, lockedin, _ = maybe_game[0]
    choices = choices.split('\t') if choices else []
    noaddyet = noaddyet.split(',') if noaddyet else []
    users = users.split(',')
    return PaysHoff(
      gameid=gameid,
      admin=admin,
      users=users,
      nextuser=nextuser,
      must_add=noaddyet,
      options=choices,
      decided=lockedin)

  def JoinGame(self, gameid:str, player:str) -> (PaysHoff, bool):
    game = self.GetGameById(gameid)
    if not game:
      return self.CreateGame(player), False
    now = self._GetTimestamp()
    if player in game.users:
      return game, False
    game.users.append(player)
    game.must_add.append(player)
    query = '''UPDATE payshoff SET
                 access = :now,
                 userlist = :users,
                 noaddyet = :must_add
               WHERE gameid IS :gameid'''
    self.Cursor().execute(query, {
      'now': self._GetTimestamp(),
      'users': ','.join(game.users),
      'must_add': ','.join(game.must_add),
      'gameid': gameid,
    })
    self.Connection().commit()
    return game, True

  def AddOption(self, gameid:str, player:str, option:str):
    game = self.GetGameById(gameid)
    if not game:
      raise ValueError('Invalid Game')
    if game.nextuser != player:
      raise ValueError('Invalid User')
    if game.decided:
      raise ValueError('Game Over')
    game.options.append(option[:16].replace('\t', '  '))
    nextuser = game.users[(game.users.index(player) + 1) % len(game.users)]
    must_add = game.must_add
    if player in must_add:
      must_add.remove(player)
    query = '''UPDATE payshoff SET
                 access = :now,
                 choices = :choices,
                 nextuser = :nextuser,
                 noaddyet = :mustadd
               WHERE gameid IS :gameid'''
    self.Cursor().execute(query, {
      'now': self._GetTimestamp(),
      'choices': '\t'.join(game.options),
      'nextuser': nextuser,
      'mustadd': ','.join(must_add),
      'gameid': gameid
    })
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
    nextuser = game.nextuser
    if player == game.nextuser:
      nextuser = game.users[(game.users.index(player) + 1) % len(game.users)]
    query = '''UPDATE payshoff SET
                 access = :now,
                 choices = :choices,
                 nextuser = :nextuser
               WHERE gameid IS :gameid'''
    self.Cursor().execute(query, {
      'now': self._GetTimestamp(),
      'choices': '\t'.join(game.options),
      'nextuser': nextuser,
      'gameid': gameid
    })
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
    query = '''UPDATE payshoff SET
                 access = :now,
                 lockedin = TRUE
               WHERE gameid IS :gameid'''
    self.Cursor().execute(query, {
      'now': self._GetTimestamp(), 'gameid': gameid})
    self.Connection().commit()
    return game