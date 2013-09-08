# -*- coding: utf-8 -*-

from bae.core import const

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

### 从const 获取BCS 信息
BCSHOST = const.BCS_ADDR
AK = const.ACCESS_KEY
SK = const.SECRET_KEY

##配置Mysql 数据库信息，只需设置 MYSQL_DB
MYSQL_DB = "your_db_name_in_bae_mysql" #在BAE 管理面板找到你的数据库名
MYSQL_USER = const.MYSQL_USER
MYSQL_PASS = const.MYSQL_PASS
MYSQL_HOST = "%s:%s" % (const.MYSQL_HOST, const.MYSQL_PORT)
JQUERY = "http://libs.baidu.com/jquery/1.9.1/jquery.min.js"

COOKIE_SECRET = "11oETzKXQAGaYdkd5gEmGehJFuYh7Ewnp2XdTP1o/Vo="

LANGUAGE = 'zh-CN'

EACH_PAGE_POST_NUM = 10 #每页显示文章数
RECENT_POST_NUM = 10 #边栏显示最近文章数
RELATED_NUM = 10 #显示相关文章数
SIDER_TAG_NUM = 100 #边栏显示标签数
SIDER_CAT_NUM = 100 #边栏显示分类数
SHORTEN_CONTENT_WORDS = 150 #文章列表截取的字符数
DESCRIPTION_CUT_WORDS = 100 #meta description 显示的字符数
FEED_NUM = 10 #订阅输出文章数


#######下面是保存附件的空间，可选BCS 和 七牛 （都有免费配额），只选一个
## 1) BAE BCS
BUCKET = "" #your bcs bucket nam，, 如 upload 。不用或用七牛请留空

## 2) 七牛 注册可获永久10G空间和每月10G流量，注册地址 http://t.cn/z8h5lsg
QN_AK = "" #七牛 ACCESS_KEY
QN_SK = "" #七牛 SECRET_KEY
QN_BUCKET = "" #空间名称，如 upload
