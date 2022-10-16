
import flask
import jinja2

from impulse.util import resources

from what2pick import clask
from what2pick import user_dao
from what2pick import pays_hoff_dao


class Application(clask.Clask):
  def __init__(self, db_file:str):
    self._users = user_dao.UserDAO(db_file)
    self._payshoff = pays_hoff_dao.PaysHoffDAO(db_file)

  def GetUser(self):
    username = flask.request.cookies.get('uid')
    password = flask.request.cookies.get('pwd')
    return self._users.LoginAsUser(username, password)

  def PersistLogin(self, res, user):
    res.set_cookie("uid", value=user.uid)
    res.set_cookie("pwd", value=user.pwd)
    return res

  @clask.Clask.Route(path='/')
  def Index(self):
    user = self.GetUser()
    res = flask.make_response(flask.render_template(
      'what2pick/index.html',
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
    game = self._payshoff.CreateGame(user)
    if game:
      res = flask.make_response('OK', 302)
      res.headers['Location'] = f'/p/{game.gameid}'
      return self.PersistLogin(res, user)
    else:
      return 'Fatal Error. Contact admin', 500

  @clask.Clask.Route(path='/p/<gid>')
  def GetGameDetail(self, gid):
    user = self.GetUser()
    game = self._payshoff.JoinGame(gid, user.uid)
    res = flask.make_response(str(game))
    return self.PersistLogin(res, user)





def main():
  app = flask.Flask(__name__, template_folder=resources.Resources.Dir())
  Application.Launch(app, 'database.sqlite')
  print(app.url_map)
  app.run()