
import datetime
import flask
import jinja2
import logging
import time
import threading
import uuid

from impulse.util import resources
from pylib.web import clask
from pylib.web import gunicorn
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

  def GetUser(self) -> user_dao.User:
    username = flask.request.cookies.get('uid')
    password = flask.request.cookies.get('pwd')
    if not (username or password):
      return None
    return self._users.LoginAsUser(uuid.UUID(username), uuid.UUID(password))

  def SaveLogin(self, res:flask.Response, user:user_dao.User) -> user_dao.User:
    if user is None:
      return res
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
    user_is_logged_in:bool = (user != None)
    username:str = user.name if user else ""
    res = flask.make_response(flask.render_template(
      'index.html',
      user_is_logged_in = user_is_logged_in,
      username = username
    ))
    return self.SaveLogin(res, user)

  @clask.Clask.Route(path='/signup/<redir>')
  def CreateUser(self, redir:str):
    user = self.GetUser()
    if not user:
      user = self._users.CreateUser()
    location = '/'
    if redir == 'p':
      game_id = flask.request.args.get('gid')
      if game_id:
        location = f'/p/{game_id}'
    return self.SaveLogin(flask.redirect(location, 307), user)

  @clask.Clask.Route(method=clask.Method.POST)
  def SetName(self, name):
    user = self.GetUser()
    if user is None:
      return 'no', 400
    name = name[:16].strip()
    if name:
      user = self._users.ChangeUsername(user.uid, user.pwd, name)
    res = flask.make_response('OK')
    return self.SaveLogin(res, user)

  @clask.Clask.Route(path="/p")
  def CreateGame(self):
    user = self.GetUser()
    if user is None:
      return 'must login to create a game', 400
    game = self._payshoff.CreateGame(user.uid)
    if game:
      res = flask.make_response('OK', 302)
      res.headers['Location'] = f'/p/{game.gameid}'
      return self.SaveLogin(res, user)
    else:
      return 'Fatal Error. Contact admin', 500

  @clask.Clask.Route(path='/p/<gid>')
  def GetGameDetail(self, gid):
    gid = uuid.UUID(gid)
    user = self.GetUser()
    if not user:
      return flask.make_response(flask.render_template(
        'payshoff.html',
        game_id = gid,
        user_is_logged_in = False))
    game, trigger_update = self._payshoff.JoinGame(gid, user.uid)
    if game.gameid != gid:
      res = flask.make_response('OK', 302)
      res.headers['Location'] = f'/p/{game.gameid}'
      return self.SaveLogin(res, user)
    am_current = (game.next_user == user.uid) and (not game.decided)
    am_admin = game.admin == user.uid and (not game.decided)
    can_remove = (am_current and (user.name not in game.must_add)) or am_admin
    can_select = am_current and (not game.must_add) and len(game.options) == 1
    current_player = self._users.GetUsernameByUUID(game.next_user)
    res = flask.make_response(flask.render_template(
      'payshoff.html',
      user_is_logged_in = True,
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
    return self.SaveLogin(res, user)

  @clask.Clask.Route(path='/p/<gid>/add', method=clask.Method.POST)
  def AddToPaysHoffGame(self, gid, option):
    gid = uuid.UUID(gid)
    user = self.GetUser()
    if user is None:
      return 'unauthorized', 401
    try:
      game = self._payshoff.AddOption(gid, user.uid, option)
      res = flask.make_response('OK', 200)
      self.NotifyReload(gid)
      return self.SaveLogin(res, user)
    except ValueError as e:
      return str(e), 400

  @clask.Clask.Route(path='/p/<gid>/del', method=clask.Method.POST)
  def RemoveFromPaysHoffGame(self, gid, option):
    gid = uuid.UUID(gid)
    user = self.GetUser()
    if user is None:
      return 'unauthorized', 401
    try:
      game = self._payshoff.RemoveOption(gid, user.uid, int(option))
      res = flask.make_response('OK', 200)
      self.NotifyReload(gid)
      return self.SaveLogin(res, user)
    except ValueError as e:
      return str(e), 400

  @clask.Clask.Route(path='/p/<gid>/adm_skip', method=clask.Method.POST)
  def AdminSkipNextUser(self, gid):
    gid = uuid.UUID(gid)
    user = self.GetUser()
    if user is None:
      return 'unauthorized', 401
    try:
      game = self._payshoff.AdminSkipNextUser(gid, user.uid)
      res = flask.make_response('OK', 200)
      self.NotifyReload(gid)
      return self.SaveLogin(res, user)
    except ValueError as e:
      return str(e), 400

  @clask.Clask.Route(path='/p/<gid>/sel', method=clask.Method.POST)
  def FinishPaysHoffGame(self, gid):
    gid = uuid.UUID(gid)
    user = self.GetUser()
    if user is None:
      return 'unauthorized', 401
    try:
      game = self._payshoff.Select(gid, user.uid)
      res = flask.make_response('OK', 200)
      self.NotifyReload(gid)
      return self.SaveLogin(res, user)
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


def main():
  logging.getLogger('eventlet').disabled = True #(logging.ERROR)
  logging.getLogger('werkzeug').disabled = True #(logging.ERROR)
  gunicorn.GunicornHost(CreateApp(), {'bind': '0.0.0.0:5000'}).run()
