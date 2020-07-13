from django import forms
from web import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

from django_redis import get_redis_connection
from utils.tencent.sms import send_sms_single
from django.conf import settings
import random

from web.forms.bootstrap import BootStrapForm
from utils import encrypt

class RegisterModelForm(forms.ModelForm):
    #这里添加的字段并不会写入数据库，视图函数中form.save的时候会去掉不需要的字段
    mobile_phone = forms.CharField(label='手机号', validators=[RegexValidator(r'^(1[3|4|5|6|7|8|9])\d{9}$', '手机号格式错误'), ])
    password = forms.CharField(
        label='密码',
        min_length=8,
        max_length=64,
        error_messages={
            'min_length':'密码长度不能小于8个字符',
            'max_length':'密码长度不能大于64个字符'
        },
        widget=forms.PasswordInput())

    confirm_password = forms.CharField(
        label='重复密码',
        widget=forms.PasswordInput())
    code = forms.CharField(
        label='验证码',
        widget=forms.TextInput())

    class Meta:
        model = models.UserInfo
        fields = ['username', 'email', 'password', 'confirm_password', 'mobile_phone', 'code'] #页面中展示的字段顺序

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():  #name表示字段名称，field表示这个字段对象
            field.widget.attrs['class'] = 'form-control' #为每个字段添加class样式
            field.widget.attrs['placeholder'] = '请输入%s' % (field.label,) #为每个字段添加placeholder样式

    def clean_username(self):
        #models中的模型创建时各个字段类型以及其中的参数(譬如EmaiField)已经是一层校验，只有过了之后才会再到这歌函数来验证
        #用这个表单实例化的时候会调用这个函数验证username字段
        username=self.cleaned_data['username']
        exists = models.UserInfo.objects.filter(username=username).exists()
        if exists:
            raise ValidationError('用户名已存在')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        exists = models.UserInfo.objects.filter(email=email).exists()
        if exists:
            raise ValidationError('邮箱已存在')
        return email

    def clean_password(self):
        password=self.cleaned_data['password']
        #加密并返回
        return encrypt.md5(password)
    def clean_confirm_password(self):
        pwd=self.cleaned_data.get('password') #因为先校验的password字段，所以这里也是取到的密文
        if not pwd:
            raise ValidationError('密码不合规范')
        confirm_pwd=encrypt.md5(self.cleaned_data['confirm_password']) #所以这里也要将重复密码加密并进行比较
        if pwd != confirm_pwd:
            raise ValidationError('两次密码不一致')
        return confirm_pwd

    def clean_mobile_phone(self):
        mobile_phone = self.cleaned_data['mobile_phone']
        exists = models.UserInfo.objects.filter(mobile_phone=mobile_phone).exists()
        if exists:
            raise ValidationError('手机号已被注册')
        return mobile_phone

    def clean_code(self):
        code = self.cleaned_data['code']
        # mobile_phone = self.cleaned_data['mobile_phone']
        mobile_phone = self.cleaned_data.get('mobile_phone')
        if not mobile_phone:
            return code
        conn = get_redis_connection()
        redis_code = conn.get(mobile_phone)
        if not redis_code:
            raise ValidationError('验证码失效或未发送，请重新发送')

        redis_str_code = redis_code.decode('utf-8')
        if code.strip() != redis_str_code:
            raise ValidationError('验证码错误，请重新输入')
        return code
