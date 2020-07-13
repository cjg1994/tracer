from django.shortcuts import render,HttpResponse
from web.forms.file import FileFolderModelForm,FileModelForm
from django.http import JsonResponse
from web import models
from utils.tencent.cos import file_delete,credential
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
import json
import requests
# from django.forms import model_to_dict

def file(request,project_id):
    folder_id = request.GET.get('folder', '')
    parent_object = None
    if folder_id.isdecimal():
        parent_object = models.FileRepository.objects.filter(id=folder_id, project=request.tracer.project).first()
    if request.method == 'POST':
        edit_id = request.POST.get('fid','')
        edit_object = None
        if edit_id.isdecimal():
            edit_object = models.FileRepository.objects.filter(id=edit_id,project=request.tracer.project).first()
        if edit_object:
            form = FileFolderModelForm(request,folder_id,data=request.POST,instance=edit_object)
        else:
            form = FileFolderModelForm(request, folder_id=folder_id, data=request.POST)  # 不要忘了data参数，不然是一张空表，下面验证不会通过
        if form.is_valid():
            form.instance.project = request.tracer.project
            form.instance.file_type = 2
            form.instance.parent = parent_object
            form.instance.update_user = request.tracer.user
            form.save()
            return JsonResponse({'status':True})

        return JsonResponse({'status':False,'error':form.errors})
    folder_list = []
    if parent_object:
        #说明查询的是某个文件夹的列表
        file_list = models.FileRepository.objects.filter(project=request.tracer.project,parent=parent_object).order_by('-file_type')
    else:
        #查询根目录
        file_list = models.FileRepository.objects.filter(project=request.tracer.project,parent__isnull=True).order_by('-file_type')

    while parent_object:
        #进入父目录，页面中要展示目录的路径
        folder_list.insert(0,parent_object)
        #folder_list.insert(0,{'id':parent_object.id,'name':parent_object.name})
        # model_to_dict(parent_object,['id','name'])#与上一行等价，将对象转换成字典，需要导入model_to_dict
        parent_object = parent_object.parent


    form = FileFolderModelForm(request,folder_id=folder_id)

    return render(request,'file.html',{'form':form,'file_list':file_list,'folder_list':folder_list,'folder_id':folder_id})


def folder_delete(request,project_id):
    fid = request.GET.get('fid')
    #传来的fid可能是文件或者文件夹的id
    delete_object = models.FileRepository.objects.filter(id=fid,project=request.tracer.project).first()
    #若是文件:
    if delete_object.file_type == 1:
        request.tracer.project.use_space -= delete_object.file_size
        #要把cos中的文件删除接着要把列表页面的这个文件显示删除
        key = [{'Key':delete_object.name}]
        file_delete(request.tracer.project.bucket,request.tracer.project.region,key)
        delete_object.delete()
    else:
        #若是文件夹，需要把此文件夹下的所有文件删除并且返还使用空间
        key = []
        total_use_size = 0
        folder_list = [delete_object,]
        for folder in folder_list:
            childrens = models.FileRepository.objects.filter(parent=delete_object)
            for children in childrens:
                if children.file_type == 2:
                    folder_list.append(children)
                else:
                    total_use_size += children.file_size
                    key.append({'Key':children.key})
        file_delete(request.tracer.project.bucket,request.tracer.project.region,key)
        delete_object.delete()
    return JsonResponse({'status':True})

@csrf_exempt
def file_credential(request,project_id):
    # print(request.body)   #b'[{"name":"shenhe.png","size":31348}]' 大小单位是B
    #如果文件大小超出，那么就不返回临时凭证，而是返回一个字典表示错误信息
    file_list = json.loads(request.body.decode('utf-8'))
    total_size = 0
    per_file_size = request.tracer.price_policy.per_file_size * 1024 * 1024
    for file in file_list:
        total_size += file.get('size')
        if file.get('size') > per_file_size:
            return JsonResponse({'status':False,'error':'单文件过大，最大允许{}M'.format(request.tracer.price_policy.per_file_size)})
    if total_size + request.tracer.project.use_space > request.tracer.price_policy.project_space*1024*1024*1024:
        return JsonResponse({'status': False, 'error': "容量超过限制，请升级套餐。"})
    result_dict = credential(request.tracer.project.bucket,request.tracer.project.region)
    return JsonResponse({'status':True,'data':result_dict})

@csrf_exempt
def file_save(request,project_id):
    # print(request.POST) #前端传来的parent是一个id,表单实例化的时候自动转成了对应的对象
    form = FileModelForm(request,data=request.POST)
    if form.is_valid():  #表单验证
        #通过form.save()的方法存储到数据库返回的instance对象，通过  instance.get_file_type_display( 的方式获取不到choices的中文信息
        # form.instance.file_type = 1
        # form.update_user = request.tracer.user
        # instance = form.save()  #添加成功后，新添加的那个对象    数据库的file_type中存的是1或2  要想取得对应的中文用instance.get_file_type_display()
        data_dict = form.cleaned_data #得到清洗后的数据
        # print(data_dict) #此时parent已经是一个对象
        data_dict.pop('etag')
        data_dict.update({'project':request.tracer.project,'file_type':1,'update_user':request.tracer.user})
        instance = models.FileRepository.objects.create(**data_dict) #通过create方法存入数据库 成功写入但是展示的时候没有实时刷新
        request.tracer.project.use_space += instance.file_size
        request.tracer.project.save()
        #构造一个字典返回给前端用于展示上传的文件信息
        return JsonResponse({'status':True,'data':{
            'id':instance.id,
            'name':instance.name,
            'file_size':instance.file_size,
            'update_user':instance.update_user.username,
            'update_datetime':instance.update_datetime.strftime('%Y{}%m{}%d{} %H:%M').format('年','月','日'), #这里的转换还不支持中文
            'download_url':reverse('file_download',kwargs={'project_id':project_id,'download_id':instance.id})
        }})
    return JsonResponse({'status':False,'error':'文件写入失败'})


def file_download(request,project_id,download_id):
    #文件下载的思路是先获取文件的数据，返回一个response,再设置响应头
    file_object = models.FileRepository.objects.filter(id=download_id).first()
    res = requests.get(file_object.file_path) #content获取的是二进制数据
    data = res.content#小文件
    data = res.iter_content() #大文件，分块下载
    response = HttpResponse(data,content_type="application/octet-stream") #左下角会有个下载提示框
    from django.utils.encoding import escape_uri_path
    response['Content-Disposition'] = "attachment; filename={}".format(escape_uri_path(file_object.name))#中文文件名转义
    return response