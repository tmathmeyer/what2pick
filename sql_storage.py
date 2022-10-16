
import sqlite3
import threading


class SQLStorageBase():
  def __init__(self, dbfile:str):
    self._conn_map:typing.Mapping[int, sqlite3.Connection] = {}
    self._database_file:str = dbfile

  def _Connection(self, on_create_cb=lambda _:None) -> sqlite3.Connection:
    thread_id = threading.get_ident()
    if thread_id in self._conn_map:
      return self._conn_map[thread_id]
    self._conn_map[thread_id] = sqlite3.connect(self._database_file)
    on_create_cb(self._conn_map[thread_id])
    return self._conn_map[thread_id]

  def Cursor(self, on_connect_db=lambda _:None) -> sqlite3.Connection:
    return self._Connection(on_connect_db)