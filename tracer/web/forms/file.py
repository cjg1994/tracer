from django import forms
from web.forms.bootstrap import BootStrapForm
from web import models
from django.core.exceptions import ValidationError
from utils.tencent.cos import file_check

class FileFolderModelForm(BootStrapForm,forms.ModelForm):

    class Meta:
        model = models.FileRepository
        fields= ['name']

    def __init__(self,request,folder_id,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.request = request
        self.folder_id = folder_id

    def clean_name(self):

        name = self.cleaned_data['name']
        if self.folder_id:
            exists = models.FileRepository.objects.filter(name=name,project=self.request.tracer.project,parent_id=self.folder_id)
        else:
            exists = models.FileRepository.objects.filter(name=name,project=self.request.tracer.project,parent__isnull=True)#查询一个字段是否为空__isnull=True
        if exists:
            raise ValidationError('文件夹已存在')

        return name


class FileModelForm(forms.ModelForm):
    etag = forms.CharField(label='ETag')

    class Meta:
        model = models.FileRepository
        exclude = ['project','file_type','update_user','update_datetime']

    def __init__(self,request,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.request = request
    def clean_file_path(self):
        file_path = self.cleaned_data['file_path']
        return "https://{}".format(file_path) #将文件名拼接成url
    #整体字段的钩子，每个字段的钩子执行完后执行
    def clean(self):
        key = self.cleaned_data['key'] #前端上传成功后发送到后端的key,如果有非法用户并非上传文件，而是直接往url post一个请求，并且也包括一个key,这个clean函数就会捕获到错误
        etag = self.cleaned_data['etag']
        size = self.cleaned_data['file_size']
        if not key or not etag:
            return self.cleaned_data
        #向COS校验文件是否是自己传到COS的文件，因为如果存在非法用户直接向视图函数的url发post请求，也会把请求的数据写入数据库
        from qcloud_cos.cos_exception import CosServiceError
        try:
            result = file_check(self.request.tracer.project.bucket, self.request.tracer.project.region, key)
        except CosServiceError as e:
            self.add_error('key','文件不存在')
            return self.cleaned_data
        if etag != result.get('ETag'):
            self.add_error('etag','ETag错误') #给某个字段添加错误信息，这样表单验证就会不通过 form.is_valid()是False
        # print(size)
        # print(type(size)) #int 因为数据模型中字段要求就是整数，
        # print("***************")
        # print(type(result.get('Content-Length')))
        # print(result.get('Content-Length')) #str 要转成int
        if int(size) != int(result.get('Content-Length')):
            self.add_error('file_size','文件大小错误')
        return self.cleaned_data