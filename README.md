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

相关链接
------------------

若有好建议或遇到问题可以到官方博客或支持论坛交流。

官方DEMO [http://www.ijd8.com/](http://www.ijd8.com/ "爱简单吧")

官方支持论坛 [http://youbbs.sinaapp.com/](http://youbbs.sinaapp.com/ "youBBS")
