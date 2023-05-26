
import time
import uuid

from pylib import typecheck
from pylib.web import http

from what2pick import sql_storage


@sql_storage.TableSpec('payshoff')
class PaysHoff:
  gameid: sql_storage.PrimaryKey(uuid.UUID)
  admin: uuid.UUID
  players: sql_storage.CSV(uuid.UUID)
  watchers: sql_storage.CSV(uuid.UUID)
  next_player: uuid.UUID
  must_add: sql_storage.CSV(uuid.UUID)
  options: sql_storage.TSV(str)
  decided: bool
  active_timer: bool
  seconds_to_pick: int
  kick_on_last_remove: bool
  last_access: sql_storage.UnixTime

  def AdvanceToNextUser(self):
    self.next_player = self.players[
      (self.players.index(self.next_player) + 1) % len(self.players)]

  def CheckAdmin(self, user:uuid.UUID):
    if user != self.admin:
      raise http.HttpException('Must Be Admin', http.Code.FORBIDDEN)

  def CheckAllowChanges(self):
    if self.decided:
      raise http.HttpException('Game Ended.', http.Code.METHOD_NOT_ALLOWED)

  def CheckNextPlayer(self, user:uuid.UUID):
    if self.next_player != user:
      raise http.HttpException('Not your turn', http.Code.METHOD_NOT_ALLOWED)


class PaysHoffDAO(sql_storage.SQLStorageBase):
  def __init__(self, dbfile:str):
    super().__init__(dbfile)
    self.Cursor(on_connect_db=self._CreateTable)

  def _CreateTable(self, _):
    self.CreateTableForType(PaysHoff)

  def _GetTimestamp(self):
    return int(time.time())
    
  @typecheck.Ensure
  def CreateGame(self, player:uuid.UUID) -> PaysHoff:
    gameid = uuid.uuid4()
    ph_game = PaysHoff(
      gameid = gameid,
      admin = player,
      players = [player],
      watchers = [],
      next_player = player,
      must_add = [player],
      options = [],
      decided = False,
      active_timer = False,
      seconds_to_pick = 0,
      kick_on_last_remove = False,
      last_access = 0)
    self.Insert(ph_game)
    return ph_game

  @typecheck.Ensure
  def GetGameById(self, gameid:uuid.UUID, noexcept=False) -> PaysHoff|None:
    games = list(self.GetAll(PaysHoff, gameid=gameid))
    if len(games) != 1:
      if noexcept:
        return None
      raise http.HttpException.NotFound(gameid)
    return games[0]

  @typecheck.Ensure
  def JoinGame(self, gameid:uuid.UUID, player:uuid.UUID):
    game = self.GetGameById(gameid, noexcept=True)
    if not game:
      return self.CreateGame(player), False
    if player in game.players:
      return game, False
    if player in game.watchers:
      return game, False
    game.players.append(player)
    game.must_add.append(player)
    self.Update(game)
    return game, True

  @typecheck.Ensure
  def ToggleKickOnLastRemoveMode(self, gid:uuid.UUID, admin:uuid.UUID):
    game = self.GetGameById(gid)
    game.CheckAllowChanges()
    game.CheckAdmin(admin)
    game.kick_on_last_remove = not game.kick_on_last_remove
    self.Update(game)
    return game

  @typecheck.Ensure
  def SetPlayerToWatcher(self, gid:uuid.UUID, player:uuid.UUID, adm:uuid.UUID):
    game = self.GetGameById(gid)
    game.CheckAllowChanges()
    game.CheckAdmin(adm)
    if len(game.players) == 1:
      raise http.HttpException('must keep 1 player', http.Code.NOT_ACCEPTABLE)
    if player not in game.players:
      raise http.HttpException('not active player', http.Code.BAD_REQUEST)
    if player in game.watchers:
      raise http.HttpException('already a watcher', http.Code.BAD_REQUEST)
    if game.next_player == player:
      game.AdvanceToNextUser()
    game.watchers.append(player)
    game.players.remove(player)
    if player in game.must_add:
      game.must_add.remove(player)
    self.Update(game)
    return game, True

  @typecheck.Ensure
  def AddOption(self, gameid:uuid.UUID, player:uuid.UUID, option:str):
    game = self.GetGameById(gameid)
    game.CheckAllowChanges()
    game.CheckNextPlayer(player)
    option = option[:30].replace('\t', '_')
    game.options.append(option)
    if player in game.must_add:
      game.must_add.remove(player)
    game.AdvanceToNextUser()
    self.Update(game)
    return game

  @typecheck.Ensure
  def RemoveOption(self, gameid:uuid.UUID, player:uuid.UUID, option:int):
    game = self.GetGameById(gameid)
    game.CheckAllowChanges()
    if player not in (game.next_player, game.admin):
      raise http.HttpException('Not your turn', http.Code.METHOD_NOT_ALLOWED)
    if option >= len(game.options) or option < 0:
      raise http.HttpException('Index out of bounds', http.Code.BAD_REQUEST)
    if game.next_player in game.must_add:
      raise http.HttpException('Everyone must add', http.Code.NOT_ACCEPTABLE)
    if len(game.options) == 1 and len(game.players) == 1:
      raise http.HttpException('You must Select!', http.Code.NOT_ACCEPTABLE)

    game.options = game.options[:option] + game.options[option+1:]
    if player == game.next_player:
      game.AdvanceToNextUser()
      if not len(game.options) and game.kick_on_last_remove:
        game.players.remove(player)
        game.watchers.append(player)
    self.Update(game)
    return game

  @typecheck.Ensure
  def Select(self, gameid:uuid.UUID, player:uuid.UUID) -> PaysHoff:
    game = self.GetGameById(gameid)
    game.CheckAllowChanges()
    game.CheckNextPlayer(player)
    if game.must_add:
      raise http.HttpException('Everyone must add', http.Code.NOT_ACCEPTABLE)
    if len(game.options) != 1:
      raise http.HttpException('Too many choices', http.Code.METHOD_NOT_ALLOWED)
    game.decided = True 
    self.Update(game)
    return game

  @typecheck.Ensure
  def AdminSkipNextUser(self, gameid:uuid.UUID, player:uuid.UUID):
    game = self.GetGameById(gameid)
    game.CheckAdmin(player)
    game.CheckAllowChanges()
    game.AdvanceToNextUser()
    self.Update(game)
    return game