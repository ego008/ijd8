# -*- coding: utf-8 -*-

import sae.const

DEBUG = False
SITE_TITLE = u"博客标题"
SITE_SUB_TITLE = u"博客副标题"
SITE_KEYWORDS = u"博客关键字"
SITE_DECRIPTION = u"博客描述"

AUTHOR_NAME = u"博客作者" #显示在RSS订阅里面
#CONACT_MAIL = "xxx@gmail.com" #暂未用到

THEMES = ['octopress','admin']

LINK_BROLL = [
        {'text': u"爱简单吧", 'url': "http://www.ijd8.com", 'title': u"ijd8官方博客"},
        {'text': u"YouBBS", 'url': "http://youbbs.sinaapp.com", 'title': u"ijd8支持论坛"},
    ]

MAJOR_DOMAIN = 'www.yourdomain.com' #主域名

##Mysql 数据库信息
MYSQL_DB = sae.const.MYSQL_DB
MYSQL_USER = sae.const.MYSQL_USER
MYSQL_PASS = sae.const.MYSQL_PASS
MYSQL_HOST = "%s:%s" % (sae.const.MYSQL_HOST_S, sae.const.MYSQL_PORT)
MYSQL_HOST_M = "%s:%s" % (sae.const.MYSQL_HOST, sae.const.MYSQL_PORT)

JQUERY = "http://lib.sinaapp.com/js/jquery/1.9.1/jquery-1.9.1.min.js"

LANGUAGE = 'zh-CN'

EACH_PAGE_POST_NUM = 10 #每页显示文章数
RECENT_POST_NUM = 10 #边栏显示最近文章数
RELATED_NUM = 10 #显示相关文章数
SIDER_TAG_NUM = 100 #边栏显示标签数
SIDER_CAT_NUM = 100 #边栏显示分类数
SHORTEN_CONTENT_WORDS = 150 #文章列表截取的字符数
DESCRIPTION_CUT_WORDS = 100 #meta description 显示的字符数
FEED_NUM = 10 #订阅输出文章数

#######下面是保存附件的空间，可选SAE Storage  和 七牛（有免费配额），只选一个
## 1) 用SAE Storage 需要在SAE 控制面板开通
BUCKET = "" #Domain Name, 如 upload 。不用或用七牛请留空

## 2) 七牛 注册可获永久10G空间和每月10G流量，注册地址 http://t.cn/z8h5lsg
QN_AK = "" #七牛 ACCESS_KEY
QN_SK = "" #七牛 SECRET_KEY
QN_BUCKET = "" #空间名称 , 如 upload
