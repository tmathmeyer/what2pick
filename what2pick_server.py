
import datetime
import flask
import jinja2
import logging
import time
import threading
import uuid

from impulse.util import resources

from what2pick import clask
from what2pick import user_dao
from what2pick import pays_hoff_dao


class AutoReloader:
  def __init__(self):
    self._condition = threading.Condition()

  def notify_task_completion(self):
    with self._condition:
      self._condition.notify_all()

  def wait_for_notice(self):
    try:
      with self._condition:
        self._condition.wait(timeout=60)
    except:
      time.sleep(30)


class Application(clask.Clask):
  def __init__(self, db_file:str):
    self._users = user_dao.UserDAO(db_file)
    self._payshoff = pays_hoff_dao.PaysHoffDAO(db_file)
    self._autoreloads = {}

  def GetUser(self):
    agent = flask.request.user_agent.string
    if ('FB' in agent) or ('Messenger' in agent) or ('facebook' in agent):
      return None
    username = flask.request.cookies.get('uid')
    password = flask.request.cookies.get('pwd')
    if not (username or password):
      return self._users.CreateUser()
    return self._users.LoginAsUser(uuid.UUID(username), uuid.UUID(password))

  def PersistLogin(self, res, user):
    expire_date = datetime.datetime.now() + datetime.timedelta(days=90)
    res.set_cookie("uid", value=str(user.uid), expires=expire_date)
    res.set_cookie("pwd", value=str(user.pwd), expires=expire_date)
    return res

  def NotifyReload(self, uuid):
    if uuid in self._autoreloads:
      self._autoreloads[uuid].notify_task_completion()

  def Wait(self, uuid):
    if uuid not in self._autoreloads:
      self._autoreloads[uuid] = AutoReloader()
    self._autoreloads[uuid].wait_for_notice()

  @clask.Clask.Route(path='/')
  def Index(self):
    user = self.GetUser()
    res = flask.make_response(flask.render_template(
      'index.html',
      username = user.name
    ))
    return self.PersistLogin(res, user)

  @clask.Clask.Route(method=clask.Method.POST)
  def SetName(self, data):
    user = self.GetUser()
    name = data['name'][:16]
    if name.strip():
      user = self._users.ChangeUsername(user.uid, user.pwd, name)
    res = flask.make_response('OK')
    return self.PersistLogin(res, user)

  @clask.Clask.Route(path="/p")
  def CreateGame(self):
    user = self.GetUser()
    game = self._payshoff.CreateGame(user.uid)
    if game:
      res = flask.make_response('OK', 302)
      res.headers['Location'] = f'/p/{game.gameid}'
      return self.PersistLogin(res, user)
    else:
      return 'Fatal Error. Contact admin', 500

  @clask.Clask.Route(path='/p/<gid>')
  def GetGameDetail(self, gid):
    gid = uuid.UUID(gid)
    user = self.GetUser()
    if not user:
      return 'Open In Browser, fb webview is broken', 200
    game, trigger_update = self._payshoff.JoinGame(gid, user.uid)
    if game.gameid != gid:
      res = flask.make_response('OK', 302)
      res.headers['Location'] = f'/p/{game.gameid}'
      return self.PersistLogin(res, user)
    am_current = (game.next_user == user.uid) and (not game.decided)
    am_admin = game.admin == user.uid and (not game.decided)
    can_remove = (am_current and (user.name not in game.must_add)) or am_admin
    can_select = am_current and (not game.must_add) and len(game.options) == 1
    current_player = self._users.GetUsernameByUUID(game.next_user)
    res = flask.make_response(flask.render_template(
      'payshoff.html',
      username = user.name,
      gameoptions = game.options,
      can_remove = can_remove,
      can_add = am_current,
      can_select = can_select,
      decided = game.decided,
      game_id = game.gameid,
      current_player = current_player,
      am_admin = am_admin,
      debug_info = f'{user}\n{game}',
    ))
    if trigger_update:
      self.NotifyReload(gid)
    return self.PersistLogin(res, user)

  @clask.Clask.Route(path='/p/<gid>/add', method=clask.Method.POST)
  def AddToPaysHoffGame(self, gid, data):
    gid = uuid.UUID(gid)
    user = self.GetUser()
    try:
      game = self._payshoff.AddOption(gid, user.uid, data['option'])
      res = flask.make_response('OK', 200)
      self.NotifyReload(gid)
      return self.PersistLogin(res, user)
    except ValueError as e:
      return str(e), 400

  @clask.Clask.Route(path='/p/<gid>/del', method=clask.Method.POST)
  def RemoveFromPaysHoffGame(self, gid, data):
    gid = uuid.UUID(gid)
    user = self.GetUser()
    try:
      game = self._payshoff.RemoveOption(gid, user.uid, int(data['option']))
      res = flask.make_response('OK', 200)
      self.NotifyReload(gid)
      return self.PersistLogin(res, user)
    except ValueError as e:
      return str(e), 400

  @clask.Clask.Route(path='/p/<gid>/adm_skip', method=clask.Method.POST)
  def AdminSkipNextUser(self, gid, data):
    gid = uuid.UUID(gid)
    user = self.GetUser()
    try:
      game = self._payshoff.AdminSkipNextUser(gid, user.uid)
      res = flask.make_response('OK', 200)
      self.NotifyReload(gid)
      return self.PersistLogin(res, user)
    except ValueError as e:
      return str(e), 400

  @clask.Clask.Route(path='/p/<gid>/sel', method=clask.Method.POST)
  def FinishPaysHoffGame(self, gid, data):
    gid = uuid.UUID(gid)
    user = self.GetUser()
    try:
      game = self._payshoff.Select(gid, user.uid)
      res = flask.make_response('OK', 200)
      self.NotifyReload(gid)
      return self.PersistLogin(res, user)
    except ValueError as e:
      return str(e), 400

  @clask.Clask.Route(path='/p/<gid>/poll')
  def AwaitRefreshNotice(self, gid):
    gid = uuid.UUID(gid)
    game = self._payshoff.GetGameById(gid)
    if not game:
      return 'no game', 404
    self.Wait(gid)
    return 'reload', 200


def CreateApp():
  content = f'{resources.Resources.Dir()}/what2pick/frontend'
  app = flask.Flask(__name__, static_folder=content, template_folder=content)
  Application.Launch(app, 'storage.db')
  return app


import gunicorn.app.base
class GunicornHost(gunicorn.app.base.BaseApplication):
  def __init__(self, app, options=None):
    self.options = {
      'worker_class': 'eventlet'
    }
    self.options.update(options or {})
    self.application = app
    super().__init__()

  def load_config(self):
    for k,v in self.options.items():
      if k in self.cfg.settings and v is not None:
        self.cfg.set(k.lower(), v)
      else:
        print(f'failed to set option: {k}')

  def load(self):
    return self.application


def main():
  logging.getLogger('eventlet').disabled = True #(logging.ERROR)
  logging.getLogger('werkzeug').disabled = True #(logging.ERROR)
  app = CreateApp()

  # Run with Gunicorn
  GunicornHost(app, {'bind': '0.0.0.0:5000'}).run()

  # Run with Werzkeurgerbergerfleurger
  # app.run(host='0.0.0.0', port=5000)

  # Run with Eventlet
  #from eventlet import wsgi
  #wsgi.server(eventlet.listen(('0.0.0.0', 5000)), app)
