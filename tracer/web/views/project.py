from django.shortcuts import render,HttpResponse,redirect
from django.http import JsonResponse
from web.forms.project import ProjectModelForm
from web import models

from utils.tencent.cos import create_bucket
import time

def project_list(request):
    if request.method == 'GET':
        form = ProjectModelForm(request)
        #我创建的项目：星标，未星标
        #我参与的项目：星标，未星标
        project_dict = {'star':[],'my':[],'join':[]}
        my_projects = models.Project.objects.filter(creator=request.tracer.user)
        for row in my_projects:
            if row.star == True:
                project_dict['star'].append({'value':row,'type':'my'})
            else:
                project_dict['my'].append({'value':row,'type':'my'})
        join_projects =  models.ProjectUser.objects.filter(user=request.tracer.user)
        for row in join_projects:
            if row.star:
                project_dict['star'].append({'value':row.project,'type':'join'})
            else:
                project_dict['join'].append({'value':row.project,'type':'join'})
        return render(request,'project_list.html',{'form':form,'project_dict':project_dict})
    form = ProjectModelForm(request,data=request.POST)

    if form.is_valid():
        #form.instance等于这个project实例
        #创建项目时创建一个桶 桶名：手机号-时间戳 后面那串数字是你自己的腾讯云存储账号附带固定的一个值
        bucket_name = "{}-{}-1302458528".format(request.tracer.user.mobile_phone,int(time.time()))
        region = "ap-chengdu"
        create_bucket(bucket_name,region)
        # 项目表中有些字段有默认值，所以不需要添加，creator是一个外键，所以要赋一个用户对象
        form.instance.creator = request.tracer.user
        form.instance.bucket = bucket_name
        form.instance.region = region
        #创建项目，但是还需要校验一些字段，比如是否还有空间创建项目，是否有权限创建，所以在 ProjectModelForm中加上各个字段的钩子函数
        instance = form.save()
        #3.创建项目时初始化问题类型，也就是给问题类型表添加该项目的几条默认数据
        issuetype_list = []
        for item in models.IssuesType.PROJECT_INIT_LIST:
            issuetype_list.append(models.IssuesType(project=instance,title=item))
        models.IssuesType.objects.bulk_create(issuetype_list)

        return JsonResponse({'status':True})

    return JsonResponse({'status':False,'error':form.errors})



def project_star(request,project_type,project_id):
    if project_type == 'my':
        models.Project.objects.filter(id=project_id,creator=request.tracer.user).update(star=True)
        return redirect('project_list') #返回项目列表页，又会进入到项目列表页的视图函数，最后返回项目列表.html
    if project_type == 'join':
        #ProjectUser模型中project是外键，获取project的id的形式为project_id
        models.ProjectUser.objects.filter(project_id=project_id,user=request.tracer.user).update(star=True)
        return redirect('project_list')
    # if project_type == 'star':
    #     models.Project.objects.filter(id=project_id,creator=request.tracer.user).update(star=False)
    #     #Q查询要放在前面，不等于某个对象要用Q查询，project中的creator是一个外键，不同于id,要使用双下划线,表示要跨到userInfo表
    #     models.ProjectUser.objects.filter(~Q(project__creator=request.tracer.user),project_id=project_id).update(star=False)
    #     return redirect('project_list')
    return HttpResponse('类型错误')

def project_unstar(request,project_type,project_id):
    if project_type == 'my':
        models.Project.objects.filter(id=project_id,creator=request.tracer.user).update(star=False)
        return redirect('project_list') #返回项目列表页，又会进入到项目列表页的视图函数，最后返回项目列表.html
    if project_type == 'join':
        #ProjectUser模型中project是外键，获取project的id的形式为project_id
        models.ProjectUser.objects.filter(project_id=project_id,user=request.tracer.user).update(star=False)
        return redirect('project_list')

    return HttpResponse('类型错误')