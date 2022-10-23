
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

from what2pick import names
from what2pick import sql_storage


@dataclass
class User:
  uid: str
  pwd: str
  name: str
  lastaccess: int


class UserDAO(sql_storage.SQLStorageBase):
  def __init__(self, dbfile:str):
    super().__init__(dbfile)
    self.Cursor(on_connect_db=self._CreateTable)

  def _CreateTable(self, _):
    self.Cursor().execute('''
      create table IF NOT EXISTS users (
        uid TEXT PRIMARY KEY,
        pwd TEXT
        name TEXT
        access INTEGER)''')
    self.Connection().commit()

  def _GetTimestamp(self):
    return int(time.time())

  def LoginAsUser(self, uid, pwd):
    query = 'SELECT pwd,name,access FROM users WHERE uid = :uid'
    maybe_user = self.Cursor().execute(query, {'uid': uid}).fetchall()
    self.Connection().commit()
    if not maybe_user:
      return self.CreateUser()
    now = self._GetTimestamp()
    if now - int(maybe_user[0][2]) > (60 * 60 * 24 * 3):
      return self.CreateUser()
    if maybe_user[0][0] != pwd:
      return self.CreateUser()
    query = 'UPDATE users SET access = :now where uid is :uid'
    self.Cursor().execute(query, {'uid': uid, 'now': now})
    self.Connection().commit()
    return User(uid, *maybe_user[0])

  def ChangeUsername(self, uid, pwd, name):
    user = self.LoginAsUser(uid, pwd)
    now = self._GetTimestamp()
    name = name[:16]
    query = 'UPDATE users SET name = :name WHERE uid IS :uid'
    self.Cursor().execute(query, {'uid': user.uid, 'name': name})
    self.Connection().commit()
    return User(user.uid, user.pwd, name, user.lastaccess)

  def GetUsernameByUUID(self, uid):
    query = 'SELECT name FROM users WHERE uid IS :uid'
    maybe_user = self.Cursor().execute(query, {'uid': uid}).fetchall()
    self.Connection().commit()
    if not maybe_user:
      return None
    return maybe_user[0][0]

  def CreateUser(self):
    uid = str(uuid.uuid4())
    pwd = str(uuid.uuid4())
    name = self.GetRandomName()
    now = self._GetTimestamp()
    query = '''INSERT INTO users (uid,pwd,name,access)
               VALUES (:uid, :pwd, :name, :now)'''
    self.Cursor().execute(query, {
      'uid': uid, 'pwd': pwd, 'name': name, 'now': now})
    self.Connection().commit()
    return User(uid, pwd, name, now)

  def GetRandomName(self):
    return names.GetRandomFullName()