import os

import oss2

from datetime import datetime


class OSSClient:
    def __init__(self):
        self.endpoint = os.getenv('OSS_ENDPOINT')
        self.bucket_name = os.getenv('OSS_BUCKET_NAME')
        self.auth = oss2.Auth(os.getenv('ACCESS_KEY_ID'), os.getenv('ACCESS_KEY_SECRET'))
        self.bucket = oss2.Bucket(self.auth, self.endpoint, self.bucket_name)

    def put_object(self, key, data):
        date_prefix = datetime.now().strftime("%Y/%m/%d")
        full_key = f"{date_prefix}/{key}"

        # 根据文件扩展名设置 Content-Type
        headers = {}
        if key.endswith('.mp4'):
            headers['Content-Type'] = 'video/mp4'
        elif key.endswith('.mp3'):
            headers['Content-Type'] = 'audio/mpeg'
        elif key.endswith('.wav'):
            headers['Content-Type'] = 'audio/wav'
        elif key.endswith('.jpg') or key.endswith('.jpeg'):
            headers['Content-Type'] = 'image/jpeg'
        elif key.endswith('.png'):
            headers['Content-Type'] = 'image/png'
        # 可以根据需要添加更多的文件类型

        # 上传对象并设置头部
        self.bucket.put_object(full_key, data, headers=headers)

        # 生成并返回对象的 URL
        url_prefix = self.endpoint.replace('https://', f'https://{self.bucket_name}.')
        return f'{url_prefix}/{full_key}'

    def get_object(self, key):
        return self.bucket.get_object(key).read()

    def delete_object(self, key):
        self.bucket.delete_object(key)

    def list_objects(self):
        return [obj.key for obj in oss2.ObjectIterator(self.bucket)]

    def get_object_url(self, key):
        return self.bucket.sign_url('GET', key, 0)

    def put_object_from_file(self, key, file_path):
        self.bucket.put_object_from_file(key, file_path)

    def get_object_to_file(self, key, file_path):
        self.bucket.get_object_to_file(key, file_path)

    def delete_objects(self, keys):
        self.bucket.batch_delete_objects(keys)

    def delete_bucket(self):
        oss2.Bucket(self.auth, self.bucket.bucket_name).delete_bucket()

if __name__ == '__main__':
    oss_client = OSSClient()
    oss_client.put_object("test.txt", b"hello world")
    print(oss_client.get_object_url("test.txt"))
