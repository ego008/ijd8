#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import os.path
import re
import json
from urllib import unquote
from time import time

import torndb
import tornado.web
import tornado.wsgi

import tenjin
from tenjin.helpers import *

import markdown2 as markdown

from setting import *

from common import detail_date, detail_date_tzd, getpw, quoted_string,\
        get_post_mdy, getpw, unquoted_unicode
from plugins import parse_text

class Application(tornado.wsgi.WSGIApplication):
    def __init__(self):
        handlers = [
            (r"/", HomePage),
            (r"/t/(\d+)", GotoTopicPage),
            (r"/topic/(\d+)/(.*)", TopicPage),
            (r"/category/(\d+)/(.*)", CategoryPage),
            (r"/tag/(.+)", TagPage),
            (r"/atom\.xml", AtomPage),
            (r"/sitemap\.xml", Sitemap),
            (r"/admin/", AdminHomePage),
            (r"/admin/login", AdminLoginPage),
            (r"/admin/logout", AdminLogoutPage),
            (r"/admin/fileupload", AdminUploadPage),
            (r"/admin/post", AdminPostPage),
            (r"/admin/category", AdminCategoryPage),
            (r"/admin/markitup/preview", AdminPostPrevewPage),
        ]
        settings = dict(
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
            cookie_secret=COOKIE_SECRET,
            login_url="/admin/login",
            autoescape=None,
            debug = True
        )
        tornado.wsgi.WSGIApplication.__init__(self, handlers, **settings)

        # Have one global connection to the blog DB across all handlers
        # 从数据库
        self.db = torndb.Connection(
            host=MYSQL_HOST, database=MYSQL_DB,
            user=MYSQL_USER, password=MYSQL_PASS, max_idle_time=10)

        # 主数据库
        self.dbm = torndb.Connection(
            host=MYSQL_HOST_M, database=MYSQL_DB,
            user=MYSQL_USER, password=MYSQL_PASS, max_idle_time=10)

engine = tenjin.Engine(path=[os.path.join('templates', theme) for theme in THEMES] + ['templates'], cache=tenjin.MemoryCacheStorage(), preprocess=True)

###def
_re_html=re.compile('<.*?>|\&.*?\;', re.UNICODE|re.I|re.M|re.S)
def textilize(s):
    return _re_html.sub("", s).strip()

def get_part(html):
    if "<!--more-->" in html:
        return html.split("<!--more-->")[0]
    else:
        return textilize(html)[:SHORTEN_CONTENT_WORDS]

def get_des(html):
    return textilize(html)[:DESCRIPTION_CUT_WORDS]



class BaseHandler(tornado.web.RequestHandler):

    @property
    def db(self):
        return self.application.db

    @property
    def dbm(self):
        return self.application.dbm

    def get_current_user(self):
        user_id = self.get_secure_cookie("user")
        if not user_id: return None
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


class HomePage(BaseHandler):
    def get(self):
        page = int(self.get_argument("page", 1))
        table_status = self.db.query("SHOW TABLE STATUS LIKE 'oppy_post'")[0]
        max_id = table_status["Auto_increment"] - 1
        if max_id == 0:
            self.redirect("/admin/")
            return
        total_page = max_id/EACH_PAGE_POST_NUM
        if max_id%EACH_PAGE_POST_NUM:
            total_page += 1
        if page > total_page:
            page = total_page
            self.redirect("/?page=%d" % page)
            return
        elif page < 1:
            page = 1
            self.redirect("/?page=%d" % page)
            return
        from_id = max_id - EACH_PAGE_POST_NUM*(page-1) + 1
        self.echo("blog_index.html", {
            "title": "%s - %s" % (SITE_TITLE, SITE_SUB_TITLE),
            "description": SITE_DECRIPTION,
            "keywords": SITE_KEYWORDS,
            "objs": self.db.query("SELECT id,title,html,add_time FROM oppy_post WHERE id < %d ORDER BY id DESC LIMIT %d" % (from_id, EACH_PAGE_POST_NUM) ),
            "page": page,
            "total_page": total_page,
            "cats": self.db.query("SELECT id,name,num FROM oppy_category LIMIT %d" % SIDER_CAT_NUM),
            "tags": self.db.query("SELECT name,num FROM oppy_tag ORDER BY num DESC LIMIT %d" % SIDER_TAG_NUM),
            })



class GotoTopicPage(BaseHandler):
    def get(self, id):
        obj = self.db.get("SELECT title FROM oppy_post WHERE id = %s", int(id))
        if obj:
            self.redirect("/topic/%d/%s" % (int(id), quoted_string(obj["title"])), 301)
        else:
            raise tornado.web.HTTPError(404)

