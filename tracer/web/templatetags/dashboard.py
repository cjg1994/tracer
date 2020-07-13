from django.template import Library

register = Library()
#根据size大小显示成 KB M G
@register.simple_tag
def user_space(size):
    if size > 1024 * 1024 * 1024:
        return '{:.2f}G'.format(size / 1024 * 1024 * 1024)
    if size > 1024 * 1024:
        return '{:.2f}M'.format(size / 1024 * 1024)
    if size > 1024:
        return '{:.2f}KB'.format(size / 1024)
    else:
        return '{:.2f}B'.format(size)
