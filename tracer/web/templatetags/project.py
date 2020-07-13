from django.template import Library
from django.urls import reverse
from web import models

register = Library()
#存放自定义标签的目录名必须是templatetags 目录下面还要加一个__init__.py文件， {% load 标签 %}才不会出错
#如果一段html片段在很多页面中用到就可以使用inclusion_tag来实现
#自定义标签的一种，到时候可以用{% 标签名 %} 来产生这一段(inclusion/all_project_list.html)的html片段
@register.inclusion_tag('inclusion/all_project_list.html')#模板中去找这个路径
def all_project_list(request): #函数名也就是之后使用时的标签名
    # 1. 获我创建的所有项目
    my_project_list = models.Project.objects.filter(creator=request.tracer.user)

    # 2. 获我参与的所有项目
    join_project_list = models.ProjectUser.objects.filter(user=request.tracer.user)
    #需要返回字典类型，request由使用标签时传入
    return {'my': my_project_list, 'join': join_project_list,'request':request} #返回值字典类型，inclusion/all_project_list.html中可以直接使用键名得到对象

@register.inclusion_tag('inclusion/manage_menu_list.html')
def manage_menu_list(request):
    data_list=[
        {'title':'概述','url':reverse('dashboard',kwargs={'project_id': request.tracer.project.id})},
        {'title':'问题','url':reverse('issues',kwargs={'project_id': request.tracer.project.id})},
        {'title':'统计','url':reverse('statistics',kwargs={'project_id': request.tracer.project.id})},
        {'title':'wiki','url':reverse('wiki',kwargs={'project_id': request.tracer.project.id})},
        {'title':'配置','url':reverse('setting',kwargs={'project_id': request.tracer.project.id})},
        {'title':'文件','url':reverse('file',kwargs={'project_id': request.tracer.project.id})},
    ]
    for data in data_list:
        if request.path_info.startswith(data['url']):
            data['class']='active'
    return {'data_list':data_list}