from django.shortcuts import render,reverse
from web.forms.issues import IssuesModelForm,IssuesReplyModelForm,IssuesInviteForm
from django.http import JsonResponse
from utils.pagination import Pagination
from web import models
from django.views.decorators.csrf import csrf_exempt
import json
from django.utils.safestring import mark_safe
from utils.encrypt import uid
import datetime


class CheckFilter:
    def __init__(self,name,data_list,request):
        self.data_list = data_list
        self.request = request
        self.name = name
    def __iter__(self):
        for item in self.data_list:
            key = str(item[0])
            value = item[1]
            value_list = self.request.GET.getlist(self.name)  #列表中元素是字符串形式['1','2','3']
            ck=""
            if key in value_list:
                ck = "checked"
                value_list.remove(key)
            else:
                value_list.append(key)   #value_list中的元素拿来作为下一次点击时生成的url中各个参数的值
            query_dict = self.request.GET.copy()
            query_dict._mutable = True
            query_dict.setlist(self.name,value_list)
            if 'page' in query_dict:
                query_dict.pop('page')
            url = "{}?{}".format(self.request.path_info,query_dict.urlencode()) #querydict对象的urlencode方法 生成url中参数的部分
            yield mark_safe("<a class='cell' href='{url}'><input type='checkbox'/ {ck}>{value}</a>".format(value=value,ck=ck,url=url))
class SelectFilter():
    def __init__(self,name,data_list,request):
        self.data_list = data_list
        self.request = request
        self.name = name
    def __iter__(self):
        yield mark_safe("<select class='select2' multiple='multiple' style='width:100%'>")
        for item in self.data_list:
            key = str(item[0])
            text = item[1]
            value_list = self.request.GET.getlist(self.name)
            select = ""
            if key in value_list:
                select = "selected"
                value_list.remove(key)
            else:
                value_list.append(key)
            query_dict = self.request.GET.copy()
            query_dict._mutable = True
            query_dict.setlist(self.name, value_list)
            url = "{}?{}".format(self.request.path_info, query_dict.urlencode())  # querydict对象的urlencode方法 生成url中参数的部分
            yield mark_safe("<option value='{url}' {select}>{text}</option>".format(select=select,text=text,url=url))
        yield mark_safe("</select>")
def issues(request, project_id):
    if request.method == 'GET':
        # 根据URL做筛选，筛选条件（根据用户通过GET传过来的参数实现）
        # ?status=1&status=2&issues_type=1
        allow_filter_name = ['issues_type', 'status', 'priority', 'assign', 'attention']
        conditions = {}
        for key in allow_filter_name:
            value_list = request.GET.getlist(key)
            if not value_list:
                continue
            conditions["{}__in".format(key)] = value_list
        form = IssuesModelForm(request)
        queryset = models.Issues.objects.filter(project = request.tracer.project).filter(**conditions)
        current_page = request.GET.get('page','')
        all_count = queryset.count()
        base_url = request.path_info
        query_params = request.GET
        per_page =10
        paginator = Pagination(current_page, all_count, base_url, query_params, per_page)
        issues_object_list = queryset[paginator.start:paginator.end]

        issues_type_list = list(models.IssuesType.objects.filter(project_id=project_id).values_list('id','title').distinct())
        #选出项目创建者和参与者，组成一个(id,username)的列表
        total_user_list=[(request.tracer.project.creator_id,request.tracer.project.creator.username),]
        project_user_list = models.ProjectUser.objects.filter(project_id=project_id).values_list('user_id','user__username')
        total_user_list.extend(project_user_list)

        invite_form = IssuesInviteForm()
        context = {
            'issues_object_list':issues_object_list,
            'page_html':paginator.page_html(),
            'form':form,
            'invite_form':invite_form,
            'status_filter':CheckFilter('status',models.Issues.status_choices,request),
            'priority_filter':CheckFilter('priority',models.Issues.priority_choices,request),
            'issues_type_filter':CheckFilter('issues_type',issues_type_list,request),
            'assign_filter':SelectFilter('assign',total_user_list,request),
            'attention_filter':SelectFilter('attention',total_user_list,request),
        }
        return render(request, 'issues.html',context)
    form = IssuesModelForm(request,data=request.POST)

    if form.is_valid():
        #校验通过，写入数据库
        form.instance.project = request.tracer.project
        form.instance.creator = request.tracer.user
        form.save()
        return JsonResponse({'status':True})
    return JsonResponse({'status':False,'error':form.errors})

