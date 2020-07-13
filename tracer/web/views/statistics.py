from django.shortcuts import render
from web import models
from django.http import JsonResponse
import datetime
from django.db.models import Count
import collections

def statistics(request,project_id):

    return render(request,'statistics.html')

def statistics_chart(request,project_id):
    """优先级饼图"""
    start = datetime.datetime.strptime(request.GET.get('start'), '%Y-%m-%d')
    end = datetime.datetime.strptime(request.GET.get('end'), '%Y-%m-%d') + datetime.timedelta(days=1)
    result = models.Issues.objects.filter(project_id=project_id, create_datetime__gte=start, create_datetime__lt=end)
    result = result.values('priority').annotate(ct=Count('id'))
    #result : <QuerySet [{'priority': 'danger', 'ct': 5}, {'priority': 'success', 'ct': 1}, {'priority': 'warning', 'ct': 1}]>
    data_dict={}
    for key,value in models.Issues.priority_choices:
        data_dict[key]={'name':value,'y':0}
    for item in result:
        data_dict[item['priority']]['y'] = item['ct']

    return JsonResponse({'status':True,'data':list(data_dict.values())})

def statistics_project_user(request,project_id):
    start = datetime.datetime.strptime(request.GET.get('start'), '%Y-%m-%d')
    end = datetime.datetime.strptime(request.GET.get('end'), '%Y-%m-%d') + datetime.timedelta(days=1)
    #models.Issues.objects.filter(project_id=6).values('assign','status')起初考虑根据assign和status两个字段分组就可以拿到每个被指派用户
    #的不同状态问题数，但是这只能拿到存在的状态问题数，不存在的状态应该默认数量为0，所以应该创建个字典包含每个被指派用户每种状态问题的数量
    all_user_dict = collections.OrderedDict()#有序字典，键值对添加时是什么顺序，取值的时候顺序同样
    all_user_dict[request.tracer.project.creator.id] = {
        'name':request.tracer.project.creator.username,
        'status':{item[0]:0 for item in models.Issues.status_choices}
    }
    all_user_dict[None] = {
            'name':'未指派',
            'status':{item[0]:0 for item in models.Issues.status_choices}
        }
    #字典中加入项目参与者，构造每个人的每种状态问题数，并默认为0
    user_list = models.ProjectUser.objects.filter(project_id=project_id)
    for user in user_list:
        all_user_dict[user.user_id]={
            'name':user.user.username,
            'status':{item[0]:0 for item in models.Issues.status_choices}
        }
    #至此，all_user_dict存储了每个成员以及未指派的问题信息

    issues = models.Issues.objects.filter(project_id=project_id,create_datetime__gte=start, create_datetime__lt=end)
    for item in issues:
        if not item.assign:
            all_user_dict[None]['status'][item.status] += 1
        else:
            all_user_dict[item.assign_id]['status'][item.status] += 1

    categories = [data['name'] for data in all_user_dict.values()]
    data_result_dict = collections.OrderedDict()
    for item in models.Issues.status_choices:
        data_result_dict[item[0]] = {'name': item[1], "data": []}

    for key, text in models.Issues.status_choices:
        # key=1,text='新建'
        for row in all_user_dict.values():
            count = row['status'][key]
            data_result_dict[key]['data'].append(count)

    context = {
        'status': True,
        'data': {
            'categories': categories,
            'series': list(data_result_dict.values())
        }
    }
    return JsonResponse(context)