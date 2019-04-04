from django.shortcuts import render, redirect
from django.urls import reverse
from django.db import transaction
from django.conf import settings
from django.views.generic import View
from apps.goods.models import GoodsSKU
from apps.user.models import Address
from apps.order.models import OrderInfo, OrderGoods

from django.http import JsonResponse

from django_redis import get_redis_connection
from utils.mixin import LoginRequiredMixin
from datetime import datetime
from alipay import AliPay
import os


# /order/pay
class OrderPlaceView(LoginRequiredMixin, View):
    """提交订单页面"""
    def post(self, request):
        # 获取参数，一键多值 接受到的是列表
        sku_ids = request.POST.getlist('sku_ids')
        # 进行参数校验
        if not all(sku_ids) or len(sku_ids) < 1:
            # 没有商品id，重定向到购物车页面进行选择
            return redirect(reverse('cart:cart'))
        # 获取登录的用户信息,构建cart_key
        user = request.user
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        skus = []
        # 初始化总的数量和总价
        total_count = 0
        total_price = 0
        # 查询对应的商品信息
        for sku_id in sku_ids:
            sku = GoodsSKU.objects.get(id=sku_id)

            # 查询商品在购物车中的数量
            count = conn.hget(cart_key, sku_id)
            count = int(count)
            # 计算每种商品的小计,redis 中的值是字符串类型，需要转化类型
            amount = sku.price * count
            # 动态的给sku对象添加数量和小计
            sku.count = count
            sku.amount = amount
            # 计算总的数量和总价
            total_count += count
            total_price += amount
            # 最后将sku对象添加到列表中
            skus.append(sku)

        # for sku in skus:
        #     print(sku, type(sku))
        #     print(sku.name, sku.price, sku.count, sku.amount)

        # 运费：运费子系统
        transit_price = 10
        # 实付款
        total_pay = total_price + transit_price

        # 获取用户的全部地址
        addrs = Address.objects.filter(user=user)

        # 将sku_id 以逗号间隔拼接成字符串
        sku_ids = ','.join(sku_ids)

        # 构建context上下文
        context = {'addrs': addrs,
                   'total_count': total_count,
                   'total_price': total_price,
                   'transit_price': transit_price,
                   'total_pay': total_pay,
                   'skus': skus,
                   'sku_ids': sku_ids}

        return render(request, 'df_order/place_order.html', context)


# 前端传递的参数: 地址id(addr_id) 支付方式(pay_method) 用户要购买的商品id字符串(sku_ids)
# mysql事务: 一组sql操作，要么都成功，要么都失败
# 高并发: 秒杀
# 支付: 支付宝支付
# /order/commit
class OrderCommitView1(View):
    # 加悲观锁: 总是假设最坏的情况，每次去拿数据的时候都认为别人会修改，所以每次在拿数据的时候都会上锁，这样别人想拿这个数据就会阻塞直到它拿到锁
    """订单创建"""
    @transaction.atomic
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收参数
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')

        # 校验参数
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 1, 'errmsg': '参数不完整'})

        # 校验支付方式
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 2, 'errmsg': '非法支付方式'})

        # 校验地址
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '非法地址'})

        # todo: 创建订单核心业务
        order_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id)
        # 订单总金额和总数量
        total_count = 0
        total_price = 0
        # 运费
        transit_price = 10

        # 设置事务保存点
        save_id = transaction.savepoint()

        try:
            # todo: 保存订单信息表: 向df_order_info表中添加一条记录
            order = OrderInfo.objects.create(order_id=order_id,
                                             user=user,
                                             addr=addr,
                                             pay_method=pay_method,
                                             total_count=total_count,
                                             total_price=total_price,
                                             transit_price=transit_price,
            )

            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id

            # 获取商品
            sku_ids = sku_ids.split(',')
            print('获取订单商品：', sku_ids)
            for sku_id in sku_ids:
                # 根据id获取商品的信息

                try:
                    sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                    # select_for_update() 相当获得了锁, sql: select * from df_goods_sku where id=sku_id for update;
                except GoodsSKU.DoesNotExist:
                    # 商品信息出错，事务进行回滚
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res': 4, 'errmsg': '商品信息错误'})

                print('user:%d  stock:%d' % (user.id, sku.stock))
                # import time
                # time.sleep(10)

                # 获取用户要购买的商品的数目
                count = conn.hget(cart_key, sku_id)

                # 判断商品的库存
                if int(count) > sku.stock:
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res': 6, 'errmsg': '商品库存不足'})

                # todo: 向订单商品表中添加信息
                OrderGoods.objects.create(order=order,
                                          sku=sku,
                                          count=count,
                                          price=sku.price
                )

                # 修改商品表中的数据
                sku.stock -= int(count)
                sku.sales += int(count)
                sku.save()

                # 将每个商品的数量和小计进行累加得到总的金额和件数
                total_price += sku.price * int(count)
                total_count += int(count)

            # 更新订单表中的总金额和总件数
            order.total_count = total_count
            order.total_price = total_price
            order.save()

        except Exception as e:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 7, 'errmsg': '下单失败'})

        # 提交事务
        transaction.savepoint_commit(save_id)

        # 订单的相关信息写入完成之后,删除购物车中的记录信息
        conn.hdel(cart_key, *sku_ids)  # sku_ids 列表需要拆包
        # 返回应答
        return JsonResponse({'res': 5, 'message': '订单创建成功'})