def issues_detail(request,project_id,issue_id):

    issue_object = models.Issues.objects.filter(id=issue_id,project=request.tracer.project).first()
    form = IssuesModelForm(request,instance=issue_object)
    return render(request,'issues_detail.html',{'form':form,'issue_object':issue_object})

@csrf_exempt
def issues_record(request,project_id,issue_id):
    if request.method == 'GET':
        #返回对应问题的回复
        reply_objects = models.IssuesReply.objects.filter(issues_id=issue_id)
        reply_list = []
        for row in reply_objects:
            reply_dict = {
                'id':row.id,
                'creator':row.creator.username,
                'reply_type':row.get_reply_type_display(),
                'content':row.content,
                'parent_id':row.reply_id,  #reply_id这样即使reply为空也不会报错，但是reply.id就必须reply不为空
                'datetime':row.create_datetime
            }
            reply_list.append(reply_dict)
        return JsonResponse({'status':True,'data':reply_list})
    form = IssuesReplyModelForm(request.POST)
    if form.is_valid():
        #保存提交的回复
        form.instance.reply_type = 2
        form.instance.issues_id = issue_id #外键赋值也可以是其关联的表的字段的赋值
        form.instance.creator = request.tracer.user
        instance = form.save()
        data = {
            'id': instance.id,
            'creator': instance.creator.username,
            'reply_type': instance.get_reply_type_display(),
            'content': instance.content,
            'parent_id': instance.reply_id,  # reply_id这样即使reply为空也不会报错，但是reply.id就必须reply不为空
            'datetime': instance.create_datetime
        }
        return JsonResponse({'status':True,'data':data})

    return JsonResponse({'status':False,'error':form.errors})

