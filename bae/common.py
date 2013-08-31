# -*- coding: utf-8 -*-

from hashlib import md5
from urllib import unquote, quote
from datetime import datetime

###### def
def getpw(pw):
    md5a = md5(pw.encode('utf-8')).hexdigest()[7:24]
    return md5(md5a).hexdigest()[4:20]

def unquoted_unicode(string, coding='utf-8'):
    return unquote(string).decode(coding)

def quoted_string(unicode, coding='utf-8'):
    return quote(unicode.encode(coding)).replace("%20", "-")

def format_date(dt):
    return dt.strftime('%a, %d %b %Y %H:%M:%S GMT')

def timestamp_to_datetime(timestamp):
    return datetime.fromtimestamp(timestamp)

def format_date2(timestamp):
    #2011-12-12 23:26:41
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def detail_date(timestamp):
    #Jul 23, 2011
    return datetime.fromtimestamp(timestamp).strftime('%b %dth, %Y')

def detail_date_tzd(timestamp):
    #YYYY-MM-DDThh:mm:ssTZD
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%dT%H:%M:%STZD')

def get_post_mdy(timestamp):
    dt = datetime.fromtimestamp(timestamp)
    return (dt.strftime("%b"), dt.day, dt.year)
