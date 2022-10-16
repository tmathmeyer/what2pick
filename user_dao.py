
'''
field        | type         | desc
-------------|--------------|----------------------------------------
uuid         | str          | the user id
pwd          | str          | the user "password". Unchangeable.
name         | str          | user settable name. 8 char max.
lastaccess   | number       | last timestamp this user was accessed
'''

import time
import uuid

from dataclasses import dataclass

from what2pick import sql_storage


@dataclass
class User:
  uid: str
  pwd: str
  name: str
  lastaccess: int


class UserDAO(sql_storage.SQLStorageBase):
  _name = 'users'

  def __init__(self, dbfile:str):
    super().__init__(dbfile)
    self.Cursor(on_connect_db=self._CreateTable)

  def _CreateTable(self, _):
    cols = ','.join([
      'uid TEXT PRIMARY KEY',
      'pwd TEXT',
      'name TEXT',
      'access INTEGER'
    ])
    self.Cursor().execute(f'create table IF NOT EXISTS {self._name} ({cols})')
    self.Connection().commit()

  def _GetTimestamp(self):
    return int(time.time())

  def LoginAsUser(self, uid, pwd):
    query = f'select pwd,name,access from {self._name} where uid is "{uid}"'
    maybe_user = self.Cursor().execute(query).fetchall()
    if not maybe_user:
      return self.CreateUser()
    now = self._GetTimestamp()
    if now - int(maybe_user[0][2]) > (60 * 60 * 24 * 3):
      return self.CreateUser()
    if maybe_user[0][0] != pwd:
      return self.CreateUser()
    query = f'update {self._name} set access = {now} where uid is "{uid}"'
    self.Cursor().execute(query)
    self.Connection().commit()
    return User(uid, *maybe_user[0])

  def ChangeUsername(self, uid, pwd, name):
    user = self.LoginAsUser(uid, pwd)
    now = self._GetTimestamp()
    query = f'update {self._name} set name = "{name}" where uid is "{user.uid}"'
    self.Cursor().execute(query)
    return User(user.uid, user.pwd, name, user.lastaccess)

  def GetUsernameByUUID(self, uid):
    maybe_user = self.Cursor().execute(
      f'select name from {self._name} where uid is {uid}').fetchall()
    self.Connection().commit()
    if not maybe_user:
      return None
    return maybe_user[0][0]

  def CreateUser(self):
    now = self._GetTimestamp()
    uid = str(uuid.uuid4())
    pwd = str(uuid.uuid4())
    name = self.GetRandomName()
    cols = 'uid,pwd,name,access'
    vals = f'"{uid}","{pwd}","{name}",{now}'
    query = f'insert into {self._name} ({cols}) values ({vals})'
    self.Cursor().execute(query)
    self.Connection().commit()
    return User(uid, pwd, name, now)

  def GetRandomName(self):
    return 'Ted Meyer'