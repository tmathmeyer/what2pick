
import os
import tempfile
import time
import uuid

from impulse.testing import unittest
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


class MockDAO(sql_storage.SQLStorageBase):
  pass


class SQLStorageUnittests(unittest.TestCase):
  def setup(self):
    self._tf = tempfile.mkstemp()[1]
    self._mock_dao = MockDAO(self._tf)

  def cleanup(self):
    os.system(f'rm -rf {self._tf}')

  def test_CreateTableForType(self):
    expected = '''CREATE TABLE IF NOT EXISTS payshoff (gameid TEXT PRIMARY KEY,
                                                       admin TEXT,
                                                       users TEXT,
                                                       next_user TEXT,
                                                       must_add TEXT,
                                                       options TEXT,
                                                       decided INTEGER,
                                                       last_access INTEGER)'''
    bloat = '\n                                                       '
    expected = expected.replace(bloat, '')
    actual = self._mock_dao.CreateTableForType(PaysHoff, noexec=True)
    self.assertEqual(expected, actual)

  def test_insertItems(self):
    admin = uuid.uuid4()
    gameid = uuid.uuid4()
    ph_game = PaysHoff(
      gameid = gameid,
      admin = admin,
      users = [admin],
      next_user = admin,
      must_add = [admin],
      options = [],
      decided = False,
      last_access = 0)


    self._mock_dao.CreateTableForType(PaysHoff)
    self._mock_dao.Insert(ph_game, noexec=False)
    gid = list(self._mock_dao.GetAll(PaysHoff, gameid=gameid))[0]
    print(gid, '\n')
    gid.must_add = []
    self._mock_dao.Update(gid)
    gid = list(self._mock_dao.GetAll(PaysHoff, gameid=gameid))[0]
    print(gid, '\n')
    gid.options.append('solid gold')
    time.sleep(3)
    self._mock_dao.Update(gid)
    gid = list(self._mock_dao.GetAll(PaysHoff, gameid=gameid))[0]
    print(gid, '\n')