@csrf_exempt
def issues_change(request,project_id,issue_id):
    post_dict = json.loads(request.body.decode('utf-8'))
    issue_object = models.Issues.objects.filter(id=issue_id,project_id=project_id).first() #找到要更新的那个字段
    name = post_dict.get('name')
    value = post_dict.get('value')
    field = models.Issues._meta.get_field(name) #获取模型中对应字段对象

    def create_reply_record(content):
        instance = models.IssuesReply.objects.create(
            reply_type=1,
            issues=issue_object,
            content=content,
            creator=request.tracer.user
        )
        data = {
            'id': instance.id,
            'creator': instance.creator.username,
            'reply_type': instance.get_reply_type_display(),
            'content': instance.content,
            'parent_id': instance.reply_id,  # reply_id这样即使reply为空也不会报错，但是reply.id就必须reply不为空
            'datetime': instance.create_datetime
        }
        return data
    #1.数据库对应的问题数据字段更新
    #1.1 字段的值是文本类型，无论前端发来的是什么值，修改文本值都不会对其它数据造成影响
    #因为假如有恶意请求，不是手动更改页面上的选项，而是直接往接口post请求，发送的是不合法的数据，所以需要进行判断
    if name in ['subject','desc','start_date','end_date']:
        if not field.null:
            #不能为空但是传来的数据是空的
            if not value:
                return JsonResponse({'status':False,'errror':'该字段不能为空'})
            #不能为空，且传来的数据不为空，那么就更新字段并保存
            setattr(issue_object,name,value)
            issue_object.save()
            content = "{}更新为{}".format(field.verbose_name,value) #获取字段对应的中文名
        else:
            #字段可以为空且数据为空
            setattr(issue_object,name,None)
            issue_object.save()
            content = "{}更新为空".format(field.verbose_name)
            #字段可以为空切数据不为
            # 空  其实和字段不能为空，数据不为空逻辑一样，都是需要更新字段并保存
            setattr(issue_object, name, value)
            issue_object.save()
            content = "{}更新为{}".format(field.verbose_name, value)
        #2.更新完数据库中的记录后将instance返回，让前端生成一条操作记录,创建一条IssuesReply记录
        return JsonResponse({'status':True,'data':create_reply_record(content)})
    if name in ['issues_type','parent','module','assign']:
        #外键类型的字段，要判断传来的value值是否对应着某个对象
        if not value:
            if not field.null:
                return JsonResponse({'ststus':False,'error':'值不能为空'})
            setattr(issue_object,name,None)
            issue_object.save()
            content = "{}更新为空".format(field.verbose_name)
        else:
            #如果是assign字段，关联表是UserInfo,查找的是所有用户id是否等于value,我们应该只查找项目关联的用户是否有这个id
            if name == 'assign':
                #是否是项目创建者
                if value == str(request.tracer.project.creator_id):
                    instance = request.tracer.project.creator
                else:
                    project_user_object = models.ProjectUser.objects.filter(project_id=project_id,user_id=value).first()
                    if project_user_object:
                        instance = project_user_object.user
                    else:
                        instance = None
                if not instance:
                    return JsonResponse({'ststus': False, 'error':'对应用户不存在'})
                setattr(issue_object, name, instance)
                issue_object.save()
                content = "{}更新为{}".format(field.verbose_name, str(instance))
            else:
                #其他三个字段，用户传来的数据不为空,去关联的表中找是否存在id=value的数据对象
                exist = field.rel.model.objects.filter(id=value,project_id=project_id).first()  #外键字段得到关联的ORM模型 field.rel.model
                if not exist:
                    return JsonResponse({'ststus': False, 'error': '数据不合法'})
                setattr(issue_object,name,exist)
                issue_object.save()
                content = "{}更新为{}".format(field.verbose_name,str(exist))
        return JsonResponse({'status': True, 'data': create_reply_record(content)})
    if name == 'attention':
        #多对多字段，此时传来的value应该是一个列表  类似 ['1','2','3']
        #构建一个项目关联用户的列表，遍历value，看看每个值是否都能找到对应的用户
        if not isinstance(value, list):
            return JsonResponse({'status': False, 'error': "数据格式错误"})
        if not value:
            issue_object.attention.set(value) #m2m字段设置值要使用set方法，这里将字段值设为空，并且会清空m2m字段产生的关系表中的该问题所有的数据，即该问题关注者为空
            issue_object.save()
            content = "{}更新为空".format(field.verbose_name)
        else:
            user_dict = {str(request.tracer.project.creator_id):request.tracer.project.creator.username} #外键关联字段可以使用下划线写法creator_id
            rows = models.ProjectUser.objects.filter(project_id=project_id)                            #但是username只能是creator.username
            for row in rows:
                user_dict[str(row.user_id)] = row.user.username
            username_list = []
            for v in value:
                username = user_dict.get(str(v))  #不确定前端传来的value中的元素是整型还是字符串类型，都转成字符串进行比较
                if not username:
                    return JsonResponse({'ststus': False, 'error': '部分用户不存在'})
                username_list.append(username)
            issue_object.attention.set(value)
            issue_object.save()
            content = "{}更新为{}".format(field.verbose_name, ",".join(username_list))
        return JsonResponse({'status': True, 'data': create_reply_record(content)})
    if name in ['priority', 'status', 'mode']:
        choices = field.choices
        text=None
        for k,v in choices:
            if str(k) == value:
                text=v
        if not text:
            return JsonResponse({'ststus': False, 'error': '选择不合法'})
        setattr(issue_object,name,value)
        issue_object.save()
        content = "{}更新为{}".format(field.verbose_name,text)
        return JsonResponse({'status': True, 'data': create_reply_record(content)})

