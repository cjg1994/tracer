from django.shortcuts import render,redirect
from web.forms.wiki import WikiModelForm
from django.urls import reverse
from web import models
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from utils.tencent.cos import file_upload
from utils.encrypt import uid

def wiki(request,project_id):
    if request.method == 'GET':
        wiki_id = request.GET.get('wiki_id')
        if not wiki_id or not wiki_id.isdecimal():
            return render(request,'wiki.html')
        wiki_object = models.Wiki.objects.filter(id=wiki_id,project=request.tracer.project).first()
        return render(request,'wiki.html',{'wiki_object':wiki_object})
    return render(request,'wiki.html')

def wiki_add(request,project_id):
    if request.method == 'GET':
        form = WikiModelForm(request)
        return render(request, 'wiki_form.html', {'form':form})
    form = WikiModelForm(request,request.POST)
    if form.is_valid():
        #因为wiki表中的project是一个外键，所以要赋一个项目实例对象，也可以通过form.instance.project_id = project_id  外键_属性
        form.instance.project = request.tracer.project
        if form.instance.parent:
            form.instance.depth = form.instance.parent.depth + 1
        else:
            form.instance.depth = 1
        form.save()
        return redirect(reverse('wiki',kwargs={'project_id':project_id}))
    #如果有错，就是还留在wiki_add.html界面，并且输入框保留上次输入的内容，只要传入form = WikiModelForm(request.POST)即可
    return render(request,'wiki_form.html',{'form':form})

def wiki_catalog(request,project_id):

    data = models.Wiki.objects.filter(project=request.tracer.project).values('id','title','parent_id').order_by('depth','id')

    return JsonResponse({'status':True,'data':list(data)})

def wiki_delete(request,project_id,wiki_id):
    models.Wiki.objects.filter(project=request.tracer.project,id=wiki_id).delete()
    return render(request,'wiki.html')

def wiki_edit(request,project_id,wiki_id):
    wiki_object = models.Wiki.objects.filter(project=request.tracer.project, id=wiki_id).first()
    if not wiki_object:
        url = reverse('wiki',kwargs={'project_id':project_id})
        return redirect(url)
    #一个实例对象去实例化出一个表单对象采用instance参数
    if request.method == 'GET':
        form = WikiModelForm(request,instance=wiki_object)
        return render(request,'wiki_form.html',{'form':form})
    form = WikiModelForm(request, data=request.POST,instance=wiki_object) #instance参数是必需的，表示对数据库中这行数据进行修改
    # form = WikiModelForm(request, data=request.POST) #不加instance就会新增一条数据
    if form.is_valid():
        form.instance.project = request.tracer.project
        if form.instance.parent:
            form.instance.depth = form.instance.parent.depth + 1
        else:
            form.instance.depth = 1
        form.save()
        url= reverse('wiki', kwargs={'project_id': project_id})
        new_url = '{0}?wiki_id={1}'.format(url,wiki_object.id)
        return redirect(new_url)

#图片是以post方式上传，会报一个Forbidden错误，要跳过csrf验证需要加上一个装饰器
@csrf_exempt
def wiki_upload(request,project_id):
    #上传图片后返回给markdown的数据格式
    result = {
        'success': 0,
        'message': None,
        'url': None
    }

    file_object = request.FILES.get('editormd-image-file') #得到一个图片对象
    if not file_object:
        result['message'] = '文件不存在'
        return JsonResponse(result)
    bucket = request.tracer.project.bucket
    region = request.tracer.project.region
    ext = file_object.name.rsplit('.')[-1]  #文件流对象 name属性可以获取文件名  取后缀名用于构造文件名
    key = "{}.{}".format(uid(request.tracer.user.mobile_phone),ext)
    image_url = file_upload(bucket=bucket,
                region=region,
                key=key,
                file=file_object)

    result['success'] = 1
    result['url'] = image_url
    return JsonResponse(result)

