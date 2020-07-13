# -*- coding=utf-8
"""
腾讯云cos存储实例，实现上传文件
"""


from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
import sys
import logging

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

secret_id = 'AKIDQKURDVt7NuPDtL9zpRq23qTtFRRHYMK5'      # 替换为用户的 secretId
secret_key = 'lxwhy3uXyCdw93oMLTRFqZqrcDbaJqfN'      # 替换为用户的 secretKey
region = 'ap-shanghai'     # 替换为用户的 Region ,区域代码

config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key)
# 2. 获取客户端对象
client = CosS3Client(config)

#创建存储桶
# response = client.create_bucket(
#     Bucket='examplebucket-1250000000'
# )
# 查询存储桶列表
# response = client.list_buckets(
# )
#### 高级上传接口（推荐）
# 根据文件大小自动选择简单上传或分块上传，分块上传具备断点续传功能。
response = client.upload_file(
    Bucket='chenjianguo-1302458528',
    LocalFilePath='init_user.py',  #本地文件路径
    Key='aaa.txt',  #上传到桶之后的文件名
)
print(response['ETag'])