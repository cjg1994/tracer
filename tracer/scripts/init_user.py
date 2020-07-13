"""使用离线脚本向用户表添加数据"""
import os
import sys
import django


base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)
os.environ.setdefault("DJANGO_SETTINGS_MODULE","tracer.settings")  #为了能找到这个配置文件需要修改sys.path
django.setup()

from web import models
#ORM增加数据
models.UserInfo.objects.create(username='chenrusheng',email='123456789@qq.com',mobile_phone='15757116315',password=12345678)