class OrderCommitView(View):
    # 加乐观锁: 总是假设最好的情况，每次去拿数据的时候都认为别人不会修改，所以不会上锁，但是在更新的时候会判断一下在此期间别人有没有去更新这个数据
    """订单创建"""
    @transaction.atomic
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收参数
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')

        # 校验参数
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 1, 'errmsg': '参数不完整'})

        # 校验支付方式
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 2, 'errmsg': '非法支付方式'})

        # 校验地址
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '非法地址'})

        # todo: 创建订单核心业务
        order_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id)
        # 订单总金额和总数量
        total_count = 0
        total_price = 0
        # 运费
        transit_price = 10

        # 设置事务保存点
        save_id = transaction.savepoint()

        try:
            # todo: 保存订单信息表: 向df_order_info表中添加一条记录
            order = OrderInfo.objects.create(order_id=order_id,
                                             user=user,
                                             addr=addr,
                                             pay_method=pay_method,
                                             total_count=total_count,
                                             total_price=total_price,
                                             transit_price=transit_price,
            )

            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id

            # 获取商品
            sku_ids = sku_ids.split(',')

            for sku_id in sku_ids:
                for i in range(3):  # 尝试3次
                    # 根据id获取商品的信息
                    try:
                        sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                        # select_for_update() 相当获得了锁, sql: select * from df_goods_sku where id=sku_id for update;
                    except GoodsSKU.DoesNotExist:
                        # 商品信息出错，事务进行回滚
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 4, 'errmsg': '商品信息错误'})

                    # 获取用户要购买的商品的数目
                    count = conn.hget(cart_key, sku_id)

                    # 判断商品的库存
                    if int(count) > sku.stock:
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 6, 'errmsg': '商品库存不足'})

                    # 修改商品表中的数据(更新库存和销量)
                    orgin_stock = sku.stock
                    new_stock = orgin_stock - int(count)
                    new_sales = sku.sales + int(count)

                    # print('user:%d  time:%d stock:%d' % (user.id, i, sku.stock))
                    # import time
                    # time.sleep(10)

                    # todo:
                    # update df_goods_sku set stock=new_stock, sales=new_sales
                    # where id=sku_id and stock = orgin_stock
                    # 返回受影响的行数res, 0为失败
                    res = GoodsSKU.objects.filter(id=sku_id, stock=orgin_stock).update(stock=new_stock,
                                                                                       sales=new_sales)  # 乐观锁
                    if res == 0:  # 返回0表示更新失败
                        if i == 2:  # 尝试到第三次
                            transaction.savepoint_rollback(save_id)
                            return JsonResponse({'res': 8, 'errmsg': '下单失败2'})
                        continue

                    # todo: 向订单商品表中添加信息
                    OrderGoods.objects.create(order=order,
                                              sku=sku,
                                              count=count,
                                              price=sku.price
                    )

                    # 将每个商品的数量和小计进行累加得到总的金额和件数
                    total_price += sku.price * int(count)
                    total_count += int(count)

                    # 下单成功，跳出循环
                    break

            # 更新订单表中的总金额和总件数
            order.total_count = total_count
            order.total_price = total_price
            order.save()

        except Exception as e:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 7, 'errmsg': '下单失败'})

        # 提交事务
        transaction.savepoint_commit(save_id)

        # 订单的相关信息写入完成之后,删除购物车中的记录信息
        conn.hdel(cart_key, *sku_ids)  # sku_ids 列表需要拆包
        # 返回应答
        return JsonResponse({'res': 5, 'message': '订单创建成功'})


# 请求方式: ajax post
# 前端请求的参数: 订单id(order_id)
# order/pay
class OrderPayView(View):
    """订单支付"""
    def post(self, request):

        # 用户是否登录
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收参数
        order_id = request.POST.get('order_id')

        # 校验参数
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的订单'})

        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单错误'})

        # 业务处理：使用python sdk调用支付宝的支付接口
        # alipay初始化
        app_private_key_string = open("apps/order/app_private_key.pem").read()
        alipay_public_key_string = open("apps/order/alipay_public_key.pem").read()

        # app_private_key_string == """
        #     -----BEGIN RSA PRIVATE KEY-----
        #     base64 encoded content
        #     -----END RSA PRIVATE KEY-----
        # """
        #
        # alipay_public_key_string == """
        #     -----BEGIN PUBLIC KEY-----
        #     base64 encoded content
        #     -----END PUBLIC KEY-----
        # """

        # app_private_key_string = os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')
        # alipay_public_key_string = os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem')

        alipay = AliPay(
            appid="2016092700608687",  # 应用id
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=alipay_public_key_string,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False, 此处沙箱模拟True
        )

        # 调用支付接口
        # 电脑网站支付，需要跳转到https://openapi.alipaydev.com/gateway.do? + order_string
        total_pay = order.total_price + order.transit_price
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,  # 订单id
            total_amount=str(total_pay),  # 支付总金额
            subject='天天生鲜%s 用户' % order_id,
            return_url=None,
            notify_url=None  # 可选, 不填则使用默认notify url
        )

        # 返回应答
        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_string

        return JsonResponse({'res': 3, 'pay_url': pay_url})


