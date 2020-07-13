from django import forms
from web import models
from web.forms.bootstrap import BootStrapForm
from django.core.exceptions import ValidationError
from web.forms.widgets import ColorRadioSelect
class ProjectModelForm(BootStrapForm,forms.ModelForm):
    bootstrap_class_exclude = ['color']
    # desc = forms.CharField(widget=forms.Textarea(attr={}))
    class Meta:
        model = models.Project
        fields=['name','color','desc']
        widgets={
            'desc':forms.Textarea(),
            #''color':forms.RadioSelect #color字段包含choices参数，默认是select下拉框，这里改成RadioSelect
            #下面使用的是自定义的插件，继承RadioSelect,并把其中生成的ul li标签替换掉，那么前端展示的时候会横着显示，并且还可以自己加span标签
            'color':ColorRadioSelect(attrs={'class':'color-radio'})
        }
    def __init__(self,request,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.request = request
    def clean_name(self):
        #校验name字段
        name = self.cleaned_data['name']
        #1.当前用户创建要创建的项目是否与他创建过的项目同名
        exists = models.Project.objects.filter(name=name,creator=self.request.tracer.user).exists()
        if exists:
            raise ValidationError("同名项目已存在")  #这里的异常会保存在视图函数中的form实例对象的errors属性中
        #2.当前用户创建的项目最大数是否已经达到
        max_items = self.request.tracer.price_policy.project_num
        count = models.Project.objects.filter(creator=self.request.tracer.user).count()

        if count >= max_items:
            raise ValidationError('超过最大创建数，请购买增值服务')
        return name   #一定要记得钩子函数要返回对应的字段值，不然会报错 这个字段不能为null