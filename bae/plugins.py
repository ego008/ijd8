# -*- coding: utf-8 -*-

import re
from pygments import highlight
from pygments import lexers
from pygments.formatters import HtmlFormatter

###### def
def pygmentize(code_raw, language):
    lexer = lexers.get_lexer_by_name(language, encoding='utf-8', startinline=True)
    return highlight(code_raw, lexer, HtmlFormatter(encoding="utf-8",startinline=True))

def tableize_code (text, lang = ""):
    string = text.strip()
    table = ['<div class="highlight"><table><tr><td class="gutter"><pre class="line-numbers">']
    code = []
    index = 0
    for line in string.split("\n"):
        table.append("<span class='line-number'>%d</span>\n" % (index+1))
        code.append("<span class='line'>%s</span>" % line)
        index += 1
    table.append("</pre></td><td class='code'><pre><code class='%s'>%s</code></pre></td></tr></table></div>" % (lang, "\n".join(code)))
    return "".join(table)

def strip_hl_div(text):
    __HL_RE = re.compile('<div class="highlight"><pre>(.+?)</pre></div>', re.UNICODE|re.I|re.M|re.S)
    m = __HL_RE.match(text)
    if m:
        return text.replace(m.group(0), m.group(1))
    return text


####### code block #####
def code_block(text):
    """
    Syntax
    {% codeblock [title] [lang:language] [url] [link text] %}
    code snippet
    {% endcodeblock %}
    """
    __CODE_BLOCK_RE = re.compile(r"""\s({% codeblock ([^%\[\]]*)%}(.+?){% endcodeblock %})""",re.I|re.M|re.S)
    __CaptionUrlTitle = re.compile('(\S[\S\s]*)\s+(https?:\/\/\S+|\/\S+)\s*(.+)?', re.UNICODE|re.I|re.M|re.S)
    __Caption = re.compile('(\S[\S\s]*)', re.UNICODE|re.I|re.M|re.S)
    __Lang = re.compile('\s*lang:(\S+)', re.UNICODE|re.I|re.M|re.S)

    codes = __CODE_BLOCK_RE.findall(text)
    for code in codes:
        caption = ""
        filetype = ""
        fileurl = ""
        code_block_str = code[0]
        code_info = code[1]
        code_raw = code[2]
        if code_info:
            m = __Lang.search(code_info)
            if m:
                filetype = m.group(1)
                code_info = __Lang.sub("", code_info)
            m = __CaptionUrlTitle.match(code_info)
            if m:
                filename = m.group(1)
                caption = "<figcaption><span>%s</span><a href='%s' target='_blank' rel='nofollow'>%s</a></figcaption>\n" % (m.group(1), m.group(2), m.group(3))
            else:
                m2 = __Caption.match(code_info)
                if m2:
                    filename = m2.group(1)
                    caption = "<figcaption><span>%s</span></figcaption>\n" % m2.group(1)
                else:
                    filename = ""
                    caption = ""
            if not filetype and filename:
                m = re.search(r"\S[\S\s]*\w+\.(\w+)", filename)
                if m:
                    filetype = m.group(1)

        #
        source = ["<figure class='code'>"]
        if caption:
            source.append(caption)
        if filetype:
            try:
                hltext = pygmentize(code_raw, filetype)
                tmp_text = tableize_code (strip_hl_div(hltext), filetype)
            except:
                tmp_text = tableize_code (code_raw.replace('<','&lt;').replace('>','&gt;'))
        else:
            tmp_text = tableize_code (code_raw.replace('<','&lt;').replace('>','&gt;'))
        source.append(tmp_text)
        source.append("</figure>")
        #print "\n".join(source)
        text = text.replace(code_block_str, "\n".join(source))

    return text

### Backtick Code Blocks ###
def backtick_code_block(text):
    """
    Syntax
    ``` [language] [title] [url] [link text]
    code snippet
    ```
    """
    __CODE_BLOCK_RE = re.compile(r"""\s(^`{3} *([^\n]+)?\n(.+?)\n`{3})""",re.I|re.M|re.S)
    __AllOptions = re.compile('([^\s]+)\s+(.+?)\s+(https?:\/\/\S+|\/\S+)\s*(.+)?', re.UNICODE|re.I|re.M|re.S)
    __LangCaption = re.compile('([^\s]+)\s*(.+)?', re.UNICODE|re.I|re.M|re.S)
    codes = __CODE_BLOCK_RE.findall(text)
    for code in codes:
        options = ""
        caption = ""
        lang = ""
        fileurl = ""
        code_block_str = code[0]
        code_info = code[1]
        code_raw = code[2]
        if code_info:
            m = __AllOptions.match(code_info)
            if m:
                lang = m.group(1)
                caption = "<figcaption><span>%s</span><a href='%s' target='_blank' rel='nofollow'>%s</a></figcaption>" % (m.group(2), m.group(3), m.group(4))
            else:
                m2 = __LangCaption.match(code_info)
                if m2:
                    lang = m2.group(1)
                    caption = "<figcaption><span>%s</span></figcaption>" % m2.group(2)
        if re.match('\A( {4}|\t)', code_raw):
            code_raw = re.sub('^( {4}|\t)', '', code_raw)

        #
        source = ["<figure class='code'>"]
        if caption:
            source.append(caption)

        if not lang or lang == 'plain':
            tmp_text = tableize_code (code_raw.replace('<','&lt;').replace('>','&gt;'))
        else:
            try:
                hltext = pygmentize(code_raw, lang)
                tmp_text = tableize_code (strip_hl_div(hltext), lang)
            except:
                tmp_text = tableize_code (code_raw.replace('<','&lt;').replace('>','&gt;'))

        source.append(tmp_text)
        source.append("</figure>")
        text = text.replace(code_block_str, "\n".join(source))
    return text

### VideoTag ###
def videotag(text):
    """
    Syntax
    {% video url/to/video [width height] [url/to/poster] %}
    """
    __VIDEOTAG_RE = re.compile(r"""\s({% video (https?:\S+)(\s+(https?:\S+))?(\s+(https?:\S+))?(\s+(\d+)\s(\d+))?(\s+(https?:\S+))? %})""",re.I|re.M|re.S)
    codes = __VIDEOTAG_RE.findall(text)
    vtype = {
      'mp4': "type='video/mp4; codecs=\"avc1.42E01E, mp4a.40.2\"'",
      'ogv': "type='video/ogg; codecs=theora, vorbis'",
      'webm': "type='video/webm; codecs=vp8, vorbis'"
    }

    for code in codes:
        video = code[1]
        width = int(code[7])
        height = int(code[8])
        poster = code[10]

        if video and width > 0 and height > 0:
            video_code = []
            video_code.append("<video width='%d' height='%d' preload='none' controls poster='%s'>" % (width, height, poster))
            t = video.split(".")[-1]
            video_code.append("<source src='%s' %s>" % (video, vtype[t]))
            video_code.append("</video>")
            text = text.replace(code[0], "".join(video_code))

    return text

###########
def parse_text(text):
    text = videotag(text)
    text = code_block(text)
    text = backtick_code_block(text)
    return text
