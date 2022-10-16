langs("Python")

py_binary (
  name = "what2pick",
  srcs = [
    "clask.py",
    "pays_hoff_dao.py",
    "sql_storage.py",
    "user_dao.py",
    "what2pick.py",
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
  main_executable = "what2pick",
  deps = [
    ":what2pick",
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