class TopicPage(BaseHandler):
    def get(self, id, title):
        obj = self.db.get("SELECT p.id,p.cid,p.views,p.title,p.html,p.tags,p.add_time,c.name as cname FROM oppy_post p LEFT JOIN oppy_category c ON p.cid=c.id WHERE p.id = %s", int(id))
        if obj:
            qt = quoted_string(obj["title"])

            if obj["title"].replace(" ", "-") != title:
                self.redirect("/topic/%d/%s" % (int(id), qt))
                return
            #nearly article
            table_status = self.db.query("SHOW TABLE STATUS LIKE 'oppy_post'")[0]
            max_id = table_status["Auto_increment"] - 1
            new_id = int(id) + 1
            old_id = int(id) - 1
            new_obj = old_obj = None
            if new_id <= max_id:
                new_obj = self.db.get("SELECT id,title FROM oppy_post WHERE id = %s", new_id)
            if old_id > 0:
                old_obj = self.db.get("SELECT id,title FROM oppy_post WHERE id = %s", old_id)

            #Related articles, base similar tag
            related_posts = None
            if RELATED_NUM > 0 and obj["tags"]:
                id_dic = {}
                for tag in obj["tags"].split(","):
                    tag_obj = self.db.get("SELECT num,content FROM oppy_tag WHERE name = %s LIMIT 1", tag)
                    if tag_obj and tag_obj["num"]>1:
                        id_list = tag_obj["content"].split(",")
                        id_list.remove(str(id))
                        for tid in id_list:
                            try:
                                id_dic[tid] += 1
                            except:
                                id_dic[tid] = 1
                ## sort
                if id_dic:
                    id_tuple = sorted(id_dic.items(), key=lambda id_dic:id_dic[1], reverse=True)[:RELATED_NUM]
                    id_list = [int(x[0]) for x in id_tuple]
                    if len(id_list) == 1:
                        related_posts = self.db.query("SELECT id,title FROM oppy_post WHERE id = %s", int(id_list[0]))
                    else:
                        related_posts = self.db.query("SELECT id,title FROM oppy_post WHERE id in(%s)" % ",".join([str(x) for x in id_list]))

            self.echo("blog_detail.html", {
                "title": "%s - %s" % (obj["title"], SITE_TITLE),
                "description": "%s - %s" % (obj["cname"], get_des(obj["html"])),
                "keywords": obj["tags"],
                "qt": qt,
                "obj": obj,
                "new_obj": new_obj,
                "old_obj": old_obj,
                "related_posts": related_posts,
                "recent_posts": self.db.query("SELECT id,title FROM oppy_post ORDER BY id DESC LIMIT %d" % RECENT_POST_NUM ),
                "cats": self.db.query("SELECT id,name,num FROM oppy_category LIMIT %d" % SIDER_CAT_NUM),
                "tags": self.db.query("SELECT name,num FROM oppy_tag ORDER BY num DESC LIMIT %d" % SIDER_TAG_NUM),
                })
            self.dbm.execute("UPDATE oppy_post SET views = views + 1 WHERE id = %s LIMIT 1", int(id))
        else:
            raise tornado.web.HTTPError(404)

class CategoryPage(BaseHandler):
    def get(self, id, name):
        cobj = self.db.get("SELECT id,name,num FROM oppy_category WHERE id = %s", int(id))
        if cobj:
            qt = quoted_string(cobj["name"])
            if cobj["name"] != name:
                self.redirect("/category/%d/%s" % (int(id), qt))
                return

            if cobj["num"] == 0:
                self.write("该分类下还没文章")
                return

            page = int(self.get_argument("page", 1))
            total_page = cobj["num"]/EACH_PAGE_POST_NUM
            if cobj["num"]%EACH_PAGE_POST_NUM:
                total_page += 1
            if page > total_page:
                page = total_page
                self.redirect("/category/%d/%s?page=%d" % (int(id), qt, page))
                return
            elif page < 1:
                page = 1
                self.redirect("/category/%d/%s?page=%d" % (int(id), qt, page))
                return
            offset = EACH_PAGE_POST_NUM * (page-1)
            self.echo("category_index.html", {
                "title": "Category:%s - %s" % (cobj["name"], SITE_TITLE),
                "qt": qt,
                "cobj": cobj,
                "page": page,
                "total_page": total_page,
                "objs": self.db.query("SELECT id,title,add_time FROM oppy_post WHERE cid = %d ORDER BY id DESC LIMIT %d,%d" % (int(id), offset, EACH_PAGE_POST_NUM) ),
                "recent_posts": self.db.query("SELECT id,title FROM oppy_post ORDER BY id DESC LIMIT %d" % RECENT_POST_NUM ),
                "cats": self.db.query("SELECT id,name,num FROM oppy_category LIMIT %d" % SIDER_CAT_NUM),
                "tags": self.db.query("SELECT name,num FROM oppy_tag ORDER BY num DESC LIMIT %d" % SIDER_TAG_NUM),
                })
        else:
            raise tornado.web.HTTPError(404)

