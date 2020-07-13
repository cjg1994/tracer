#bootstrap样式单独拿出来作为一个form,以后要用直接导入再多继承
class BootStrapForm(object):
    bootstrap_class_exclude = []  #部分继承，有些字段加样式，有些字段不加
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) #这里执行forms.Form的__init__方法后self.fields就存在了 所以说子类要想实例化时执行2个父类的init方法，就需要调super
        for name, field in self.fields.items():  #name表示字段名称，field表示这个字段对象 #这里的self.fields是怎么得到的,
#多继承class LoginSMSForm(BootStrapForm,forms.Form): 上面的super调用的是forms.Form的__init__方法 ，回想起继承的MRO顺序
            if name in self.bootstrap_class_exclude: #部分字段继承样式
                continue
            old_class = field.widget.attrs.get('class','')
            field.widget.attrs['class'] = '{} form-control'.format(old_class) #为每个字段添加class样式
            field.widget.attrs['placeholder'] = '请输入%s' % (field.label,) #为每个字段添加placeholder样式;输入框默认值请输入用户名就是这个属性


if __name__ == '__main__':
    b=BootStrapForm()
    print(b.fields)