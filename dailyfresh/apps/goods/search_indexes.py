#!usr/bin/env python
# -*- coding:utf-8 -*-
# 定义索引类, 此文件名为固定的


import datetime
from haystack import indexes
from apps.goods.models import GoodsSKU


class GoodsSKUIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    # author = indexes.CharField(model_attr='user')
    # pub_date = indexes.DateTimeField(model_attr='pub_date')

    def get_model(self):
        return GoodsSKU

    # 建立索引数据
    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.all()  # filter(pub_date__lte=datetime.datetime.now())
