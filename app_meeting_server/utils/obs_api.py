# -*- coding: utf-8 -*-
# @Time    : 2023/11/22 20:33
# @Author  : Tom_zc
# @FileName: obs_api.py
# @Software: PyCharm
from obs import ObsClient


class ObsClientImp:
    def __init__(self, ak, sk, endpoint):
        if not all([ak, sk, endpoint]):
            raise RuntimeError("lack of params")
        self.obs_client = ObsClient(access_key_id=ak, secret_access_key=sk, server=endpoint)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.obs_client.close()

    def get_object(self, bucket_name, object_key):
        return self.obs_client.getObject(bucket_name, object_key)

    def list_objects(self, bucket_name):
        objs = []
        mark = None
        while True:
            obs_objs = self.obs_client.listObjects(bucket_name, marker=mark, max_keys=1000)
            if obs_objs.status < 300:
                index = 1
                for content in obs_objs.body.contents:
                    objs.append(content)
                    index += 1
                if obs_objs.body.is_truncated:
                    mark = obs_objs.body.next_marker
                else:
                    break
        return objs

    def upload_file(self, bucket_name, object_key, filename, metadata):
        return self.obs_client.uploadFile(bucketName=bucket_name, objectKey=object_key, uploadFile=filename,
                                          taskNum=10, enableCheckpoint=True, metadata=metadata)

    def upload_file_without_metadata(self, bucket_name, object_key, filename):
        return self.obs_client.uploadFile(bucketName=bucket_name, objectKey=object_key, uploadFile=filename,
                                          taskNum=10, enableCheckpoint=True)
