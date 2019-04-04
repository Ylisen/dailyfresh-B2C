# -*-coding:utf-8-*-
from django.conf.urls import url
# from apps.user import views
from django.contrib.auth.decorators import login_required
from apps.user.views import RegisterView, ActiveView, LoginView, LogoutView, UserInfoView, UserOrderView, AddressView

app_name = 'apps.user'
urlpatterns = [
    # url(r'^register', views.register, name='register'),   # 注册页面
    # url(r'register_handle', views.register_handle, name='register_handle')  # 注册处理

    url(r'^register/$', RegisterView.as_view(), name='register'),  # 注册页面
    url(r'^active/(?P<token>.*)$', ActiveView.as_view(), name='active'),  # 用户激活
    url(r'^login/$', LoginView.as_view(), name='login'),  # 登录
    url(r'^logout/$', LogoutView.as_view(), name='logout'),  # 退出登录

    # 在url配置的时候，调用login_required装饰器，相当于配置的函数是login_required的返回值
    # url(r'^$', login_required(UserInfoView.as_view()), name='user'),  # 用户中心-信息页
    # url(r'^order/$', login_required(UserOrderView.as_view()), name='order'),  # 用户中心-订单页
    # url(r'^address/$', login_required(AddressView.as_view()), name='address'),  # 用户中心-地址页

    url(r'^$', UserInfoView.as_view(), name='user'),  # 用户中心-信息页
    url(r'^order/(?P<page>\d+)$', UserOrderView.as_view(), name='order'),  # 用户中心-订单页
    url(r'^address/$', AddressView.as_view(), name='address'),  # 用户中心-地址页

]
