langs("Python")
load("//rules/env/Docker/build_defs.py")

py_binary (
  name = "what2pick_server",
  srcs = [
    "pays_hoff_dao.py",
    "names.py",
    "sql_storage.py",
    "user_dao.py",
    "what2pick_server.py",
  ],
  deps = [
    "//impulse/util:bintools",
    "//pylib:typecheck",
    "//pylib/web:api_tools",
    "//pylib/web:launchers",
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
      "'gunicorn @ git+https://github.com/benoitc/gunicorn.git'",
      "eventlet",
      "requests",
    ],
    "alpine_packages": [
      "git",
    ],
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