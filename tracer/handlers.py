# -*- coding: UTF-8 -*-
import time
import logging
import tornado.web
from models import Tracer


class BaseHandler(tornado.web.RequestHandler):
    def initialize(self):
        self._dbsession = self.application.dbsession_maker()

    def on_finish(self):
        self._dbsession.close()

    @property
    def dbsession(self):
        return self._dbsession

    def get_current_user(self):
        return self.get_secure_cookie("user")


class Index(BaseHandler):
    def get(self):
        self.render("index.html")


class Logout(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        self.redirect(self.reverse_url('login'))


class Login(BaseHandler):
    def prepare(self):
        self._kwargs = dict(error="", remember="", login_name="")
        remember = self.get_secure_cookie("remember")
        if remember == 'yes':
            self._kwargs['login_name'] = self.get_secure_cookie("login_name")
            self._kwargs['remember'] = remember

    def get(self):
        if self.get_current_user() is not None:
            self.redirect(self.reverse_url('tracer_manager', 'list', '0'))
        else:
            self.render("login.html", **self._kwargs)

    def post(self):
        username = self.get_argument('username')
        password = self.get_argument('password')
        remember = self.get_argument('remember', default='')
        if username == self.settings.get('admin_user') and \
            password == self.settings.get('admin_password'):
            self.set_secure_cookie("user", username)
            if remember == 'yes':
                self.set_secure_cookie("login_name", username)
                self.set_secure_cookie("remember", 'yes')
            else:
                self.clear_cookie("login_name")
                self.clear_cookie("remember")
            self.redirect(self.reverse_url('tracer_manager', 'list', '0'))
        else:
            self._kwargs['error'] = "用户名或密码错误"
            self.render("login.html", **self._kwargs)


class TracerManager(BaseHandler):
    @tornado.web.authenticated
    def get(self, method, key):
        if method == 'add':
            self.render("tracer_add.html")
        elif method == 'list':
            self.render("tracer_list.html")


class TracerShower(BaseHandler):
    def get(self):
        pass
