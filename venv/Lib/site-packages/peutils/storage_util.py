# -*- coding: UTF-8 -*-

'''
Author: vincent yao
Date: 2023/7/4
Short Description:
    三方存储API
Change History:

'''
import json
import os
from urllib.parse import quote

import boto3
import oss2
from obs import ObsClient


# =========================================================S3========================================================
class S3_API:
    def __init__(self, aws_access_key_id, aws_secret_access_key, endpoint_url, bucket):
        self.client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            endpoint_url=endpoint_url,
        )
        self.bucket = bucket

    def list_current_folders(self, prefix):
        folders = []
        response = self.client.list_objects_v2(
            Bucket=self.bucket, Prefix=prefix, Delimiter="/"
        )
        folders.extend(
            [content["Prefix"] for content in response.get("CommonPrefixes", [])]
        )

        while response.get("IsTruncated", False):
            continuation_token = response.get("NextContinuationToken")
            response = self.client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
                ContinuationToken=continuation_token,
                Delimiter="/",
            )
            folders.extend(
                [content["Prefix"] for content in response.get("CommonPrefixes", [])]
            )
        return folders

    def list_current_files(self, prefix, suffixes=[]):
        contents = []

        response = self.client.list_objects_v2(
            Bucket=self.bucket, Prefix=prefix, Delimiter="/"
        )
        contents.extend(
            list(
                filter(
                    lambda x: any(
                        [x.get("Key").endswith(suffix) for suffix in suffixes]
                        + [not suffixes]
                    ),
                    response.get("Contents", []),
                )
            )
        )

        while response.get("IsTruncated", False):
            continuation_token = response.get("NextContinuationToken")
            response = self.client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
                ContinuationToken=continuation_token,
                Delimiter="/",
            )
            contents.extend(
                list(
                    filter(
                        lambda x: any(
                            [x.get("Key").endswith(suffix) for suffix in suffixes]
                            + [not suffixes]
                        ),
                        response.get("Contents", []),
                    )
                )
            )
        contents = list(filter(lambda x: not x.get("Key").endswith("/"), contents))

        return contents

    def list_bucket_files_deep(self, prefix, suffixes=[]):
        contents = []

        response = self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        contents.extend(
            list(
                filter(
                    lambda x: any(
                        [x.get("Key").endswith(suffix) for suffix in suffixes]
                        + [not suffixes]
                    ),
                    response.get("Contents", []),
                )
            )
        )

        while response.get("IsTruncated", False):
            continuation_token = response.get("NextContinuationToken")
            response = self.client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
                ContinuationToken=continuation_token,
            )
            contents.extend(
                list(
                    filter(
                        lambda x: any(
                            [x.get("Key").endswith(suffix) for suffix in suffixes]
                            + [not suffixes]
                        ),
                        response.get("Contents", []),
                    )
                )
            )
        contents = list(filter(lambda x: not x.get("Key").endswith("/"), contents))

        return contents

    def get_obj(self, key):
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def put_json(self, json_data, key):
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(json_data, ensure_ascii=False).encode(),
        )

    def upload_file(self, file, key):
        self.client.upload_file(file, self.bucket, key)


# =========================================================OBS========================================================
class ObsPath:
    def __init__(self, obs_path):
        obs_path = obs_path.strip()
        assert obs_path.startswith("obs://"), "路径必须以obs://开始"
        assert obs_path.endswith("/"), "路径必须以/结束"
        self.bucket_name = obs_path.replace("obs://", "").split("/")[0]
        self.obs_rel_path = "/".join(obs_path.replace("obs://", "").split("/")[1:])


class OBS_API:
    def __init__(self, bucket_name, ak, sk, server):
        self.bucket_name = bucket_name
        self.client = ObsClient(access_key_id=ak, secret_access_key=sk, server=server)

    def list_bucket_files_deep(self, obs_path, suffix='', with_bucket_name=False):
        if obs_path.endswith("/") == False:
            obs_path = obs_path + "/"
        path_list = []
        ignore_list = []
        result = self.client.listObjects(self.bucket_name, prefix=obs_path)
        for content in result.body.contents:
            key = content.key
            if key.endswith("/") == False and key != obs_path and key.endswith(suffix):
                basename = key.split("/")[-1]
                if basename.startswith((".", "~")):
                    ignore_list.append(key)
                else:
                    path_list.append(key)
        if len(ignore_list) != 0:
            print(f"!请注意:{obs_path}下已自动忽略文件: {ignore_list}")
        if with_bucket_name == True:
            return [f"/{self.bucket_name}/" + x for x in path_list]
        elif with_bucket_name == False:
            return path_list
        else:
            raise Exception("obs api with_bucket_name定义错误")

    def list_bucket_current(self, obs_path, list_type, suffix='', full_path=True):
        if obs_path.endswith("/") == False:
            obs_path = obs_path + "/"
        if list_type == 'folder':
            result = self.client.listObjects(self.bucket_name, prefix=obs_path, delimiter='/')
            fd_list = [commonPrefixs.prefix for commonPrefixs in result.body.commonPrefixs]
            if full_path == True:
                return fd_list
            elif full_path == False:
                return [os.path.basename(x[:-1]) for x in fd_list]
            else:
                raise Exception("obs api参数定义错误")
        elif list_type == 'file':
            path_list = []
            ignore_list = []
            max_key = 1000
            next_marker = ''
            while True:
                resp = self.client.listObjects(self.bucket_name, prefix=obs_path, max_keys=max_key, marker=next_marker,
                                               delimiter='/')
                for content in resp.body.contents:
                    key = content.key
                    if key.endswith("/") == False and key != obs_path and key.endswith(suffix):
                        basename = key.split("/")[-1]
                        if basename.startswith((".", "~")):
                            ignore_list.append(key)
                        else:
                            path_list.append(key)
                if not resp.body.is_truncated:
                    break
                next_marker = resp.body.next_marker

            if len(ignore_list) != 0:
                print(f"!请注意:{obs_path}下已自动忽略文件: {ignore_list}")
            return path_list


