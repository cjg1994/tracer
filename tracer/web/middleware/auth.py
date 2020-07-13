from django.utils.deprecation import MiddlewareMixin #导入中间件

import datetime
from django.conf import settings
from django.shortcuts import redirect
from web import models

class Tracer():
    def __init__(self):
        self.user = None
        self.price_policy = None
        self.project = None
class AuthMiddleWare(MiddlewareMixin):

    def process_request(self,request):
        """如果用户已登录，则在request中赋值"""
        request.tracer = Tracer()
        user_id = request.session.get('user_id',0)
        user_object = models.UserInfo.objects.filter(id=user_id).first()
        request.tracer.user = user_object

        #白名单 没有登录也可以访问的页面  #request.path_info 是获取当前请求的url(urls.py中定义的路径url 比如 /login/  /image/code/)
        if request.path_info in settings.WHITE_REGEX_URL_LIST:
            #下面这行就是一个return 一开始以为是renturn request 但是报错了
            return   #若用户访问的是白名单 执行到这一步结束
        #检查用户是否登录，已登录继续往后走，未登录返回登录页面
        if not request.tracer.user:
            return redirect('/login/')
        #若用户没登录 知道这一步就结束了

        #创建项目之前要获取当前用户所拥有的的额度
        #方式一：获取当前用户的最近一次交易记录，每个注册的用户交易表中都生成一条免费版的交易记录
        _object = models.Transaction.objects.filter(user=user_object,status=2).order_by('-id').first()
        #判断额度是否已过期
        current_datetime = datetime.datetime.now()
        if _object.end_datetime and _object.end_datetime < current_datetime:
            #表示过期了，那就变成了免费用户
            _object = models.Transaction.objects.filter(user=user_object,status=2,price_policy__category=1).first()
        #以后在视图函数中取请求用户的数据时，就可以通过request.tracer这个对象
        request.tracer.price_policy = _object.price_policy #价格策略表中的一条数据对象

        #方式二：Transaction交易表中只存放购买记录，免费的用户记录不存放
        """
        _object = models.Transaction.objects.filter(user=user_object, status=2).order_by('-id').first()
        if not _object:
            request.price_policy = models.PricePolicy.objects.filter(category=1,title="个人免费版").filter()
        else:
            current_datetime = datetime.datetime.now()
            if _object.end_datetime and _object.end_datetime < current_datetime:
                request.price_policy = models.PricePolicy.objects.filter(category=1, title="个人免费版").filter()
            else:
                request.price_policy = _object.price_policy
        """

    # 所有请求先经过process_request,再做路由匹配，再执行process_view，最后再去执行对应的视图函数
    def process_view(self,request,view,args,kwargs):
        if not request.path_info.startswith('/manage/'): #如果访问的url不是项目相关的就返回 交由后续的视图函数处理
            return #
        project_id = kwargs.get('project_id') #kwargs中保存了url中参数匹配的信息 键值对
        project_object = models.Project.objects.filter(id=project_id,creator=request.tracer.user).first()
        if project_object: #如果访问的是项目管理相关的url并且是登录者创建的项目 就返回 交由视图函数处理
            request.tracer.project = project_object
            return
        project_user_object = models.ProjectUser.objects.filter(project_id=project_id,user=request.tracer.user).first()
        if project_user_object:
            request.tracer.project = project_user_object.project
            return
        return redirect('project_list') #如果访问的是项目管理相关的url 但是登陆者并不是项目创建者或者相关者 那么就只能看项目的列表首页


