
import time
import uuid

from impulse.util import typecheck

from what2pick import names
from what2pick import sql_storage


@sql_storage.TableSpec('users')
class User:
  uid: sql_storage.PrimaryKey(uuid.UUID)
  pwd: uuid.UUID
  name: str
  lastaccess: sql_storage.UnixTime


class UserDAO(sql_storage.SQLStorageBase):
  def __init__(self, dbfile:str):
    super().__init__(dbfile)
    self.Cursor(on_connect_db=self._CreateTable)

  def _CreateTable(self, _):
    self.CreateTableForType(User)

  def CreateUser(self) -> User:
    user = User(
      uid = uuid.uuid4(),
      pwd = uuid.uuid4(),
      name = self.GetRandomName(),
      lastaccess = 0)
    self.Insert(user)
    return user

  @typecheck.Ensure
  def GetUsernameByUUID(self, uid:uuid.UUID) -> User | None:
    users = list(self.GetAll(User, uid=uid))
    if len(users) != 1:
      return None
    return users[0]

  @typecheck.Ensure
  def LoginAsUser(self, uid:uuid.UUID, pwd:uuid.UUID) -> User:
    user = self.GetUsernameByUUID(uid)
    if not user:
      return self.CreateUser()
    now = sql_storage.UnixTime.Now()
    if now - user.lastaccess.Value() > (60 * 60 * 24 * 31):
      return self.CreateUser()
    if user.pwd != pwd:
      return self.CreateUser()
    self.Update(user)
    return user

  @typecheck.Ensure
  def ChangeUsername(self, uid:uuid.UUID, pwd:uuid.UUID, name:str) -> User:
    user = self.LoginAsUser(uid, pwd)
    user.name = name[:22]
    self.Update(user)
    return user

  @typecheck.Ensure
  def GetRandomName(self) -> str:
    return names.GetRandomFullName()