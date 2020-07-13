from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
from qcloud_cos.cos_exception import CosServiceError


from django.conf import settings


def create_bucket(bucket, region='ap-chengdu'):
    """
    创建桶
    :param bucket:桶名
    :param region:桶所在区域
    :return:
    """

    config = CosConfig(Region=region, SecretId=settings.TENCENT_COS_ID, SecretKey=settings.TENCENT_COS_KEY)

    client = CosS3Client(config)
    # 创建桶
    response = client.create_bucket(
        Bucket=bucket,
        ACL="public-read"  # private  / public-read /public-read-write
    )
    cors_config = {
        'CORSRule': [
            {
                'MaxAgeSeconds': 500,
                'AllowedOrigin': ['*', ],  # ["http://www.qq.com","https://www.xxx.com"]
                'AllowedMethod': ['GET', 'PUT', 'HEAD', 'POST', 'DELETE'],
                'AllowedHeader': ['*', ],
                'ExposeHeader': ['*', ]
            }
        ]
    }
    # 桶的跨域设置
    client.put_bucket_cors(
        Bucket=bucket,
        CORSConfiguration=cors_config
    )


def file_upload(bucket, region, key, file):
    # upload_file_from_buffer(self, Bucket, Key, Body, MaxBufferSize=100, PartSize=10, MAXThread=5, **kwargs):
    config = CosConfig(Region=region, SecretId=settings.TENCENT_COS_ID, SecretKey=settings.TENCENT_COS_KEY)

    client = CosS3Client(config)
    # 创建桶
    response = client.upload_file_from_buffer(
        Bucket=bucket,
        Key=key,  # 上传到桶之后的文件名
        Body=file,  # 要上传的文件流对象，不是本地文件，本地文件上传用upload_file  因为是markdown读取本地文件，传给django(相当于文件流), django再传给腾讯COS
    )
    ##https://chenjianguo-1302458528.cos.ap-shanghai.myqcloud.com/123.txt
    return "https://{}.cos.{}.myqcloud.com/{}".format(bucket, region, key)


def file_delete(bucket, region, key):
    config = CosConfig(Region=region, SecretId=settings.TENCENT_COS_ID, SecretKey=settings.TENCENT_COS_KEY)

    client = CosS3Client(config)
    objects = {
        "Quiet": "true",
        "Object": key
    }
    response = client.delete_objects(
        Bucket=bucket,
        Delete=objects
    )


def credential(bucket, region):
    from sts.sts import Sts
    config = {
        # 临时密钥有效时长，单位是秒
        'duration_seconds': 1800,
        'secret_id': settings.TENCENT_COS_ID,
        # 固定密钥
        'secret_key': settings.TENCENT_COS_KEY,
        # 设置网络代理
        # 'proxy': {
        #     'http': 'xx',
        #     'https': 'xx'
        # },
        # 换成你的 bucket
        'bucket': bucket,
        # 换成 bucket 所在地区
        'region': region,
        # 这里改成允许的路径前缀，可以根据自己网站的用户登录态判断允许上传的具体路径
        # 例子： a.jpg 或者 a/* 或者 * (使用通配符*存在重大安全风险, 请谨慎评估使用)
        'allow_prefix': '*',
        # 密钥的权限列表。简单上传和分片需要以下的权限，其他权限列表请看 https://cloud.tencent.com/document/product/436/31923
        'allow_actions': [
            # 简单上传
            'name/cos:PutObject',
            'name/cos:PostObject',
            # 分片上传
            'name/cos:InitiateMultipartUpload',
            'name/cos:ListMultipartUploads',
            'name/cos:ListParts',
            'name/cos:UploadPart',
            'name/cos:CompleteMultipartUpload'
        ],

    }

    sts = Sts(config)
    result_dict = sts.get_credential()
    return result_dict


def file_check(bucket, region, key):
    config = CosConfig(Region=region, SecretId=settings.TENCENT_COS_ID, SecretKey=settings.TENCENT_COS_KEY)
    client = CosS3Client(config)
    # 会返回一个字典，其中就有对应文件的信息,也就是对应key的ETag值
    data = client.head_object(
        Bucket=bucket,
        Key=key
    )
    return data


def delete_bucket(bucket, region):
    config = CosConfig(Region=region, SecretId=settings.TENCENT_COS_ID, SecretKey=settings.TENCENT_COS_KEY)
    client = CosS3Client(config)
    try:
        # 桶中所有文件
        while True:  # 循环，每次最多取1000个文件
            part_objects = client.list_objects(bucket)  # 最多1000个  返回的互数据类似一个json数据
            contents = part_objects.get('Contents')  # 所有文件对象列表   其中有个键Contents 值是一个个文件的信息
            if not contents:
                break

            objects = {
                'Quiet': "true",
                "Object": [{'Key': item["Key"]} for item in contents]
            }
            # 批量删除
            client.delete_objects(bucket, objects)
            if part_objects['IsTruncated'] == "flase":  # part_objects有一个IsTruncated键，表示是否是截断的数据
                break

        # 找到碎片，删除
        while True:
            part_uploads = client.list_multipart_uploads(bucket)
            uploads = part_uploads.get('Upload')
            if not uploads:
                break
            for item in uploads:
                client.abort_multipart_upload(bucket, item['Key'], item['UploadId'])
            if part_uploads['IsTruncated'] == "false":
                break
        # 删除桶
        client.delete_bucket(bucket)
    except CosServiceError as e:
        pass