# =========================================================OSS========================================================
class OssPath:
    def __init__(self, oss_path):
        oss_path = oss_path.strip()
        assert oss_path.startswith("oss://"), "路径必须以oss://开始"
        assert oss_path.endswith("/"), "路径必须以/结束"
        self.bucket_name = oss_path.replace("oss://", "").split("/")[0]
        self.oss_rel_path = "/".join(oss_path.replace("oss://", "").split("/")[1:])


class OSS_API:
    def __init__(self, bucket_name, OSS_AK, OSS_SK, OSS_REGION, time_out=60):
        self.bucket_name = bucket_name
        self.auth = oss2.Auth(OSS_AK, OSS_SK)
        self.bucket = oss2.Bucket(self.auth, OSS_REGION, bucket_name, connect_timeout=time_out)

    def list_bucket_files_deep(self, oss_path, suffix='', with_bucket_name=False):
        ### 忽略临时文件和隐藏文件,忽略文件夹
        if oss_path.endswith("/") == False:
            oss_path = oss_path + "/"

        path_list = []
        ignore_list = []
        for obj in oss2.ObjectIterator(self.bucket, prefix=oss_path):
            if obj.key.endswith("/") == False and obj.key != oss_path and obj.key.endswith(suffix):
                basename = obj.key.split("/")[-1]
                if basename.startswith((".", "~")):
                    ignore_list.append((obj.key))
                else:
                    path_list.append(obj.key)

        if len(ignore_list) != 0:
            print(f"!请注意:{oss_path}下已自动忽略文件: {ignore_list}")

        if with_bucket_name == True:
            return [f"/{self.bucket_name}/" + x for x in path_list]
        elif with_bucket_name == False:
            return path_list
        else:
            raise Exception("oss api with_bucket_name定义错误")

    def list_bucket_current(self, oss_path, list_type, suffix='', full_path=True):  ### suffix只有list_type是文件的时候才生效
        ### list_type 是 folder或者file
        if oss_path.endswith("/") == False:
            oss_path = oss_path + "/"
        if list_type == 'folder':
            fd_list = [obj.key for obj in oss2.ObjectIterator(self.bucket, prefix=oss_path, delimiter='/') if
                       obj.key.endswith("/") == True and obj.key != oss_path]
            if full_path == True:
                return fd_list
            elif full_path == False:
                ##截取调最后的/再
                return [os.path.basename(x[:-1]) for x in fd_list]
            else:
                raise Exception("oss api参数定义错误")
        elif list_type == 'file':
            path_list = []
            ignore_list = []
            for obj in oss2.ObjectIterator(self.bucket, prefix=oss_path, delimiter='/'):  ## 只遍历当前文件夹
                if obj.key.endswith("/") == False and obj.key != oss_path and obj.key.endswith(suffix):
                    basename = obj.key.split("/")[-1]
                    if basename.startswith((".", "~")):
                        ignore_list.append((obj.key))
                    else:
                        path_list.append(obj.key)

            if len(ignore_list) != 0:
                print(f"!请注意:{oss_path}下已自动忽略文件: {ignore_list}")
            return path_list

    def save_to_oss_url(self, bytes_data, oss_path, prefix_url, force=False):
        ### 检查文件是否已存在
        if force == False:
            if self.bucket.object_exists(oss_path) == True:
                raise Exception("文件已存在请确认")

        ### 写入文件
        rs = self.bucket.put_object(oss_path, bytes_data)
        if rs.status != 200:
            raise Exception("OSS数据写入失败")

        url = prefix_url + quote(oss_path)
        og_url = prefix_url + oss_path

        return url, og_url