# 请求方式: ajax post
# 前端请求的参数: 订单id(order_id)
# order/check
class CheckPayView(View):
    """查看订单支付结果"""
    def post(self, request):

        # 用户是否登录
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收参数
        order_id = request.POST.get('order_id')

        # 校验参数
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的订单'})

        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单错误'})

        # 业务处理：使用python sdk调用支付宝的支付接口
        # alipay初始化
        app_private_key_string = open("apps/order/app_private_key.pem").read()
        alipay_public_key_string = open("apps/order/alipay_public_key.pem").read()

        # app_private_key_string == """
        #     -----BEGIN RSA PRIVATE KEY-----
        #     base64 encoded content
        #     -----END RSA PRIVATE KEY-----
        # """
        #
        # alipay_public_key_string == """
        #     -----BEGIN PUBLIC KEY-----
        #     base64 encoded content
        #     -----END PUBLIC KEY-----
        # """

        # app_private_key_string = os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')
        # alipay_public_key_string = os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem')

        alipay = AliPay(
            appid="2016092700608687",  # 应用id
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=alipay_public_key_string,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False, 此处沙箱模拟True
        )

        # 调用支付宝的交易查询接口
        while True:
            response = alipay.api_alipay_trade_query(order_id)

            # response = {
            # "trade_no": "2017032121001004070200176844",  # 支付宝交易号
            # "code": "10000",  # 接口调用成功
            # "invoice_amount": "20.00",
            # "open_id": "20880072506750308812798160715407",
            # "fund_bill_list": [
            #     {
            #         "amount": "20.00",
            #         "fund_channel": "ALIPAYACCOUNT"
            #     }
            # ],
            # "buyer_logon_id": "csq***@sandbox.com",
            # "send_pay_date": "2017-03-21 13:29:17",
            # "receipt_amount": "20.00",
            # "out_trade_no": "out_trade_no15",
            # "buyer_pay_amount": "20.00",
            # "buyer_user_id": "2088102169481075",
            # "msg": "Success",
            # "point_amount": "0.00",
            # "trade_status": "TRADE_SUCCESS",  # 支付结果
            # "total_amount": "20.00"
            # }

            code = response.get('code')

            if code == '10000' and response.get('trade_status') == 'TRADE_SUCCESS':
                # 支付成功
                # 获取支付宝交易号
                trade_no = response.get('trade_no')
                # 更新订单状态
                order.trade_no = trade_no
                order.order_status = 4  # 待评价
                order.save()
                # 返回应答
                return JsonResponse({'res': 3, 'message': '支付成功'})
            elif code == '40004' or (code == '10000' and response.get('trade_status') == 'WAIT_BUYER_PAY'):
                # 等待买家付款
                import time
                time.sleep(5)
                continue
            else:
                # 支付出错
                return JsonResponse({'res': 4, 'errmsg': '支付失败'})


class OrderCommentView(LoginRequiredMixin, View):
    def get(self, request, order_id):
        """展示评论页"""
        user = request.user

        # 校验数据
        if not order_id:
            return redirect(reverse('user:order'))

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order'))

        # 需要根据状态码获取状态
        order.status_name = OrderInfo.ORDER_STATUS[order.order_status]

        # 根据订单id查询对应商品，计算小计金额,不能使用get
        order_skus = OrderGoods.objects.filter(order_id=order_id)
        for order_sku in order_skus:
            amount = order_sku.count * order_sku.price
            order_sku.amount = amount
        # 增加实例属性
        order.order_skus = order_skus

        context = {
            'order': order,
        }
        return render(request, 'df_order/order_comment.html', context)

    def post(self, request, order_id):
        """处理评论内容"""
        # 判断是否登录
        user = request.user

        # 判断order_id是否为空
        if not order_id:
            return redirect(reverse('user:order'))

        # 根据order_id查询当前登录用户订单
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order'))

        # 获取评论条数
        total_count = int(request.POST.get("total_count"))

        # 循环获取订单中商品的评论内容
        for i in range(1, total_count + 1):
            # 获取评论的商品的id
            sku_id = request.POST.get("sku_%d" % i)  # sku_1 sku_2
            # 获取评论的商品的内容
            content = request.POST.get('content_%d' % i, '')  # comment_1 comment_2

            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue

            # 保存评论到订单商品表
            order_goods.comment = content
            order_goods.save()

        # 修改订单的状态为“已完成”
        order.order_status = 5  # 已完成
        order.save()
        # 1代表第一页的意思，不传会报错
        return redirect(reverse("user:order", kwargs={"page": 1}))
