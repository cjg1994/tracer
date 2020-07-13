
import hashlib
from django.conf import settings
import uuid

def md5(string):
    """md5加密"""
    hash_object = hashlib.md5(settings.SECRET_KEY.encode('utf8'))#参数需要的是字节类型，所以需要编码 加盐
    hash_object.update(string.encode('utf-8')) #需要的是字节类型  对string加密
    return hash_object.hexdigest() #返回密文

def uid(string):
    data = "{}-{}".format(str(uuid.uuid4()), string)
    return md5(data)