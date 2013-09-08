ijd8
====

关于ijd8
------------------

ijd8源于一个闲置的域名和一个简单的程序博客。

- 语言：python
- 框架：tornado
- 模板引擎：tenjin
- 数据库：mysql
- 编辑器：markitup for markdown
- 主题：Octopress
- 运行环境：SAE 或 BAE
- 代码高亮：pygments

安装
------------------

有两个文件夹：SAE和BAE，把目录下的文件直接复制到程序版本文件夹下即可。

### 在SAE 上安装

1. 新建一个应用，选择语言：python
2. 在SAE 后台初始化mysql，并运行 site.sql 里的内容
3. 建立一个Storage 存放附件，如upload，当然也可以用七牛保存附件，详见setting.py
4. 建立一个版本
5. 下载后打开SAE 文件夹，修改setting.py 里面的相关内容
6. 上传到SAE 即可
7. 管理路径 /admin/

### 在BAE 上安装

1. 新建一个应用，选择语言：python
2. 在建立一个mysql 数据库并记下起名字，并运行 site.sql 里的内容
3. 建立一个云存储BUCKET 存放附件，如upload，当然也可以用七牛保存附件，详见setting.py
4. 建立一个版本
5. 下载后打开BAE 文件夹，修改setting.py 里面的相关内容
6. 上传到SAE 即可
7. 管理路径 /admin/

**注意**： BAE 上当前的pygments 是v1.4 ， 而在导入formatters 时需要载入模块commands，而BAE 上没有这个模块，解决方法是把SAE 下的pygments 文件夹复制到BAE 目录下。具体参见 [http://www.ijd8.com/t/19](http://www.ijd8.com/t/19 "BAE pygments")

官方示例使用了多说作评论系统，你也可以使用其它第三方评论系统，只需打开/templates/octopress/comment.html 把代码修改为你的就行。

应该注意的小问题
------------------

当成功建立数据库、上传代码后，打开网站时会自动转到管理员界面，由于没有默认用户，要注册一个用户作管理员。若忘记了管理员和登录密码，则需要到数据后台，打开表oppy_user，删除里面的数据，再打开/admin/ 就可重新注册为管理员。

相关链接
------------------

若有好建议或遇到问题可以到官方博客或支持论坛交流。

官方DEMO [http://www.ijd8.com/](http://www.ijd8.com/ "爱简单吧")

官方支持论坛 [http://youbbs.sinaapp.com/](http://youbbs.sinaapp.com/ "youBBS")
