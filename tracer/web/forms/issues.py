from django import forms
from  web.forms.bootstrap import BootStrapForm
from web import models


class IssuesModelForm(BootStrapForm,forms.ModelForm):
    class Meta: #内部类的设置在实例化之前
        model = models.Issues
        exclude = ['project','creator','create_datetime','latest_update_datetime']
        widgets = {
            "assign":forms.Select(attrs={'class':'selectpicker','data-live-search':'true'}),
            "attention":forms.SelectMultiple(attrs={'class':'selectpicker','data-live-search':'true','data-actions-box':'true'}),
            "parent": forms.Select(attrs={'class': 'selectpicker', 'data-live-search': 'true'}),
        }

    def __init__(self,request,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.request = request

        #数据初始化 外键字段展现为下拉框，要想自定义选择下拉框中显示的数据，就要初始化字段的choices值
        #当前项目所有的问题类型 values_list返回的数据格式是 [(),()]
        self.fields['issues_type'].choices = models.IssuesType.objects.filter(project=self.request.tracer.project).values_list('id','title')
        #当前项目所有模块

        module_list = [('','没有选中任何项')]
        module_object_list = models.Module.objects.filter(project=self.request.tracer.project).values_list('id','title')
        module_list.extend(module_object_list)
        self.fields['module'].choices = module_list
        #指派给谁,关注者，只要获取当前项目的参与者与创建者

        total_user_list = [(self.request.tracer.project.creator.id,self.request.tracer.project.creator.username),]
        project_user_list = models.ProjectUser.objects.filter(project=self.request.tracer.project).values_list('user_id','user__username')
        user_list = [('', '没有选中任何项'),]
        user_list.extend(total_user_list)
        user_list.extend(project_user_list)
        self.fields['assign'].choices = user_list
        self.fields['attention'].choices = total_user_list
        #
        # #当前项目已经创建的问题

        parent_issue_list = [('','没有选中任何项')]
        parent_list = models.Issues.objects.filter(project=self.request.tracer.project).values_list('id','subject') #id与主题
        parent_issue_list.extend(parent_list)
        self.fields['parent'].choices = parent_issue_list

class IssuesReplyModelForm(forms.ModelForm):
    class Meta:
        model = models.IssuesReply
        fields = ['content','reply']


class IssuesInviteForm(BootStrapForm,forms.ModelForm):
    class Meta:
        model = models.ProjectInvite
        fields = ['period','count']