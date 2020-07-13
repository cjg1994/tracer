from django.template import Library

register = Library()
#前端想对某个字段值做一些定制化显示，就可以创建一个简单自定义标签
@register.simple_tag
def string_just(number):
    if number < 100:
        return "#{}".format(str(number).rjust(3,"0"))