from django.shortcuts import render,redirect
from utils.tencent.cos import delete_bucket
from django.http import JsonResponse
from web import models
def setting(request,project_id):
    return render(request,'setting.html')

def setting_delete(request,project_id):
    if request.method == 'GET':
        return render(request, 'setting_delete.html')
    project_name = request.POST.get('project_name')
    if not project_name or project_name != request.tracer.project.name:
        return render(request,'setting_delete.html',{'error':'项目名错误'})
    if request.tracer.user != request.tracer.project.creator:
        return render(request,'setting_delete.html',{'error':'只有创建者才能删除该项目'})
    #删除项目之前要删除对应的桶，1.删除桶下的所有文件 2.删除桶中所有碎片文件 3,.删除桶 4.删除项目

    delete_bucket(request.tracer.project.bucket,request.tracer.project.region)
    models.Project.objects.filter(id=project_id).delete()

    return redirect('project_list')