def invite_url(request,project_id):
    form = IssuesInviteForm(data=request.POST)

    if request.tracer.user != request.tracer.project.creator:
        form.add_error('period','只有项目创建者才能生成邀请码')
        return JsonResponse({'status':False,'error':form.errors})
    if form.is_valid():
        #生成一个随机码保存到数据库
        random_invite_code = uid(request.tracer.user.mobile_phone)
        form.instance.project = request.tracer.project
        form.instance.code = random_invite_code
        form.instance.creator = request.tracer.user
        form.save()
        #拼接随机码生成一个邀请链接
        url = "{scheme}://{host}{path}".format(
            scheme=request.scheme,#协议
            host=request.get_host(),#主机名
            path=reverse('invite_join', kwargs={'code': random_invite_code}) #邀请链接一类的url
        )
        return JsonResponse({'status':True,'data':url})
    return JsonResponse({'status':True,'error':form.errors})

def invite_join(request,code):
    """校验邀请码"""
    #检验链接的code部分是否能在数据表中查询到对应记录，如果不存在，则不能加入
    invite_object = models.ProjectInvite.objects.filter(code=code).first()
    if not invite_object:
        return render(request,'invite_join.html',{'error':'邀请码不存在'})
    #如果登录者是项目创建者，则不能加入
    if request.tracer.user == invite_object.project.creator:
        return render(request, 'invite_join.html', {'error': '项目创建者无需加入'})
    #如果登录者已经是项目参与者，则不能加入
    exist = models.ProjectUser.objects.filter(project=invite_object.project,user=request.tracer.user).exists()
    if exist:
        return render(request, 'invite_join.html', {'error': '项目成员无需再加入'})
    # 如果邀请码已过期，则不能加入
    current_time = datetime.datetime.now()
    if current_time > invite_object.create_datetime + datetime.timedelta(minutes=invite_object.period):
        return render(request, 'invite_join.html', {'error': '邀请码过期'})
    ##项目创建者创建的项目的参与人数上限如果已经达到，则不能加入
    # 首先要获取项目创建者对应的额度，就可以得到最大成员数
    max_transaction = models.Transaction.objects.filter(user=invite_object.project.creator).order_by('-id').first()
    if max_transaction.price_policy.category == 1:#如果是免费版用户
        max_member = max_transaction.price_policy.project_member
    else:#否则是收费版用户，就要判断该用户的收费订单的结束时间是否已超过
        if max_transaction.end_datetime < current_time: #说明用户付费额度已过期
            free_object = models.PricePolicy.objects.filter(category=1).first()
            max_member = free_object.project_member
        else: #如果用户付费购买的额度未过期，则使用对应价格策略的最大成员数
            max_member = max_transaction.price_policy.project_member
        #接着判断项目的用户数是否已经大于等于上面的最大成员数
    #获取邀请码对应项目的已有成员数
    curren_member = models.ProjectUser.objects.filter(project_id=invite_object.project).count()
    if curren_member + 1 >= max_member:
        return render(request, 'invite_join.html', {'error': '项目成员超过限制，请升级套餐'})
    #如果邀请码使用数量超过上限，则不能加入 要先判断count是否为空，空表示无数量显示
    if invite_object.count:
        if invite_object.use_count >= invite_object.count:
            render(request, 'invite_join.html', {'error': '该邀请码超过最大使用数'})
        invite_object.use_count += 1 #上面的验证都通过之后，将验证码使用数+1，并且在项目参与者表中添加登录者的记录，并且更新成员数字段
        invite_object.save()
    models.ProjectUser.objects.create(user=request.tracer.user, project=invite_object.project)
    invite_object.project.join_count += 1
    invite_object.project.save()

    return render(request, 'invite_join.html', {'project': invite_object.project})
