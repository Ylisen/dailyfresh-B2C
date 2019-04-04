# -*-coding:utf-8-*-
from django.conf.urls import url
from apps.goods.views import IndexView, DetailView, ListView

app_name = 'apps.goods'
urlpatterns = [
    url(r'^index/$', IndexView.as_view(), name='index'),  # 商品页作为首页
    url(r'^goods/(?P<goods_id>\d+)$', DetailView.as_view(), name='detail'),  # 详情页
    url(r'^list/(?P<type_id>\d+)/(?P<page>\d+)$', ListView.as_view(), name='list'),  # 列表页
]

