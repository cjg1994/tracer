"""离线脚本的前提设置"""

import os
import sys
import django


base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)
os.environ.setdefault("DJANGO_SETTINGS_MODULE","tracer.settings")  #为了能找到这个配置文件需要修改sys.path
django.setup()