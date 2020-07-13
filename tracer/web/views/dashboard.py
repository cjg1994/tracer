from django.shortcuts import render
from web import models
from django.db.models import Count
from django.http import JsonResponse
import datetime
import time
import collections

def dashboard(request,project_id):
    #问题概览
    objects = models.Issues.objects.filter(project_id=project_id).values('status').annotate(c=Count('id'))
    context = {}
    for key,value in models.Issues.status_choices:
        context[key] = {'text':value,'count':0}
    for item in objects:
        context[item['status']]['count'] = item['c']
    #项目成员
    user_list = models.ProjectUser.objects.filter(project_id=project_id).values('user_id', 'user__username')#项目参与者 id 姓名
    # 动态概览 显示前10个问题
    top_ten_object = models.Issues.objects.filter(project_id=project_id,assign__isnull=False).order_by('-id')[0:10]

    return render(request,'dashboard.html',{
        'issues_object':context,
        'user_list':user_list,
        'top_ten_object':top_ten_object,
    })

def issues_chart(request,project_id):
    today = datetime.datetime.now().date()
    result = models.Issues.objects.filter(project_id=project_id,create_datetime__gt=today-datetime.timedelta(days=30)).extra(
        select={'ctime':"strftime('%%Y-%%m-%%d',web_issues.create_datetime)"}).values('ctime').annotate(ct=Count('id'))
                #类似sql语句 select name,age,Date(datetime) as time from xxx group by time
                #第一个参数列的别名，第二个参数把时间列转换成指定格式  时间格式,数据表的真实名字.字段
                 # MySQL中时间格式化的语句是 "DATE_FORMAT(web_transaction.create_datetime,'%%Y-%%m-%%d')"
    #result: <QuerySet [{'ctime': '2020-06-28', 'ct': 2}, {'ctime': '2020-07-01', 'ct': 5}]>
    data_dict = collections.OrderedDict()
    for i in range(30):
        date = today - datetime.timedelta(days=i)
        data_dict[date.strftime('%Y-%m-%d')] = [time.mktime(date.timetuple()) * 1000,0]    #时间戳乘以1000,因为时间戳是秒，而highcharts中时间格式默认单位是毫秒
    for item in result:
        data_dict[item['ctime']][1] = item['ct']

    data_list = list(data_dict.values())  #有部分元素中只有一个时间戳元素，因为那天并没有创建问题，所以要设置一个默认值0
    # print(data_list)
    return JsonResponse({'status':True,'data':data_list})



