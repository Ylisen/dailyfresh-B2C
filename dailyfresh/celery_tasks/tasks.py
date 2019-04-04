#!usr/bin/env python
# -*- coding:utf-8 -*-
from django.core.mail import send_mail
from django.conf import settings
from django.template import loader, RequestContext
from celery import Celery
import time

# django环境的初始化，在任务处理者worker一端加以下几句
import os
# import django
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dailyfresh.settings')
# django.setup()

from apps.goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner


# 创建一个Celery类的实例对象
app = Celery('celery_tasks.tasks', broker='redis://192.168.229.130:6379/8')


# 定义任务函数
@app.task
def send_register_active_email(to_email, username, token):
    """发送激活邮件"""
    # 组织邮件信息
    subject = '天天生鲜欢迎信息'
    message = ''
    sender = settings.EMAIL_PROM  # 发送人
    receiver = [to_email]
    html_message = '<h1>%s, 欢迎您成为天天生鲜注册会员</h1>请点击下面链接激活您的账户<br/><a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a>' % (username, token, token)

    send_mail(subject, message, sender, receiver, html_message=html_message)
    # time.sleep(5)


@app.task
def generate_static_index_html():
    """产生首页静态页面"""
    # 查询商品的种类信息
    types = GoodsType.objects.all()
    # 获取首页轮播的商品的信息
    index_banner = IndexGoodsBanner.objects.all().order_by('index')
    # 获取首页促销的活动信息
    promotion_banner = IndexPromotionBanner.objects.all().order_by('index')

    # 获取首页分类商品信息展示
    for type in types:
        # 查询首页显示的type类型的文字商品信息
        title_banner = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')
        # 查询首页显示的图片商品信息
        image_banner = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
        # 动态给type对象添加两个属性保存数据
        type.title_banner = title_banner
        type.image_banner = image_banner

    # 组织模板上下文
    context = {
        'types': types,
        'index_banner': index_banner,
        'promotion_banner': promotion_banner,
    }

    # 使用模板
    # 1. 加载模板文件，返回模板对象
    temp = loader.get_template('static_index.html')
    # 2. 定义模板上下文
    # context = RequestContext(request, context) # 可省
    # 3. 模板渲染
    static_index_html = temp.render(context)

    # 生成首页对应静态文件
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    with open(save_path, 'w') as f:
        f.write(static_index_html)

