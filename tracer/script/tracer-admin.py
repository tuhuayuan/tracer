#!/usr/bin/env python
#-*- coding: UTF-8 -*-
""" 管理的脚本
"""
from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer
from tornado.options import define, options, parse_config_file, parse_command_line
try:
    from tracer.main import Application
except ImportError:
    import os
    import sys
    pkg_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '../..'))
    sys.path.insert(0, pkg_path)
    from tracer.main import Application

define("port", default=9000, help="Run on the givent port", type=int)
define(
    "config",
    default="",
    help="Load the givent config file",
    callback=lambda path: parse_config_file(path, final=False)
)

if __name__ == "__main__":
    parse_command_line()
    HTTPServer(Application()).listen(options.port)
    IOLoop.instance().start()