class TagPage(BaseHandler):
    def get(self, name):
        name = unquote(name.encode('utf-8')).decode('utf-8')
        tobj = self.db.get("SELECT id,name,num,content FROM oppy_tag WHERE name = %s", name)
        if tobj:
            qt = quoted_string(tobj["name"])

            if tobj["num"] < 1:
                self.write("该标签下还没有文章")
                return
            page = int(self.get_argument("page", 1))
            total_page = tobj["num"]/EACH_PAGE_POST_NUM
            if tobj["num"]%EACH_PAGE_POST_NUM:
                total_page += 1
            if page > total_page:
                page = total_page
                self.redirect("/tag/%s?page=%d" % (qt, page))
                return
            elif page < 1:
                page = 1
                self.redirect("/tag/%s?page=%d" % (qt, page))
                return
            from_i = EACH_PAGE_POST_NUM * (page-1)
            id_list = tobj["content"].split(",")[from_i:(from_i + EACH_PAGE_POST_NUM)]
            self.echo("tag_index.html", {
                "title": "Tag:%s - %s" % (tobj["name"], SITE_TITLE),
                "qt": qt,
                "tobj": tobj,
                "page": page,
                "total_page": total_page,
                "objs": self.db.query("SELECT id,title,add_time FROM oppy_post WHERE id in(%s) ORDER BY id DESC" % ",".join(id_list) ),
                "recent_posts": self.db.query("SELECT id,title FROM oppy_post ORDER BY id DESC LIMIT %d" % RECENT_POST_NUM ),
                "cats": self.db.query("SELECT id,name,num FROM oppy_category LIMIT %d" % SIDER_CAT_NUM),
                "tags": self.db.query("SELECT name,num FROM oppy_tag ORDER BY num DESC LIMIT %d" % SIDER_TAG_NUM),
                })
        else:
            raise tornado.web.HTTPError(404)

class AtomPage(BaseHandler):
    def get(self):
        posts = self.db.query("SELECT id,title,html,add_time FROM oppy_post ORDER BY id DESC LIMIT %d" % FEED_NUM )
        self.set_header('Content-Type','application/atom+xml')
        self.echo("index.xml", {"posts":posts})

class Sitemap(BaseHandler):
    def get(self):
        table_status = self.db.query("SHOW TABLE STATUS LIKE 'oppy_post'")[0]
        from_id = table_status["Auto_increment"] - 1
        to_id = from_id - 40000
        if to_id<0:
            to_id = 0

        urlstr = """<url><loc>%s</loc></url>\n """
        urllist = []
        urllist.append('<?xml version="1.0" encoding="UTF-8"?>\n')
        urllist.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')

        for i in xrange(from_id, to_id,-1):
            urllist.append(urlstr%("http://%s/t/%d" % (MAJOR_DOMAIN, i)))

        urllist.append('</urlset>')

        self.set_header('Content-Type','text/xml')
        self.write(''.join(urllist))

######### damin #####

def upload_storage(bucketname=BUCKET, savename="test.txt", filedata=None):
    if bucketname and savename and filedata:
        if DEBUG:
            return None
        from sae.storage import Bucket
        bucket = Bucket(bucketname)
        if savename[0]=="/":
            savename = savename[1:]
        bucket.put_object(savename, filedata)
        return bucket.generate_url(savename)
    else:
        return False

def upload_qiniu(bucketname=QN_BUCKET, savename="test.txt", filedata=None):
    if bucketname and savename and filedata:
        if DEBUG:
            return None
        import qiniu.conf
        qiniu.conf.ACCESS_KEY = QN_AK
        qiniu.conf.SECRET_KEY = QN_SK

        bucket_name = QN_BUCKET

        import qiniu.rs
        policy = qiniu.rs.PutPolicy(bucket_name)
        uptoken = policy.token()

        import qiniu.io

        key = savename
        if key[0] == "/":
            key = key[1:]
        ret, err = qiniu.io.put(uptoken, key, filedata)
        if err is not None:
            return False
        return "http://%s.qiniudn.com/%s" % (bucket_name, key)
    else:
        return False

