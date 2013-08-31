#! /usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os.path
import re
from urllib import unquote

import torndb
import tornado.web
import tornado.wsgi

import tenjin
from tenjin.helpers import *

from setting import *

from common import detail_date,detail_date_tzd,getpw,quoted_string,get_post_mdy

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
        ]
        settings = dict(
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            autoescape=None,
            debug = DEBUG
        )
        tornado.wsgi.WSGIApplication.__init__(self, handlers, **settings)

        # Have one global connection to the blog DB across all handlers
        self.db = torndb.Connection(
            host=MYSQL_HOST, database=MYSQL_DB,
            user=MYSQL_USER, password=MYSQL_PASS, max_idle_time=30)

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

    def render(self, template, context=None, globals=None, layout=False):
        if context is None:
            context = {}
        args = dict(
            handler=self,
            request=self.request,
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

            if qt != title:
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
            self.db.execute("UPDATE oppy_post SET views = views + 1 WHERE id = %s LIMIT 1", int(id))
        else:
            raise tornado.web.HTTPError(404)

class CategoryPage(BaseHandler):
    def get(self, id, name):
        cobj = self.db.get("SELECT id,name,num FROM oppy_category WHERE id = %s", int(id))
        if cobj:
            qt = quoted_string(cobj["name"])
            if qt != name:
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


application = Application()

