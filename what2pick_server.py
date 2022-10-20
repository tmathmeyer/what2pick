
import datetime
import flask
import jinja2
import threading

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
    return self._users.LoginAsUser(username, password)

  def PersistLogin(self, res, user):
    expire_date = datetime.datetime.now() + datetime.timedelta(days=90)
    res.set_cookie("uid", value=user.uid, expires=expire_date)
    res.set_cookie("pwd", value=user.pwd, expires=expire_date)
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
    username = flask.request.cookies.get('uid')
    password = flask.request.cookies.get('pwd')
    user = self._users.ChangeUsername(username, password, data['name'][:16])
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
    user = self.GetUser()
    if not user:
      return 'Open In Browser, fb webview is broken', 200
    game, trigger_update = self._payshoff.JoinGame(gid, user.uid)
    if game.gameid != gid:
      res = flask.make_response('OK', 302)
      res.headers['Location'] = f'/p/{game.gameid}'
      return self.PersistLogin(res, user)
    am_current = (game.nextuser == user.uid) and (not game.decided)
    am_admin = game.admin == user.uid and (not game.decided)
    can_remove = (am_current and (user.name not in game.must_add)) or am_admin
    can_select = am_current and (not game.must_add) and len(game.options) == 1
    current_player = self._users.GetUsernameByUUID(game.nextuser)
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
    user = self.GetUser()
    try:
      game = self._payshoff.RemoveOption(gid, user.uid, int(data['option']))
      res = flask.make_response('OK', 200)
      self.NotifyReload(gid)
      return self.PersistLogin(res, user)
    except ValueError as e:
      return str(e), 400

  @clask.Clask.Route(path='/p/<gid>/sel', method=clask.Method.POST)
  def FinishPaysHoffGame(self, gid, data):
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
    game = self._payshoff.GetGameById(gid)
    if not game:
      return 'no game', 404
    self.Wait(gid)
    return 'reload', 200
    

def main():
  content = f'{resources.Resources.Dir()}/what2pick/frontend'
  app = flask.Flask(__name__, static_folder=content, template_folder=content)
  Application.Launch(app, 'storage.db')
  print(app.url_map)
  app.run(host='0.0.0.0', port=5000)
