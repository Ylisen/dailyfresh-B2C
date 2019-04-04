# -*-coding:utf-8-*-
from django.conf.urls import url
from apps.cart.views import CartAddview, CartInfoView, CartUpdateView, CartDeleteView

app_name = 'apps.cart'
urlpatterns = [
    url(r'^add&', CartAddview.as_view(), name='add'),  # 购物车页面
    url(r'^$', CartInfoView.as_view(), name='cart'),  # 显示购物车页
    url(r'^update$', CartUpdateView.as_view(), name='update'),  # 购物车数据更新
    url(r'^delete$', CartDeleteView.as_view(), name='delete'),  # 删除购物车中的商品记录
]
