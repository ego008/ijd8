#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import os.path
import json
from time import time

import torndb
import tornado.web
import tornado.wsgi

import tenjin
from tenjin.helpers import *
#import markdown2 as markdown
import markdown

from setting import *

from common import getpw
from plugins import parse_text

class Application(tornado.wsgi.WSGIApplication):
    def __init__(self):
        handlers = [(r"/admin/", HomePage),
            (r"/admin/login", LoginPage),
            (r"/admin/logout", LogoutPage),
            (r"/admin/fileupload", UploadPage),
            (r"/admin/post", PostPage),
            (r"/admin/category", CategoryPage),
            (r"/admin/markitup/preview", PostPrevewPage)]
        settings = dict(
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
            cookie_secret="11oETzKXQAGaYdkd5gEmGehJFuYh7Ewnp2XdTP1o/Vo=",
            login_url="/admin/login",
            autoescape=None,
            debug = DEBUG)
        tornado.wsgi.WSGIApplication.__init__(self, handlers, **settings)
        # Have one global connection to the blog DB across all handlers
        self.db = torndb.Connection(host=MYSQL_HOST, database=MYSQL_DB,
            user=MYSQL_USER, password=MYSQL_PASS, max_idle_time=30)

engine = tenjin.Engine(
            path=[os.path.join('templates', theme) for theme in THEMES] + ['templates'],
            cache=tenjin.MemoryCacheStorage(),
            preprocess=True)

class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.application.db

    def get_current_user(self):
        user_id = self.get_secure_cookie("user")
        if not user_id:
            return None
        return self.db.get("SELECT * FROM oppy_user WHERE id = %s LIMIT 1", int(user_id))

    def render(self, template, context=None, globals=None, layout=False):
        if context is None:
            context = {}
        args = dict(
            handler=self,
            request=self.request,
            current_user=self.current_user,
            xsrf_form_html=self.xsrf_form_html,
            xsrf_token=self.xsrf_token,
        )

        context.update(args)
        return engine.render(template, context, globals, layout)

    def echo(self, template, context=None, globals=None, layout=False):
        self.write(self.render(template, context, globals, layout))

def upload_bcs(bucketname=BUCKET, savename="/test.txt", filedata=None):
    if bucketname and savename and filedata:
        if DEBUG:
            return None
        from bae.api import bcs
        mybcs = bcs.BaeBCS(BCSHOST, AK, SK)
        e,r = mybcs.put_object(bucketname, savename, filedata)
        if r is None:
            return "http://%s/%s%s" % (BCSHOST, bucketname, savename)
        else:
            return False
    else:
        return False

def upload_qiniu(bucketname=QN_BUCKET, savename="test.txt", filedata=None):
    if bucketname and savename and filedata:
        if DEBUG:
            return None
        import qiniu.conf
        qiniu.conf.ACCESS_KEY = QN_AK
        qiniu.conf.SECRET_KEY = QN_SK

        import qiniu.rs
        policy = qiniu.rs.PutPolicy(bucketname)
        uptoken = policy.token()

        import qiniu.io

        key = savename
        if key[0] == "/":
            key = key[1:]
        ret, err = qiniu.io.put(uptoken, key, filedata)
        if err is not None:
            return False
        return "http://%s.qiniudn.com/%s" % (bucketname, key)
    else:
        return False