class AdminUploadPage(BaseHandler):
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
                fileurl = upload_storage(BUCKET, str(new_file_name), myfile['body'])
            elif QN_AK and QN_SK and QN_BUCKET:
                fileurl = upload_qiniu(QN_BUCKET, str(new_file_name), myfile['body'])
            else:
                rspd['msg'] = 'pls define SAE Storage BUCKET or QN_AK/QN_SK/QN_BUCKET in setting.py.'
                self.set_header('Content-Type','text/html')
                self.write(json.dumps(rspd))
                return
            if fileurl:
                #self.write("upload well done.")
                rspd['status'] = 200
                rspd['filename'] = myfile['filename']
                rspd['msg'] = fileurl
            else:
                rspd['status'] = 500
                rspd['msg'] = '500 error, pls try it again.'
        else:
            rspd['msg'] = 'none file uploaded.'

        self.set_header('Content-Type','text/html')
        self.write(json.dumps(rspd))
        return

class AdminHomePage(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.echo("admin_index.html", {
            "title": "Admin Home",
            "cats": self.dbm.query("SELECT * FROM oppy_category LIMIT 100"),
        }, layout="_layout_admin.html")

def get_tag(text):
    text = text.replace(u"，",",").replace(" ",",").replace("-",",").replace("/",",")
    tag_list = set([tag.strip() for tag in text.split(',')])
    tag_list.discard('')
    return ','.join(tag_list)

class AdminPostPage(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        id = self.get_argument("id", None)
        select_cid = self.get_argument("fcid", 1)
        obj = {"cid":int(select_cid), "title":"", "markdown":"", "tags":""}
        label = "Add"
        if id:
            obj = self.dbm.get("SELECT * FROM oppy_post WHERE id=%s LIMIT 1", int(id))
            if not obj:
                self.redirect("/admin/post")
                return
            label = "Edit"

        self.echo("admin_post.html", {
            "title": "Articles",
            "obj": obj,
            "label": label,
            "cats": self.dbm.query("SELECT * FROM oppy_category LIMIT 100"),
            "tags": self.dbm.query("SELECT name FROM oppy_tag ORDER BY num DESC LIMIT 100"),
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
            entry = self.dbm.get("SELECT * FROM oppy_post WHERE id = %s", int(id))
            if not entry: raise tornado.web.HTTPError(404)
            old_cid = int(entry["cid"])
            old_tags = entry["tags"]
            if cid==old_cid and title==entry["title"] and content==entry["markdown"] and tags==old_tags:
                self.write(json.dumps({'status': 200, 'msg':'文章没做任何改动'}))
                return
            if content!=entry["markdown"]:
                html = markdown.markdown(parse_text(content))
                self.dbm.execute("UPDATE oppy_post SET cid = %s, title = %s, markdown = %s, html = %s, tags = %s WHERE id = %s", cid, title, content, html, tags, int(id))
            else:
                self.dbm.execute("UPDATE oppy_post SET cid = %s, title = %s, tags = %s WHERE id = %s", cid, title, tags, int(id))
            #cid changed
            if old_cid != cid:
                self.dbm.execute("UPDATE oppy_category SET num = num + 1 WHERE id = %s LIMIT 1", cid)
                self.dbm.execute("UPDATE oppy_category SET num = num - 1 WHERE id = %s LIMIT 1", old_cid)
            #tags changed
            if old_tags != tags:
                old_tags_set = set(old_tags.split(',')) #.encode("utf-8")
                new_tags_set = set(tags.split(','))

                removed_tags = old_tags_set - new_tags_set
                added_tags = new_tags_set - old_tags_set

                if removed_tags:
                    for tag in removed_tags:
                        tag_obj = self.dbm.get("SELECT * FROM oppy_tag WHERE name = %s LIMIT 1", tag)
                        if tag_obj:
                            id_list = tag_obj["content"].split(",")
                            if str(id) in id_list:
                                id_list.remove(str(id))
                                num = len(id_list)
                                self.dbm.execute("UPDATE oppy_tag SET num = %s, content = %s WHERE id = %s LIMIT 1", num, ",".join(id_list), tag_obj["id"])

                if added_tags:
                    for tag in added_tags:
                        tag_obj = self.dbm.get("SELECT * FROM oppy_tag WHERE name = %s LIMIT 1", tag)
                        if tag_obj:
                            if tag_obj["content"]:
                                id_list = tag_obj["content"].split(",")
                                if str(id) not in id_list:
                                    id_list.insert(0, str(id))
                                    num = len(id_list)
                                    self.dbm.execute("UPDATE oppy_tag SET num = %s, content = %s WHERE id = %s LIMIT 1", num, ",".join(id_list), tag_obj["id"])
                            else:
                                num = 1
                                content = str(id)
                                self.dbm.execute("UPDATE oppy_tag SET num = %s, content = %s WHERE id = %s LIMIT 1", num, ",".join(id_list), tag_obj["id"])
                        else:
                            self.dbm.execute("INSERT INTO oppy_tag (name,num,content) VALUES (%s,%s,%s)",tag, 1, str(id))

            rspd['status'] = 200
            rspd['msg'] = u'完成： 你已经成功编辑了一篇文章 <a href="/t/%d" target="_blank">查看编辑后的文章</a>' % id
        else:
            #add
            html = markdown.markdown(parse_text(content))
            query = "INSERT INTO oppy_post (cid,title,markdown,html,tags,add_time) VALUES (%s,%s,%s,%s,%s,%s)"
            new_post_id = self.dbm.execute(query, cid, title, content, html, tags, int(time()))
            #category count
            self.dbm.execute("UPDATE oppy_category SET num = num + 1 WHERE id = %s LIMIT 1", cid)
            #add post id to tag
            for tag in tags.split(","):
                tag_obj = self.dbm.get("SELECT * FROM oppy_tag WHERE name = %s LIMIT 1", tag)
                if tag_obj:
                    if tag_obj["content"]:
                        id_list = tag_obj["content"].split(",")
                        if str(new_post_id) not in id_list:
                            id_list.insert(0, str(new_post_id))
                            num = len(id_list)
                            self.dbm.execute("UPDATE oppy_tag SET num = %s, content = %s WHERE id = %s LIMIT 1", num, ",".join(id_list), tag_obj["id"])
                    else:
                        num = 1
                        content = str(new_post_id)
                        self.dbm.execute("UPDATE oppy_tag SET num = %s, content = %s WHERE id = %s LIMIT 1", num, ",".join(id_list), tag_obj["id"])
                else:
                    self.dbm.execute("INSERT INTO oppy_tag (name,num,content) VALUES (%s,%s,%s)",tag, 1, str(new_post_id))

            rspd['status'] = 200
            rspd['msg'] = u'完成： 你已经成功添加了一篇文章 <a href="/t/%d" target="_blank">查看</a>' % new_post_id

        self.write(json.dumps(rspd))


class AdminCategoryPage(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        id = self.get_argument("id", None)
        obj = {"name":""}
        label = "Add"
        if id:
            obj = self.dbm.get("SELECT * FROM oppy_category WHERE id=%s LIMIT 1", int(id))
            if not obj:
                self.redirect("/admin/category")
                return
            label = "Edit"

        self.echo("category_admin.html", {
            "title": "Category",
            "obj": obj,
            "label": label,
            "cats": self.dbm.query("SELECT * FROM oppy_category LIMIT 100"),
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
            obj = self.dbm.get("SELECT * FROM oppy_category WHERE id=%s LIMIT 1", int(id))

        if obj:
            self.dbm.execute("UPDATE oppy_category SET name = %s WHERE id = %s", name, int(id))
        else:
            self.dbm.execute("INSERT INTO oppy_category (id,name,num) VALUES (null,%s,0)",name)
        self.redirect("/admin/category")

class AdminPostPrevewPage(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.write("This is a preview page.")

    @tornado.web.authenticated
    def post(self):
        data = self.get_argument("data", "no post data")
        if data:
            data = markdown.markdown(parse_text(data))
        self.echo("blog_preview.html", {"title":"Post preview", "data": data})

class AdminLoginPage(BaseHandler):
    def get(self):
        has_user = self.dbm.get("SELECT id FROM oppy_user LIMIT 1")
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
            has_user = self.dbm.get("SELECT id FROM oppy_user LIMIT 1")
            pw2 = getpw(pw)
            if has_user:
                #check user
                obj = self.dbm.get("SELECT * FROM oppy_user WHERE name = %s LIMIT 1", name)
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
                newuserid = self.dbm.execute("INSERT INTO oppy_user (id,flag,name,password) values(null,5,%s,%s)", name, pw2)
                if newuserid:
                    self.set_secure_cookie("user", str(newuserid))
                    self.redirect("/admin/")
                    return
                else:
                    self.write("db error.")
        else:
            self.write("name and pw are required.")

class AdminLogoutPage(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        self.redirect(self.get_argument("next", "/"))


application = Application()
