# -*- coding: UTF-8 -*-
import time
import tornado.web
import tornado.gen
import qrcode
import os
import math
from models import Tracer
from StringIO import StringIO
from tornado.httpclient import AsyncHTTPClient


class BaseHandler(tornado.web.RequestHandler):
    """ Handler基类，提供了SqlAlchemy集成
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


class Index(BaseHandler):
    def get(self):
        self.render("index.html")


class Logout(BaseHandler):
    """退出登录
    """
    def get(self):
        self.clear_cookie("user")
        self.redirect(self.reverse_url('login'))


class Login(BaseHandler):
    """登录处理
    """
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
                self.set_secure_cookie("remember", remember)
            else:
                self.clear_cookie("login_name")
                self.clear_cookie("remember")
            self.redirect(self.reverse_url('tracer_manager', 'list', '0'))
        else:
            self._kwargs['error'] = "用户名或密码错误"
            self.render("login.html", **self._kwargs)


class TracerManager(BaseHandler):
    """tracer管理
    @method: update|add|list|remove
    @key:
    """
    @tornado.web.authenticated
    def get(self, method, key):
        if method == 'add':
            self.get_add_tracer()
        elif method == 'list':
            self.get_list_tracer(int(key))
        elif method == 'update':
            self.get_update_tracer(str(key))
        else:
            self.send_error(404)

    @tornado.web.authenticated
    @tornado.gen.coroutine
    def post(self, method, key):
        if method == 'add':
            yield self.post_add_tracer()
        elif method == 'remove':
            yield self.post_remove_tracer(str(key))
        elif method == 'update':
            yield self.post_update_tracer(str(key))

    def get_add_tracer(self):
        obj = Tracer(
            id=Tracer.gen_id(12),
            title='',
            content='',
            status=0,
            clicked=0,
            posted=0,
            expired=0,
        )
        self.render("tracer_add.html", tracer=obj)

    @tornado.gen.coroutine
    def post_add_tracer(self):
        title = self.get_body_argument('tracer_title', default='')
        content = self.get_body_argument('tracer_content', default='')
        new_id = self.get_body_argument('tracer_id', default=Tracer.gen_id(12))
        status = self.get_body_argument('tracer_status', default=0)
        obj = Tracer(
            id=new_id,
            title=title,
            content=content,
            status=status,
            clicked=0,
            posted=int(time.time()),
            expired=0,
        )
        self.dbsession.merge(obj)
        self.dbsession.commit()
        http_client = AsyncHTTPClient()
        yield http_client.fetch('http://' + self.request.host +
                self.reverse_url('qr_viewer', new_id) + "?perisist=1&api=" + QRViewer.__api_key__)
        self.redirect(self.reverse_url('tracer_manager', 'list', 0))

    def get_list_tracer(self, page=0, per=10):
        q = self.dbsession.query(Tracer)
        tracers = q.order_by(Tracer.posted.desc()).offset(page * per).limit(per).all()
        if len(tracers) == 0 and page != 0:
            self.redirect(self.reverse_url('tracer_manager', 'list', 0))
        counter = self.dbsession.query(Tracer.id)
        page_count = int(math.ceil(float(counter.count()) / per))
        if page > page_count - 1 or page < 0:
            page = 0
        self.render("tracer_list.html",
                tracers=tracers,
                page=page,
                page_count=page_count)

    def get_update_tracer(self, tracer_id):
        tracer = self.dbsession.query(Tracer).get(tracer_id)
        if tracer is None:
            raise tornado.web.HTTPError(404)
        self.render("tracer_update.html", tracer=tracer)

    @tornado.gen.coroutine
    def post_update_tracer(self, tracer_id):
        tracer = self.dbsession.query(Tracer).get(tracer_id)
        if tracer is None:
            raise tornado.web.HTTPError(404)
        tracer.title = self.get_body_argument('tracer_title', default='')
        tracer.content = self.get_body_argument('tracer_content', default='')
        tracer.status = self.get_body_argument('tracer_status', default=0)
        self.dbsession.commit()
        self.redirect(self.reverse_url('tracer_manager', 'list', 0))

    @tornado.gen.coroutine
    def post_remove_tracer(self, tracer_id):
        t = self.dbsession.query(Tracer).get(tracer_id)
        if t is None:
            raise tornado.web.HTTPError(404)
        self.dbsession.delete(t)
        self.dbsession.commit()
        page = self.get_body_argument("page", default=0)
        self.redirect(self.reverse_url('tracer_manager', 'list', page))


class TracerShower(BaseHandler):
    """扫描二维码的展示页面
    @preview: 预览模式提供一些分辨率操作，以及可以实时的修改内容
    """
    def get(self, tracer_id):
        preview = bool(self.get_query_argument('preview', default=''))
        tracer = self.dbsession.query(Tracer).get(tracer_id)
        if tracer is None:
            raise tornado.web.HTTPError(404)
        self.render('tracer_show.html', preview=preview, tracer=tracer)

    def post(self, tracer_id):
        pass


class QRViewer(BaseHandler):
    """生成指定键值的二维码图片
    @api: 直接生成图片，返回json结果
    @perisist: 保存图片
    @static: 直接返回静态图片，不存在则返回404
    """
    __api_key__ = "43vxl8jazpNJ"
    __qr_static__ = "qr"
    __kind__ = 'png'

    def get(self, key):
        perisist = bool(self.get_query_argument("perisist", default=''))
        api = self.get_query_argument("api", default='')
        static = self.get_query_argument("static", default='')
        url = 'http://' + self.request.host + self.reverse_url('tracer', key)
        path = os.path.join(self.settings["static_path"], QRViewer.__qr_static__)
        if not os.path.exists(path):
            os.makedirs(path)

        # 直接返回静态图片
        if bool(static):
            self.redirect(self.static_url('qr/%s.%s' % (key, QRViewer.__kind__)),
                   permanent=True)
            return

        # 固定一个二维码大小和密度以适应打印到包装上
        qr = qrcode.QRCode(
            version=3,
            error_correction=qrcode.constants.ERROR_CORRECT_Q,
            box_size=3,
            border=2
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image()

        # 如果是持久化则首先检查文件是否存在
        self.set_header("Content-Type", "image/%s" % img.kind)
        if bool(perisist) and \
                (self.get_current_user() is not None or api == QRViewer.__api_key__):
            path = os.path.join(path, '%s.%s' % (key, QRViewer.__kind__))
            if not os.path.exists(path):
                img.save(path, QRViewer.__kind__)
            if bool(api):
                self.write(dict(result='OK'))
            else:
                f = open(path, 'r')
                self.write(f.read(64 * 1024))
        else:
            f = StringIO()
            img.save(f, img.kind)
            self.write(f.getvalue())
