"""
用户账户相关功能：注册、短信、登录注销
"""
import uuid
import datetime
from django.shortcuts import render,HttpResponse,redirect
from web.forms.account import RegisterModelForm,SendSmsForm,LoginSMSForm,LoginForm
from django.http import JsonResponse
from web import models


def register(request):
    """注册"""
    if request.method == 'POST':
        form = RegisterModelForm(request.POST)
        if form.is_valid():
            #验证通过后，把注册的用户信息存入数据库
            instance=form.save()
            #相当于如下代码,form.save会自动把数据库中不存在的字段给剔除掉，而用create增加数据的话需要,数据库中存的是form.cleaned_data
            # form.cleaned_data.pop('code')
            # form.cleaned_data.pop('confirm_password')
            # instance = models.UserInfo.objects.create(**form.cleaned_data)
            #方式一：为刚注册的用户创建一条交易记录，个人免费版
            price_policy=models.PricePolicy.objects.filter(category=1,title='个人免费版').first()
            models.Transaction.objects.create(
                status=2,
                order=str(uuid.uuid4()),#内置库，根据计算机网卡，当前时间等信息生成的随机字符串作为订单号，理论上不会重复
                user=instance,#user字段是外键，所以赋值的是一个user实例对象
                price_policy=price_policy,#也是外键需要价格策略表的一个实例对象
                count=0,
                price=0,
                start_datetime=datetime.datetime.now()#结束时间字段可以为空，创建时间设置了auto_add_now=True会自动添加创建的当前时间
            )
            #方式二：交易记录表中不存放免费版的记录,那么就不必为注册的用户生成一条记录

            return JsonResponse({'status':True,'data':'/login/'})
        return JsonResponse({'status':False,'error':form.errors})
    form=RegisterModelForm()
    return render(request,'register.html',{'form':form})
def send_sms(request):
    #实例化
    form=SendSmsForm(request,data=request.GET)
    #字段中定义的验证规则和自定义的验证函数必须都没有错误，is_valid才返回True
    if form.is_valid():
        return JsonResponse({'status':'True'})
    """发送短信"""
    return JsonResponse({'status':False,'error':form.errors})#因为是form帮我们做的验证，只要有一项不通过，form.errors中都可以获取错误信息

def login_sms(request):
    """短信登录"""
    if request.method == 'GET':
        form = LoginSMSForm()
        return render(request,'login_sms.html',{'form':form})
    form=LoginSMSForm(request.POST)
    if form.is_valid():
        user_object = form.cleaned_data['mobile_phone'] #mobilephone的钩子函数中返回的是一个用户对象
        #把用户名写入到session
        request.session['user_id'] = user_object.id
        request.session.set_expiry(60 * 60 * 24 * 14)
        return JsonResponse({'status':True,'data':'/index/'})
    return JsonResponse({'status':False,'error':form.errors})

def index(request):
    return render(request,'index.html')

def login(request):
    if request.method == 'GET':
        form = LoginForm(request)
        return render(request,'login.html',{'form':form})
    form = LoginForm(request,request.POST)#不仅能校验字段,并且最后返回的return render(request,'login.html',{'form':form}) 因为字段中是有数据的，前端产生的input标签也会保存默认数据，即表单提交保留上次输入的值
    if form.is_valid():
        password = form.cleaned_data['password'] #验证的表单类中已经重写密码钩子函数，所以这里拿到的就是密文
        username = form.cleaned_data['username']
        # user_object = models.UserInfo.objects.filter(username=username,password=password).first()
        #更改为用手机号或者邮箱登录 那么条件就是 (手机号=手机号 and 密码=密码) or (邮箱等于邮箱 and 密码=密码)
        from django.db.models import Q
        user_object = models.UserInfo.objects.filter(Q(email=username) | Q(mobile_phone=username)).filter(password=password).first()
        if user_object:
            request.session['user_id'] = user_object.id
            request.session.set_expiry(60 * 60 * 24 * 14)
            return redirect('index')  #这里写的是别名 url的name为idnex
            # return redirect('index/')
            # return redirect('{% url "index" %}')
        form.add_error('username','用户名未注册')#如果查不到这个用户那么就给username字段加一个错误，前端可以通过字段的error属性获取到这里的错误信息
    return render(request,'login.html',{'form':form})

def image_code(request):
    """生成图片验证码"""
    from utils.image_code import check_code
    from io import BytesIO

    image_object,code = check_code() #图片对象和对应的验证码
    request.session['image_code'] = code #将验证码存入对应用户的session中,用户第一次GET请求页面的时候，服务端就会生成以随机字符串对应这个用户，
                                        # 所以当获取验证码图片的时候服务端是已经存有对应用户的session的
    request.session.set_expiry(60)   #设置session的过期时间为60秒，那么其中存的值(验证码)也是60秒
    stream = BytesIO()
    image_object.save(stream, 'png')
    return HttpResponse(stream.getvalue())

#退出函数
def logout(request):
    request.session.flush()#清空发这个请求的用户的session里的信息，那么前面从session中取user_id就会取不到，代表着用户退出了
    return redirect('index')