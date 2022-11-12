langs("Python")
load("//rules/env/Docker/build_defs.py")

py_binary (
  name = "what2pick_server",
  srcs = [
    "clask.py",
    "pays_hoff_dao.py",
    "names.py",
    "sql_storage.py",
    "user_dao.py",
    "what2pick_server.py",
  ],
  deps = [
    "//impulse/util:bintools",
    "//impulse/util:typecheck",
  ],
  data = [
    "frontend/common.css",
    "frontend/index.css",
    "frontend/index.html",
    "frontend/payshoff.css",
    "frontend/payshoff.html",
    "frontend/payshoff.js",
    "frontend/username_edit.js",
    "names.txt",
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
    "pip_packages": [
      "Flask",
      "gunicorn==20.1.0",
      "eventlet==0.30.2",
    ],
    "alpine_packages": [],
    "environment": [],
    "ports": [ 5000 ],
    "args": ["hostname=what2pick.com"],
  }
)

py_test (
  name = "sql_storage_tests",
  srcs = [
    "sql_storage_tests.py",
    "sql_storage.py",
  ],
)