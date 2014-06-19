# -*- coding: UTF-8 -*-
import os
import tornado.web
from tornado.web import url
from tornado.options import define, options
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tracer.handlers import Login, Logout, TracerManager, TracerShower, QRViewer
from tracer.models import BaseModel

define("debug", default=False, help="Run in debug mode", type=bool)
define("db_connect_string", default="sqlite://", help="Load the givent config file")
define("db_rebuild", default=False, help="Drop all database tables", type=bool)


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            url(r"/login", Login, name="Login"),
            url(r"/logout", Logout, name="Logout"),
            url(r"/admin/tracer/(\blist|get|add|remove|update\b)/(\w+)",
                TracerManager, name="TracerManager"),
            url(r"/admin/qr", QRViewer, name="QRViewer"),
            url(r"/tracer/([0-9a-zA-Z]{8,})", TracerShower, name="TracerShower"),
        ]
        settings = dict(
            debug=options.debug,
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=False,
            cookie_secret="wxb0b2ff9c2e34505d",
            login_url="/login",
        )
        tornado.web.Application.__init__(self, handlers, **settings)
        self.engine = create_engine(options.db_connect_string, echo=options.debug)
        self.dbsession_maker = sessionmaker(bind=self.engine, autocommit=False,
                                        autoflush=False)
        if options.db_rebuild:
            BaseModel.metadata.drop_all(bind=self.engine)
        BaseModel.metadata.create_all(bind=self.engine)