class UploadPage(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.echo("upload-test.html", {"title": "file upload"})

    @tornado.web.authenticated
    def post(self):
        rspd = {'status': 201, 'msg':'ok'}
        upfile = self.request.files.get('fileupload', None)

        if upfile:
            myfile = upfile[0]

            try:
                 file_type = myfile['filename'].split('.')[-1].lower()
                 new_file_name = "%s.%s"% (str(int(time())), file_type)
            except:
                 file_type = ''
                 new_file_name = str(int(time()))

            if BUCKET:
                fileurl = upload_bcs(BUCKET, "/upload/" + str(new_file_name), myfile['body'])
            elif QN_AK and QN_SK and QN_BUCKET:
                fileurl = upload_qiniu(QN_BUCKET, "upload/" + str(new_file_name), myfile['body'])
            else:
                rspd['msg'] = 'pls define BCS BUCKET or QN_AK/QN_SK/QN_BUCKET in setting.py.'
                self.set_header('Content-Type','text/html')
                self.write(json.dumps(rspd))
                return
            if fileurl:
                #self.write("upload well done.")
                rspd['status'] = 200
                rspd['filename'] = myfile['filename']
                rspd['msg'] = fileurl
            else:
                #self.write(d)
                rspd['status'] = 500
                rspd['msg'] = '500 error, pls try it again.'
        else:
            rspd['msg'] = 'none file uploaded.'

        self.set_header('Content-Type','text/html')
        self.write(json.dumps(rspd))
        return

def set_bucket_referer():
    """
    对一个 bucket 设置防盗链，只需运行一次
    """
    acl_referer = '{"statements":[{"action":["*"],"effect":"allow","resource":["%s\\/"],"user":["*"],"referer":["http:\/\/%s\/*"]}]}' % (BUCKET, MAJOR_DOMAIN)
    from bae.api import bcs
    mybcs = bcs.BaeBCS(BCSHOST, AK, SK)
    mybcs.set_acl(BUCKET, "", acl_referer)

class HomePage(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        ## 若用BCS 存放附件可去掉下面一行注释并运行一次
        #set_bucket_referer()
        self.echo("admin_index.html", {
            "title": "Admin Home",
            "cats": self.db.query("SELECT * FROM oppy_category LIMIT 100"),
        }, layout="_layout_admin.html")

def get_tag(text):
    text = text.replace(u"，",",").replace(" ",",").replace("-",",").replace("/",",")
    tag_list = set([tag.strip() for tag in text.split(',')])
    tag_list.discard('')
    return ','.join(tag_list)

class PostPage(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        id = self.get_argument("id", None)
        select_cid = self.get_argument("fcid", 1)
        obj = {"cid":int(select_cid), "title":"", "markdown":"", "tags":""}
        label = "Add"
        if id:
            obj = self.db.get("SELECT * FROM oppy_post WHERE id=%s LIMIT 1", int(id))
            if not obj:
                self.redirect("/admin/post")
                return
            label = "Edit"

        self.echo("admin_post.html", {
            "title": "Articles",
            "obj": obj,
            "label": label,
            "cats": self.db.query("SELECT * FROM oppy_category LIMIT 100"),
            "tags": self.db.query("SELECT name FROM oppy_tag ORDER BY num DESC LIMIT 100"),
        }, layout="_layout_admin.html")

    @tornado.web.authenticated
    def post(self):
        fid = self.get_argument("fid", None)
        if fid:
            self.redirect("/admin/post?id=" + fid)
            return

        cid = int(self.get_argument("cid", 1))
        title = self.get_argument("title", None)
        if title is None:
            self.redirect("/admin/")
            return
        content = self.get_argument("markdown")
        tags = get_tag(self.get_argument("tags",""))
        id = int(self.get_argument("id"))

        self.set_header('Content-Type','application/json')
        rspd = {'status': 201, 'msg':'ok'}

        if id>0:
            #edit
            entry = self.db.get("SELECT * FROM oppy_post WHERE id = %s", int(id))
            if not entry: raise tornado.web.HTTPError(404)
            old_cid = int(entry["cid"])
            old_tags = entry["tags"]
            if cid==old_cid and title==entry["title"] and content==entry["markdown"] and tags==old_tags:
                self.write(json.dumps({'status': 200, 'msg':'文章没做任何改动'}))
                return
            if content!=entry["markdown"]:
                html = markdown.markdown(parse_text(content))
                self.db.execute("UPDATE oppy_post SET cid = %s, title = %s, markdown = %s, html = %s, tags = %s WHERE id = %s", cid, title, content, html, tags, int(id))
            else:
                self.db.execute("UPDATE oppy_post SET cid = %s, title = %s, tags = %s WHERE id = %s", cid, title, tags, int(id))
            #cid changed
            if old_cid != cid:
                self.db.execute("UPDATE oppy_category SET num = num + 1 WHERE id = %s LIMIT 1", cid)
                self.db.execute("UPDATE oppy_category SET num = num - 1 WHERE id = %s LIMIT 1", old_cid)
            #tags changed
            if old_tags != tags:
                old_tags_set = set(old_tags.split(',')) #.encode("utf-8")
                new_tags_set = set(tags.split(','))

                removed_tags = old_tags_set - new_tags_set
                added_tags = new_tags_set - old_tags_set

                if removed_tags:
                    for tag in removed_tags:
                        tag_obj = self.db.get("SELECT * FROM oppy_tag WHERE name = %s LIMIT 1", tag)
                        if tag_obj:
                            id_list = tag_obj["content"].split(",")
                            if str(id) in id_list:
                                id_list.remove(str(id))
                                num = len(id_list)
                                self.db.execute("UPDATE oppy_tag SET num = %s, content = %s WHERE id = %s LIMIT 1", num, ",".join(id_list), tag_obj["id"])

                if added_tags:
                    for tag in added_tags:
                        tag_obj = self.db.get("SELECT * FROM oppy_tag WHERE name = %s LIMIT 1", tag)
                        if tag_obj:
                            if tag_obj["content"]:
                                id_list = tag_obj["content"].split(",")
                                if str(id) not in id_list:
                                    id_list.insert(0, str(id))
                                    num = len(id_list)
                                    self.db.execute("UPDATE oppy_tag SET num = %s, content = %s WHERE id = %s LIMIT 1", num, ",".join(id_list), tag_obj["id"])
                            else:
                                num = 1
                                content = str(id)
                                self.db.execute("UPDATE oppy_tag SET num = %s, content = %s WHERE id = %s LIMIT 1", num, ",".join(id_list), tag_obj["id"])
                        else:
                            self.db.execute("INSERT INTO oppy_tag (name,num,content) VALUES (%s,%s,%s)",tag, 1, str(id))

            rspd['status'] = 200
            rspd['msg'] = u'完成： 你已经成功编辑了一篇文章 <a href="/t/%d" target="_blank">查看编辑后的文章</a>' % id
        else:
            #add
            html = markdown.markdown(parse_text(content))
            query = "INSERT INTO oppy_post (cid,title,markdown,html,tags,add_time) VALUES (%s,%s,%s,%s,%s,%s)"
            new_post_id = self.db.execute(query, cid, title, content, html, tags, int(time()))
            #category count
            self.db.execute("UPDATE oppy_category SET num = num + 1 WHERE id = %s LIMIT 1", cid)
            #add post id to tag
            for tag in tags.split(","):
                tag_obj = self.db.get("SELECT * FROM oppy_tag WHERE name = %s LIMIT 1", tag)
                if tag_obj:
                    if tag_obj["content"]:
                        id_list = tag_obj["content"].split(",")
                        if str(new_post_id) not in id_list:
                            id_list.insert(0, str(new_post_id))
                            num = len(id_list)
                            self.db.execute("UPDATE oppy_tag SET num = %s, content = %s WHERE id = %s LIMIT 1", num, ",".join(id_list), tag_obj["id"])
                    else:
                        num = 1
                        content = str(new_post_id)
                        self.db.execute("UPDATE oppy_tag SET num = %s, content = %s WHERE id = %s LIMIT 1", num, ",".join(id_list), tag_obj["id"])
                else:
                    self.db.execute("INSERT INTO oppy_tag (name,num,content) VALUES (%s,%s,%s)",tag, 1, str(new_post_id))

            rspd['status'] = 200
            rspd['msg'] = u'完成： 你已经成功添加了一篇文章 <a href="/t/%d" target="_blank">查看</a>' % new_post_id

        self.write(json.dumps(rspd))


class CategoryPage(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        id = self.get_argument("id", None)
        obj = {"name":""}
        label = "Add"
        if id:
            obj = self.db.get("SELECT * FROM oppy_category WHERE id=%s LIMIT 1", int(id))
            if not obj:
                self.redirect("/admin/category")
                return
            label = "Edit"

        self.echo("category_admin.html", {
            "title": "Category",
            "obj": obj,
            "label": label,
            "cats": self.db.query("SELECT * FROM oppy_category LIMIT 100"),
        }, layout="_layout_admin.html")

    @tornado.web.authenticated
    def post(self):
        act = self.get_argument("act") #find/add/edit
        id = self.get_argument("id", None)
        fid = self.get_argument("fid", None)
        if act=="find" and fid:
            self.redirect("/admin/category?id=" + fid)
            return
        name = self.get_argument("name", None)
        obj = None
        if id:
            obj = self.db.get("SELECT * FROM oppy_category WHERE id=%s LIMIT 1", int(id))

        if obj:
            self.db.execute("UPDATE oppy_category SET name = %s WHERE id = %s", name, int(id))
        else:
            self.db.execute("INSERT INTO oppy_category (id,name,num) VALUES (null,%s,0)",name)
        self.redirect("/admin/category")

class PostPrevewPage(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.write("This is a preview page.")

    @tornado.web.authenticated
    def post(self):
        data = self.get_argument("data", "no post data")
        if data:
            data = markdown.markdown(parse_text(data))
        self.echo("blog_preview.html", {"title":"Post preview", "data": data})

class LoginPage(BaseHandler):
    def get(self):
        has_user = self.db.get("SELECT id FROM oppy_user LIMIT 1")
        if has_user:
            label = "Login"
        else:
            label = "Sigin"
        self.echo("admin_login.html", {"title":label, "has_user": has_user, "label": label}, layout="_layout_admin.html")

    def post(self):
        name = self.get_argument("name")
        pw = self.get_argument("pw")

        if name and pw:
            #check has user
            has_user = self.db.get("SELECT id FROM oppy_user LIMIT 1")
            pw2 = getpw(pw)
            if has_user:
                #check user
                obj = self.db.get("SELECT * FROM oppy_user WHERE name = %s LIMIT 1", name)
                if obj:
                    if obj["password"] == pw2:
                        self.set_secure_cookie("user", str(obj["id"]))
                        self.redirect(self.get_argument("next", "/admin/"))
                        return
                    else:
                        self.write("pw wrong")
                else:
                    self.write("no obj")
            else:
                #add new user
                newuserid = self.db.execute("INSERT INTO oppy_user (id,flag,name,password) values(null,5,%s,%s)", name, pw2)
                if newuserid:
                    self.set_secure_cookie("user", str(newuserid))
                    self.redirect("/admin/")
                    return
                else:
                    self.write("db error.")
        else:
            self.write("name and pw are required.")

class LogoutPage(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        self.redirect(self.get_argument("next", "/"))

application = Application()

