from django.shortcuts import render,HttpResponse,redirect
from web import models
import datetime
from django_redis import get_redis_connection
import json
from utils.encrypt import uid
from django.conf import settings
from utils.alipay import AliPay

def index(request):
    return render(request,'index.html')

def price(request):
    policy_list = models.PricePolicy.objects.filter(category=2) #取出付费的价格策略
    return render(request,'price.html',{'policy_list':policy_list})

def payment(request,policy_id):
    policy_object = models.PricePolicy.objects.filter(id=policy_id,category=2).first() #用户点击购买的套餐
    if not policy_object:
        return redirect('price')

    #购买的数量
    number = request.GET.get('number','')
    if not number or not number.isdecimal(): # "123".isdecimal() --> True
        return redirect('price')
    number = int(number)
    if number < 1:
        return redirect('price')
    #购买的原价
    origin_price = number * policy_object.price
    #如果属于套餐升级，要抵扣掉之前套餐剩余的价格
    balance = 0 #抵扣的价格
    _object = None
    if request.tracer.price_policy.category == 2:#说明用户曾经购买过套餐
        #用户最近一次的付费订单
        _object = models.Transaction.objects.filter(user=request.tracer.user,status=2,price_policy__category=2).order_by('-id').first()
        #判断订单是否已使用完，否则用户就是免费用户
        current_time = datetime.datetime.now()
        total_timedelta = _object.end_datetime - _object.start_datetime
        balance_timedelta = _object.end_datetime - current_time
        if total_timedelta.days == balance_timedelta.days:
            balance = _object.price / total_timedelta.days * (balance_timedelta.days - 1)
        else:
            balance = _object.price / total_timedelta.days * balance_timedelta.days
    if balance > origin_price: #抵扣的价格比要购买的套餐更贵，比如SSVIP的用户去购买VIP的套餐，即不能套餐降级
        return redirect('price')

    context = {
        'policy_id':policy_object.id,
        'number':number,
        'origin_price':origin_price,
        'balance':round(balance,2),
        'total_price':origin_price - round(balance,2),
        'title':policy_object.title,
    }
    conn = get_redis_connection() #django-redis redis的配置信息在settings中
    key = "payment_{}".format(request.tracer.user.mobile_phone)
    conn.set(key,json.dumps(context),ex=60*30)  #把此次的订单信息存到redis中,因为存储需要序列化，所以调用json.dumps，ex是存储有效期，单位秒
    context['transaction'] = _object   #以前最近一次的订单信息
    context['policy_object'] = policy_object #要购买的套餐策略对象
    return render(request,'payment.html',context)

