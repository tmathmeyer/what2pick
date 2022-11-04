
import time
import uuid

from impulse.util import typecheck

from what2pick import sql_storage


@sql_storage.TableSpec('payshoff')
class PaysHoff:
  gameid: sql_storage.PrimaryKey(uuid.UUID)
  admin: uuid.UUID
  users: sql_storage.CSV(uuid.UUID)
  next_user: uuid.UUID
  must_add: sql_storage.CSV(uuid.UUID)
  options: sql_storage.TSV(str)
  decided: bool
  last_access: sql_storage.UnixTime

  def AdvanceToNextUser(self):
    self.next_user = self.users[
      (self.users.index(self.next_user) + 1) % len(self.users)]


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
      users = [player],
      next_user = player,
      must_add = [player],
      options = [],
      decided = False,
      last_access = 0)
    self.Insert(ph_game)
    return ph_game

  @typecheck.Ensure
  def GetGameById(self, gameid:uuid.UUID) -> PaysHoff | None:
    games = list(self.GetAll(PaysHoff, gameid=gameid))
    if len(games) != 1:
      return None
    return games[0]

  @typecheck.Ensure
  def JoinGame(self, gameid:uuid.UUID, player:uuid.UUID):
    game = self.GetGameById(gameid)
    if not game:
      return self.CreateGame(player), False
    if player in game.users:
      return game, False
    game.users.append(player)
    game.must_add.append(player)
    self.Update(game)
    return game, True

  @typecheck.Ensure
  def AddOption(self, gameid:uuid.UUID, player:uuid.UUID, option:str):
    game = self.GetGameById(gameid)
    if not game:
      raise ValueError('Invalid Game')
    if game.next_user != player:
      raise ValueError('Invalid User')
    if game.decided:
      raise ValueError('Game Over')

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
    if not game:
      raise ValueError('Invalid Game')
    if game.decided:
      raise ValueError('Game Over')
    if player not in (game.next_user, game.admin):
      raise ValueError('Admin or NextUser can remove')
    if option >= len(game.options):
      raise ValueError('Out of Bounds Option')
    if option < 0:
      raise ValuerError('Out of Bounds Option')
    if game.next_user in game.must_add:
      raise ValueError('Must add before removing')
    game.options = game.options[:option] + game.options[option+1:]
    if player == game.next_user:
      game.AdvanceToNextUser()
    self.Update(game)
    return game

  @typecheck.Ensure
  def Select(self, gameid:uuid.UUID, player:uuid.UUID) -> PaysHoff:
    game = self.GetGameById(gameid)
    if not game:
      raise ValueError('Invalid Game')
    if game.decided:
      raise ValueError('Game Over')
    if game.next_user != player:
      raise ValueError('Invalid User')
    if game.must_add:
      raise ValueError('Everyone Must Add')
    if len(game.options) != 1:
      raise ValueError('Invalid Selection')
    game.decided = True
    self.Update(game)
    return game

  @typecheck.Ensure
  def AdminSkipNextUser(self, gameid:uuid.UUID, player:uuid.UUID):
    game = self.GetGameById(gameid)
    if not game:
      raise ValueError('Invalid Game')
    if game.decided:
      raise ValueError('Game Over')
    if player != game.admin:
      raise ValueError('Must Be Admin')
    game.AdvanceToNextUser()
    self.Update(game)
    return game