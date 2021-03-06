# -*- coding: UTF-8 -*-
from __future__ import absolute_import, division, print_function, with_statement

import re
import time
import qrcode
import os
import math
import json
from StringIO import StringIO
from tracer.models import Tracer
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.options import define, options
from tornado.web import HTTPError, RequestHandler, authenticated
from tornado.gen import coroutine
from tornado.escape import url_escape

define("user", default="admin", help="Admin username")
define("password", default="admin", help="Admin password")
define("qr_token", default="secret_key", help="")
define("qr_static_path", default="qr", help="")
define("tracer_url", default="", help="")


class BaseHandler(RequestHandler):
    """ Handler基类，提供了SqlAlchemy集成,
    基于配置项目的用户验证
    """
    def initialize(self):
        self._dbsession = self.application.dbsession_maker()

    def on_finish(self):
        self._dbsession.close()

    @property
    def dbsession(self):
        return self._dbsession

    def get_current_user(self):
        return self.get_secure_cookie("user")

    def set_current_user(self, value):
        if not value:
            self.clear_cookie("user")
        else:
            self.set_secure_cookie("user", value, expires_days=None)


class Logout(BaseHandler):
    """登出
    """
    def get(self):
        self.set_current_user(None)
        self.redirect(self.reverse_url("Login"))


class Login(BaseHandler):
    """登录
    cookies:    @username  保存的登录名
                @remember  是否保存登录名
    """
    def prepare(self):
        self._kwargs = dict(error="", remember="", username="")
        remember = self.get_cookie("remember")
        if bool(remember):
            self._kwargs["username"] = self.get_cookie("username")
            self._kwargs["remember"] = remember

    def get(self):
        if self.current_user:
            self.redirect(self.reverse_url("TracerManager", "list", 0))
        else:
            self.render("login.html", **self._kwargs)

    def post(self):
        username = self.get_argument("username")
        password = self.get_argument("password")
        remember = self.get_argument("remember", default="")
        if username == options.user and password == options.password:
            self.set_current_user(username)
            if remember:
                self.set_cookie("username", username)
                self.set_cookie("remember", remember)
            else:
                self.clear_cookie("username")
                self.clear_cookie("remember")
            self.redirect(self.reverse_url("TracerManager", "list", 0))
        else:
            self._kwargs["error"] = "用户名或密码错误"
            self.render("login.html", **self._kwargs)