def pay(request):
    """生成支付订单，去支付宝支付"""
    conn = get_redis_connection()
    key = "payment_{}".format(request.tracer.user.mobile_phone)
    context_string = conn.get(key)
    if not context_string:
        return redirect('price')
    context = json.loads(context_string.decode('utf-8'))
    order_id = uid(request.tracer.user.mobile_phone)
    total_price = context['total_price']
    #数据库生成一条未支付的订单记录
    models.Transaction.objects.create(
        status=1,
        order=order_id,
        user=request.tracer.user,
        price_policy_id=context['policy_id'],
        count=context['number'],
        price=total_price
    )
    subject = context['title']

    alipay = AliPay(
        appid=settings.ALI_APPID,
        app_notify_url=settings.ALI_NOTIFY_URL,
        return_url=settings.ALI_RETURN_URL,
        app_private_key_path=settings.ALI_PRI_KEY_PATH,
        alipay_public_key_path=settings.ALI_PUB_KEY_PATH
    )
    query_params = alipay.direct_pay(
        subject=subject,
        out_trade_no=order_id,
        total_amount=total_price
    )
    pay_url = "{}?{}".format(settings.ALI_GATEWAY,query_params)
    return redirect(pay_url)
    # public_params = {
    #     "app_id":"2016102900777041",
    #     "method":"alipay.trade.page.pay",
    #     "format":"JSON",
    #     "return_url":"http://127.0.0.1:8001/pay/notify/",
    #     "notify_url":"http://127.0.0.1:8001/pay/notify/",
    #     "charset":"utf-8",
    #     "sign_type":"RSA2",
    #     "timestamp":datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),#格式要求"2014-07-24 03:07:50",
    #     "version":"1.0",
    #     "biz_content":json.dumps({
    #         "out_trade_no":order_id,
    #         "product_code":"FAST_INSTANT_TRADE_PAY",
    #         "total_amount":total_price,
    #         "subject":subject,
    #     },separators=(",",":")),  #上述的都是公共参数，该key存放的是请求参数
    # }
    # # public_params.pop("sign")
    # # sorted(public_params) #返回的是key的排序列表
    # params_list = ["{}={}".format(key,public_params.get(key)) for key in sorted(public_params)]
    # #待签名的字符串
    # unsigned_string = "&".join(params_list)
    # #调用加密函数，利用商户应用私钥对待签名字符串进行签名，并进行Base64编码,编码之后的字符串不能有换行符，需要替换为空
    # #导入加密函数 先pip install Cryptodome
    # from Crypto.PublicKey import RSA
    # from Crypto.Signature import PKCS1_v1_5
    # from Crypto.Hash import SHA256
    # from base64 import decodebytes,encodebytes
    # #用加密函数结合私钥对待签名字符串进行加密
    # private_key = RSA.importKey(open("files/应用私钥").read())
    # signer = PKCS1_v1_5.new(private_key)
    # signature = signer.sign(SHA256.new(unsigned_string.encode('utf-8')))
    # #
    # print(type(signature)) #bytes类型
    # sign_string = encodebytes(signature).decode("utf-8").replace('\n','')
    # #
    # from urllib.parse import quote_plus
    # result ="&".join(["{}={}".format(key,quote_plus(public_params.get(key))) for key in sorted(public_params)])
    # result = result + "&sign=" + quote_plus(sign_string)
    #
    # gateway = "https://openapi.alipaydev.com/gateway.do"
    # ali_pay_url = "{}?{}".format(gateway,result)
    # #跳转到支付宝的链接
    # return redirect(ali_pay_url)
    # #RSA key format is not supported

def pay_notify(request):
    """支付成功后触发的URL，一个是return_url,一个是notify_url"""
    alipay = AliPay(
        appid=settings.ALI_APPID,
        app_notify_url=settings.ALI_NOTIFY_URL,
        return_url=settings.ALI_RETURN_URL,
        app_private_key_path=settings.ALI_PRI_KEY_PATH,
        alipay_public_key_path=settings.ALI_PUB_KEY_PATH
    )
    if request.method == "GET":
        #只做跳转，判断是否支付成功，不做订单更新
        #支付宝会结合支付宝公钥通过GET方法返回数据，需要判断是不是支付宝返回的数据，还是别人伪造的数据
        params = request.GET.dict()
        sign = params.pop('sign', None)
        status = alipay.verify(params, sign)
        if status:
            #可以在这里测试一下订单更新功能，因为GET请求不需要公网IP而是本地跳转
            """
            current_datetime = datetime.datetime.now()
            out_trade_no = params['out_trade_no']
            _object = models.Transaction.objects.filter(order=out_trade_no).first()

            _object.status = 2
            _object.start_datetime = current_datetime
            _object.end_datetime = current_datetime + datetime.timedelta(days=365 * _object.count)
            _object.save()
            """
            return HttpResponse('支付完成')
        return HttpResponse('支付失败')
    else:
        #POST,这里做订单状态的更新，因为服务器如果宕机,支付宝会往notify_url间隔多次地发post请求
        from urllib.parse import parse_qs
        body_str = request.body.decode('utf-8')
        post_data = parse_qs(body_str)
        post_dict = {}
        for k, v in post_data.items():
            post_dict[k] = v[0]

        sign = post_dict.pop('sign', None)
        status = alipay.verify(post_dict, sign)
        if status:
            current_datetime = datetime.datetime.now()
            out_trade_no = post_dict['out_trade_no']
            _object = models.Transaction.objects.filter(order=out_trade_no).first()

            _object.status = 2
            _object.start_datetime = current_datetime
            _object.end_datetime = current_datetime + datetime.timedelta(days=365 * _object.count)
            _object.save()
            return HttpResponse('success')

        return HttpResponse('error')