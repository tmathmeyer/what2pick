
import dataclasses
import enum
import flask


class Method(enum.Enum):
  GET = 'GET',
  PUT = 'PUT',
  PATCH = 'PATCH',
  DELETE = 'DELETE',
  POST = 'POST',
  HEAD = 'HEAD',


class Clask():
  @dataclasses.dataclass
  class DataPack:
    method: Method
    path: str

    def GetRouter(self, app):
      return app.route(self.path, methods=[self.method.name])
  
  @staticmethod
  def Route(*args, **kwargs):
    if len(args) == 1:
      args[0]._clask = Clask.DataPack(
        Method.GET, f'/{args[0].__name__.lower()}')
      return args[0]
    def Decorator(func):
      defaults = {'method': Method.GET, 'path': f'/{func.__name__.lower()}'}
      defaults.update(kwargs)
      func._clask = Clask.DataPack(**defaults)
      return func
    return Decorator

  @classmethod
  def Launch(cls, app, *args, **kwargs):
    instance = cls(*args, **kwargs)
    for ent in dir(cls):
      entry = getattr(cls, ent)
      if hasattr(entry, '_clask'):
        datapack = getattr(entry, '_clask')
        datapack.GetRouter(app)(Clask.Bind(instance, entry, datapack))

  @classmethod
  def Bind(cls, instance, entry, datapack):
    def LacksSelf(*args, **kwargs):
      if datapack.method in (Method.POST, Method.PUT, Method.PATCH):
        kwargs['data'] = flask.request.get_json()
      return entry(instance, *args, **kwargs)
    LacksSelf.__name__ = f'__clask_{instance.__name__}_{entry.__name__}'
    return LacksSelf