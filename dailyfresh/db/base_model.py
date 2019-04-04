#!usr/bin/env python
# -*- coding:utf-8 -*-

"""
@author:lisen
@file:base_model.py
@time:2019/02/27
"""
from django.db import models


class BaseModel(models.Model):
    """模型抽象基类"""
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记')

    class Meta:
        abstract = True  # 说明是一个抽象模型类
