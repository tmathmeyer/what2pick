langs("Python")
load("//rules/env/Docker/build_defs.py")

py_binary (
  name = "what2pick_server",
  srcs = [
    "clask.py",
    "pays_hoff_dao.py",
    "sql_storage.py",
    "user_dao.py",
    "what2pick_server.py",
  ],
  deps = [
    "//impulse/util:bintools",
  ],
  data = [
    "frontend/common.css",
    "frontend/index.css",
    "frontend/index.html",
    "frontend/payshoff.css",
    "frontend/payshoff.html",
    "frontend/payshoff.js",
    "frontend/username_edit.js",
  ],
)

container (
  name = "what2pick_service",
  main_executable = "what2pick_server",
  deps = [
    ":what2pick_server",
  ],
  binaries = [],
  docker_args = {
    "pip_packages": [ "Flask", "sqlite3" ],
    "alpine_packages": [],
    "environment": [],
    "ports": [ 5000 ],
    "args": ["hostname=what2pick.com"],
  }
)