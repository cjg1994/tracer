from django import forms
from web.models import Wiki
from web.forms.bootstrap import BootStrapForm
class WikiModelForm(BootStrapForm,forms.ModelForm):

    class Meta:
        model = Wiki
        exclude = ['project','depth']

    def __init__(self,request,*args,**kwargs):
        super().__init__(*args,**kwargs)
        #下拉框显示自己特定的值，choices中的元祖第一个元素是数据库中存的值，第二个值是下拉框中显示的值
        total_data_list = [('','请选择'),] #第一个元素为空表示添加时的id会自动赋值
        data_list = Wiki.objects.filter(project=request.tracer.project).values_list('id','title')
        total_data_list.extend(data_list)
        self.fields['parent'].choices = total_data_list
