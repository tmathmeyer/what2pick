
import copy
import dataclasses
import sqlite3
import threading
import time
import uuid


class UnixTime():
  @staticmethod
  def Now(_):
    return int(time.time())

  @staticmethod
  def FromTime(value):
    return UnixTime()

  def __eq__(self, _):
    return False


class TableColumnType():
  _typemap = {
    str: ('TEXT', str, str),
    int: ('INTEGER', int, int),
    bool: ('INTEGER', int, bool),
    uuid.UUID: ('TEXT', str, uuid.UUID),
    UnixTime: ('INTEGER', UnixTime.Now, UnixTime.FromTime)
  }

  @staticmethod
  def RegisterType(_type, sqltype, tosql, fromsql):
    TableColumnType._typemap[_type] = (sqltype, tosql, fromsql)

  @staticmethod
  def TypeFor(_type):
    if isinstance(_type, TableColumnType):
      return _type
    if _type not in TableColumnType._typemap:
      print(f'Warning, unsupported type {_type} stored as a string')
      _type = str
    sqlcol, tosql, fromsql = TableColumnType._typemap[_type]
    return TableColumnType(sqlcol, fromsql, tosql)

  @staticmethod
  def SplitInto(value, sep, fn):
    if not value:
      return []
    return [fn(v) for v in value.split(sep)]

  @staticmethod
  def JoinInto(value, sep, fn):
    if not value:
      return ''
    return sep.join([str(fn(v)) for v in value])

  def __init__(self, sqltext, fromsql, tosql):
    self._sqltext = sqltext
    self._fromsql = fromsql
    self._tosql = tosql

  def SqlText(self):
    return self._sqltext

  def FromSql(self, v):
    return self._fromsql(v)

  def ToSql(self, v):
    return self._tosql(v)


def PrimaryKey(_type):
  tct = TableColumnType.TypeFor(_type)
  tct._sqltext += ' PRIMARY KEY'
  return tct


def CSV(_type):
  tct = TableColumnType.TypeFor(_type)
  return TableColumnType('TEXT',
    lambda s: TableColumnType.SplitInto(s, ',', tct.FromSql),
    lambda v: TableColumnType.JoinInto(v, ',', tct.ToSql))


def TSV(_type):
  tct = TableColumnType.TypeFor(_type)
  return TableColumnType('TEXT',
    lambda s: TableColumnType.SplitInto(s, '\t', tct.FromSql),
    lambda v: TableColumnType.JoinInto(v, '\t', tct.ToSql))


def TableSpec(tablename:str):
  '''Converts a class into a dataclass with extra sql-y features.'''
  def TableSpecWrapper(clazz):
    clazz = dataclasses.dataclass(clazz)
    clazz.__tablespec_fields__ = {}
    clazz.__tablespec_tablename__ = tablename
    clazz.__tablespec_preupdate__ = None
    clazz.__tablespec_primarykey__ = None
    for name, field in clazz.__dataclass_fields__.items():
      clazz.__tablespec_fields__[name] = TableColumnType.TypeFor(field.type)
      if 'PRIMARY KEY' in clazz.__tablespec_fields__[name].SqlText():
        clazz.__tablespec_primarykey__ = name
    return clazz
  return TableSpecWrapper


class SQLStorageBase():
  def __init__(self, dbfile:str):
    self._conn_map:typing.Mapping[int, sqlite3.Connection] = {}
    self._database_file:str = dbfile

  def Connection(self, on_create_cb=lambda _:None) -> sqlite3.Connection:
    thread_id = threading.get_ident()
    if thread_id in self._conn_map:
      return self._conn_map[thread_id]
    self._conn_map[thread_id] = sqlite3.connect(self._database_file)
    on_create_cb(self._conn_map[thread_id])
    return self._conn_map[thread_id]

  def Cursor(self, on_connect_db=lambda _:None) -> sqlite3.Connection:
    return self.Connection(on_connect_db).cursor()

  def CreateTableForType(self, _type, noexec=False):
    if not hasattr(_type, '__tablespec_tablename__'):
      raise ValueError(f'{_type} must be a |sql_storage.TableSpec|')
    fields = _type.__tablespec_fields__
    name = _type.__tablespec_tablename__
    columns = ','.join([f'{k} {t.SqlText()}' for k,t in fields.items()])
    query = f'CREATE TABLE IF NOT EXISTS {name} ({columns})'
    if not noexec:
      self.Cursor().execute(query)
      self.Connection().commit()
    return query

  def Insert(self, impl, noexec=False):
    if not hasattr(impl, '__tablespec_tablename__'):
      raise ValueError(f'{impl} must be a |sql_storage.TableSpec|')
    fields = impl.__tablespec_fields__
    name = impl.__tablespec_tablename__
    columns = ','.join(fields.keys())
    values = ','.join(f':{field}' for field in fields.keys())
    rawdata = {k:v.ToSql(getattr(impl,k)) for k,v in fields.items()}
    query = f'INSERT into {name} ({columns}) values ({values})'
    if not noexec:
      self.Cursor().execute(query, rawdata)
      self.Connection().commit()
    return query, rawdata

  def Update(self, impl):
    if not hasattr(impl, '__tablespec_primarykey__'):
      raise ValueError(f'{impl} must be a |sql_storage.TableSpec|')
    sets = {}
    name = impl.__tablespec_tablename__
    pkey = impl.__tablespec_primarykey__
    fields = impl.__tablespec_fields__
    if not impl.__tablespec_preupdate__:
      self.Insert(impl)
      return

    for field, original in impl.__tablespec_preupdate__.items():
      current = getattr(impl, field)
      if current != original:
        sets[field] = current
    if not sets:
      return

    rawdata = {k:v.ToSql(getattr(impl,k)) for k,v in fields.items()}
    setstr = ','.join([f'{n} = :{n}' for n in sets])
    query = f'UPDATE {name} SET {setstr} WHERE {pkey} is :{pkey}'
    print(query)
    self.Cursor().execute(query, rawdata)
    self.Connection().commit()

  def GetAll(self, clazz, **keys):
    if not hasattr(clazz, '__tablespec_tablename__'):
      raise ValueError(f'{clazz} must be a |sql_storage.TableSpec|')
    fields = clazz.__tablespec_fields__
    name = clazz.__tablespec_tablename__
    columns = ','.join(fields.keys())
    querystr = 'AND'.join([f'{f} is :{f}' for f in keys.keys()])
    query = f'SELECT {columns} FROM {name} WHERE {querystr}'
    typed_keys = {k:fields[k].ToSql(v) for k,v in keys.items()}
    games = self.Cursor().execute(query, typed_keys).fetchall()
    self.Connection().commit()
    for unpacked_game in games:
      constructor_params = {}
      for value, (name, type_) in zip(unpacked_game, fields.items()):
        constructor_params[name] = type_.FromSql(value)
      impl = clazz(**constructor_params)
      impl.__tablespec_preupdate__ = copy.deepcopy(constructor_params)
      yield impl