class TracerManager(BaseHandler):
    """tracer管理
    @method: update|add|list|remove
    @key:
    """
    def _gen_tracer_page(self, tracer):
        """生成tracer的静态html页面
        """
        path = os.path.join(self.settings["static_path"], "tracers")
        if not os.path.exists(path):
            os.makedirs(path)
        page = os.path.join(path, "%s.%s" % (tracer.id, "html"))
        with open(page, "w") as f:
            f.write(self.render_string("tracer_show.html", tracer=tracer))

    @authenticated
    def get(self, method, key):
        if method == "add":
            self.get_add_tracer()
        elif method == "list":
            self.get_list_tracer(int(key))
        elif method == "update":
            self.get_update_tracer(str(key))
        else:
            raise HTTPError(404)

    @authenticated
    @coroutine
    def post(self, method, key):
        if method == "add":
            yield self.post_add_tracer()
        elif method == "remove":
            yield self.post_remove_tracer(str(key))
        elif method == "update":
            yield self.post_update_tracer(str(key))

    def get_add_tracer(self):
        """响应新增页面
        """
        tracer = Tracer(
            id=Tracer.gen_id(12),
            title="",
            content="",
        )
        url = options.tracer_url
        if not url:
            url = self.request.protocol + "://" + self.request.host + self.static_url("tracers")
        self.render("tracer_add.html", tracer=tracer, url=url)

    @coroutine
    def post_add_tracer(self):
        """新建一个追踪对象
        1、生成二维码 2、写入数据库 3、创建静态页面
        """
        title = self.get_body_argument("tracer_title", default="")
        content = self.get_body_argument("tracer_content", default="")
        tracer_id = self.get_body_argument("tracer_id", default=Tracer.gen_id(12))
        tracer_url = self.get_body_argument("tracer_url", default="") + \
            "/" + tracer_id + ".html"
        qr_url = ""

        client = AsyncHTTPClient()
        req = HTTPRequest(
            url="http://" + self.request.host + self.reverse_url("QRViewer") +
                "?token=" + options.qr_token,
            method="POST",
            body="key=" + tracer_id + "&value=" + tracer_url,
        )
        resp = yield client.fetch(req)
        if resp.code == 200:
            ret = json.load(StringIO(resp.body))
            print(ret)
            qr_url = ret["url"]

        tracer = Tracer(
            id=tracer_id,
            title=title,
            content=content,
            clicked=0,
            posted=int(time.time()),
            qr=qr_url,
            url=tracer_url,
        )
        self._gen_tracer_page(tracer)
        self.dbsession.merge(tracer)
        self.dbsession.commit()

        self.redirect(self.reverse_url("TracerShower", tracer_id) +
                "?next=" + url_escape(self.reverse_url("TracerManager", "list", 0)))

    def get_list_tracer(self, page=0, per=10):
        """tracer管理主列表页面
        """
        q = self.dbsession.query(Tracer)
        tracers = q.order_by(Tracer.posted.desc()).offset(page * per).limit(per).all()
        if len(tracers) == 0 and page != 0:
            self.redirect(self.reverse_url("TracerManager", "list", 0))
        c = self.dbsession.query(Tracer.id)
        page_count = int(math.ceil(float(c.count()) / per))
        self.render("tracer_list.html",
                tracers=tracers,
                page=page if page >= 0 and page < page_count else 0,
                page_count=page_count if page_count > 0 else 1)

    def get_update_tracer(self, tracer_id):
        """返回编辑页面
        """
        tracer = self.dbsession.query(Tracer).get(tracer_id)
        next_url = self.get_query_argument("next",
                default=self.reverse_url("TracerManager", "list", 0))
        if not tracer:
            raise HTTPError(404)
        self.render("tracer_update.html", tracer=tracer, next_url=next_url)

    @coroutine
    def post_update_tracer(self, tracer_id):
        """更新已有对象
        """
        tracer = self.dbsession.query(Tracer).get(tracer_id)
        if not tracer:
            raise HTTPError(404)
        tracer.title = self.get_body_argument("tracer_title", default="")
        tracer.content = self.get_body_argument("tracer_content", default="")
        self.dbsession.commit()
        next_url = self.get_query_argument("next",
                default=self.reverse_url("TracerManager", "list", 0))
        self.redirect(next_url)

    @coroutine
    def post_remove_tracer(self, tracer_id):
        """删除对象
        """
        tracer = self.dbsession.query(Tracer).get(tracer_id)
        if not tracer:
            raise HTTPError(404)
        self.dbsession.delete(tracer)
        self.dbsession.commit()
        page = self.get_body_argument("page", default=0)
        self.redirect(self.reverse_url("TracerManager", "list", page))


class TracerShower(BaseHandler):
    """扫描二维码的预览页面
    """
    def get(self, tracer_id):
        tracer = self.dbsession.query(Tracer).get(tracer_id)
        if not tracer:
            raise HTTPError(404)

        next_url = self.get_query_argument("next",
                default=self.reverse_url("TracerManager", "list", 0))
        self.render("tracer_preview.html",
                tracer_id=tracer.id,
                next_url=next_url,
                qr_url=tracer.qr,
                tracer_url=tracer.url)


class QRViewer(RequestHandler):
    """生成指定键值的二维码图片
    @api: 直接生成图片，返回json结果
    @perisist: 保存图片
    @static: 直接返回静态图片，不存在则返回404
    """

    def _make_qrimage(self, value):
        """指定参数生成一张包含value的二维码
        """
        qr = qrcode.QRCode(
            version=3,
            error_correction=qrcode.constants.ERROR_CORRECT_Q,
            box_size=3,
            border=2,
        )
        qr.add_data(value)
        qr.make(fit=True)
        return qr.make_image()

    def get(self):
        """ 返回一张包含value参数的二维码
        """
        value = self.get_query_argument("value", default="")
        if not value:
            raise HTTPError(404)
        img = self._make_qrimage(value)
        f = StringIO()
        img.save(f)
        self.set_header("Content-Type", "image/%s" % img.kind)
        self.write(f.getvalue())

    def post(self):
        """ 创建包含value参数文件名为key二维码图片
        返回图片的url地址
        """
        token = self.get_query_argument("token", default="")
        key = self.get_body_argument("key", default="")
        value = self.get_body_argument("value", default="")
        if token != options.qr_token:
            raise HTTPError(403)
        if not value or not re.match(r"^[\w\d_]+$", key):
            raise HTTPError(404)
        img = self._make_qrimage(value)
        path = os.path.join(self.settings["static_path"], options.qr_static_path)
        name = key + "." + img.kind
        if not os.path.exists(path):
            os.makedirs(path)
        img.save(os.path.join(path, name))
        self.write(dict(
            url=self.request.protocol + "://" + self.request.host +
                    self.static_url(os.path.join(options.qr_static_path, name)),
            value=value,
            expired=0,
        ))