#创建用于验证的数据的表单
class SendSmsForm(forms.Form):
    mobile_phone=forms.CharField(label='手机号',validators=[RegexValidator(r'^(1[3|4|5|6|7|8|9])\d{9}$', '手机号格式错误'),])

    #在全局的clean验证函数执行完后，会执行对应的每个字段的验证函数，定义方式为clean__字段名，因为全局的clean返回的是self.cleand_data
    #如果上面定义的mobile_phone中的验证通过了,说明可以取到self.cleaned_data['mobile_phone']，此时再进入自定义的验证函数进行验证
    def __init__(self,request,*args,**kwargs):
        super().__init__(*args,**kwargs)
        #重写init方法，实例化时将request传入,*args,**kwargs表示原来实例化时传入的data=request.GET等参数
        self.request = request

    def clean_mobile_phone(self):
        """重写局部钩子手机校验"""
        mobile_phone=self.cleaned_data['mobile_phone']

        #判断短信模板是否有问题
        tpl=self.request.GET['tpl']
        template_id = settings.TENCENT_SMS_TEMPLATE.get(tpl)
        if not template_id:
            # self.add_error('mobile_phone','短信模板错误')
            raise ValidationError('短信模板错误')
        exists = models.UserInfo.objects.filter(mobile_phone=mobile_phone).exists()
        if tpl == 'login':
            # exists = models.UserInfo.objects.filter(mobile_phone=mobile_phone).exists()
            if not exists:
                raise ValidationError('该手机未注册')
        else:
            #检测手机号是否已被注册
            # exists = models.UserInfo.objects.filter(mobile_phone=mobile_phone).exists()
            if exists:
                raise ValidationError('手机号已存在')
        #生成随机四位数
        code=random.randrange(1000,9999)

        #发送短信,
        sms=send_sms_single(mobile_phone,template_id,[code,])
        if sms['result'] != 0:
            raise ValidationError('短信发送失败，{}'.format(sms['errmsg']))
        #验证码写入redis(django-redis)
        conn = get_redis_connection()
        conn.set(mobile_phone,code,ex=60)
        return mobile_phone

class LoginSMSForm(BootStrapForm,forms.Form): #另一种做法:多继承BootStrapForm,将下面的__init__方法注释掉
    mobile_phone = forms.CharField(label='手机号', validators=[RegexValidator(r'^(1[3|4|5|6|7|8|9])\d{9}$', '手机号格式错误'), ])
    code = forms.CharField(
        label='验证码',
        widget=forms.TextInput())
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     for name, field in self.fields.items():  #name表示字段名称，field表示这个字段对象
    #         print("***********",self.fields)
    #         field.widget.attrs['class'] = 'form-control' #为每个字段添加class样式
    #         field.widget.attrs['placeholder'] = '请输入%s' % (field.label,) #为每个字段添加placeholder样式
    def clean_mobile_phone(self):
        mobile_phone = self.cleaned_data['mobile_phone']
        user_object = models.UserInfo.objects.filter(mobile_phone=mobile_phone).first()
        if not user_object:
            raise ValidationError('手机号未注册')
        return user_object  #若验证通过，那么之后通过cleaned_data['mobile_phone']取到的就是该用户对象

    def clean_code(self):
        code = self.cleaned_data['code']
        user_object = self.cleaned_data.get('mobile_phone')
        if not user_object:
            return code
        conn = get_redis_connection()
        redis_code = conn.get(user_object.mobile_phone)
        if not redis_code:
            raise ValidationError('验证码失效或未发送，请重新发送')

        redis_str_code = redis_code.decode('utf-8')
        if code.strip() != redis_str_code:
            raise ValidationError('验证码错误，请重新输入')
        return code

class LoginForm(BootStrapForm,forms.Form):
    username=forms.CharField(label='手机号或者邮箱')
    password=forms.CharField(label='密码',widget=forms.PasswordInput(render_value=True))#render_value当密码输入错误时点击登录页面刷新会保留原密码
    code=forms.CharField(label='图片验证码')

    #读取用户输入的验证码，所以需要用到request,视图函数中会实例化这个类，所以可以通过重写init将request引入到这里
    #但是code是类中定义的字段，所以直接可以通过self.cleaned_data['code']来获取
    # 但是要获取存在服务器端的session中的验证码，又需要request,还是要重写__init__
    def __init__(self,request,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.request = request
    #重写密码钩子，返回的是加密的密码，因为之前注册的时候密码也是加密之后，在通过form.save保存的 所以数据库中存的是加密的密码
    def clean_password(self):
        password = self.cleaned_data['password']
        return encrypt.md5(password)
    #重写钩子，不止有ModelForm有钩子函数，forms.Form也是有的
    def clean_code(self):
        code = self.cleaned_data['code'] #表单中定义的字段的字段名会变成前端标签的name属性
        session_code = self.request.session.get('image_code') #因为验证码可能过期了，所以用get方法获取 要注意session中存验证码的时候的键的名称不能写错
        if not session_code:
            raise ValidationError('验证码已过期，点击重新获取')
        if code.strip().upper() != session_code: #验证码忽略左右空格，并且大小写不敏感
            raise ValidationError('验证码输入错误')
        return code

