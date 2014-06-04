# -*- coding: UTF-8 -*-
import os
import tornado.web
import tornado.httpserver
import tornado.ioloop
import models
from tornado.web import url
from tornado.options import define, options, parse_config_file
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from handlers import Index, Login, Logout, TracerManager, TracerShower

define("port", default=9000, help="run on the givent port", type=int)
define("debug", default=False, help="run in debug mode", type=bool)
define(
    "config",
    default="",
    help="load the givent config file",
    callback=lambda path: parse_config_file(path, final=False)
)
define("db_connect_string", default="sqlite://:memory", help="load the givent config file")
define("db_rebuild", default=False, help="drop all database table", type=bool)


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", Index),
            url(r"/login", Login, name='login'),
            url(r"/logout", Logout, name='logout'),
            url(r"/admin/tracer/(\blist|get|add|remove\b)/(\w+)", TracerManager, name='tracer_manager'),
            url(r"/tracer/([0-9a-zA-Z]{8,})", TracerShower, name='tracer'),
        ]
        settings = dict(
            debug=options.debug,
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
            cookie_secret="wxb0b2ff9c2e34505d",
            login_url="/login",
            admin_user = "admin",
            admin_password = "admin_mt1696",
        )
        tornado.web.Application.__init__(self, handlers, **settings)
        self.engine = create_engine(options.db_connect_string, echo=options.debug)
        self.dbsession_maker = sessionmaker(bind=self.engine, autocommit=False,
                                        autoflush=False)
        if options.db_rebuild:
            models.BaseModel.metadata.drop_all(bind=self.engine)
        models.BaseModel.metadata.create_all(bind=self.engine)


def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
