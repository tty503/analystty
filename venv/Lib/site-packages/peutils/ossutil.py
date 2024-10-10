# -*- coding: UTF-8 -*-

"""
Author: Henry.Wang
Date: 2023-11-02 14:30
Short Description:

Change History:

"""

from peutils.textutil import get_device_sn,parse_info_from_token
import platform
import requests
import warnings
import oss2
from oss2.models import PartInfo
from oss2 import determine_part_size

import os



sys_kind = platform.system()




# 权限re_up或者read
def get_oss_auth_str(oss_path,auth_type="read",is_print=True):
    headers = {
        'Content-Type': 'application/json'
    }

    payload = {
        "oss_path":oss_path,
        "auth_type": auth_type
    }
    try:


        if sys_kind == "Linux":
            url = "https://dataflow.appen.com.cn/oss_auth/other/oss_auth_from_vpc/"
        else:
            url = "https://dataflow.appen.com.cn/oss_auth/other/oss_auth_from_debug/"
            payload["sn_no"] = get_device_sn()

        r = requests.post(url=url, json=payload,headers=headers)

        if r.status_code == 403:
            ip_info = requests.get("https://jsonip.com").json().get("ip")
            raise Exception( f"{url.split('/')[-2]} 当前未开通白名单 {ip_info}")
        else:
            data = r.json()
            if data["code"] != 200:
                raise Exception(f"授权接口调用失败，具体原因:{data['message']}")
            auth_str = data["data"]["auth_str"]
            if is_print is True:
                print(f"请复制下方的授权码，使用oss登陆,授权码将在12小时后过期，请尽快使用!")
                print(auth_str)
            # auth_dict = parse_info_from_token(auth_str)
            return auth_str

    except Exception as e:
        raise Exception(f"授权接口调用异常，请稍后重试!{e}")


def get_long_object_link(auth_str,bucket_name,file_key,duration=604800):
    headers = {
        'Content-Type': 'application/json'
    }

    payload = {
        "authToken": auth_str,
        "filePath": file_key,
        "bucketName":bucket_name,
        "expiration":duration,
    }

    try:
        r = requests.post(url="https://dataflow.appen.com.cn/oss_app/other/get_oss_file_url/", json=payload,headers=headers)
        print(r.text)
        rsp = r.json()
        if rsp["code"] != 200:
            raise Exception(rsp["message"])
        else:
            return rsp["data"]["url"]


    except Exception as e:
        # print(e)
        raise Exception(f"授权接口调用异常，请稍后重试!{e}")





class OSS_STS_API():
    def __init__(self,bucket_name, time_out=60,region=None):
        oss_path = f"oss://{bucket_name}/"
        self.auth_str = get_oss_auth_str(oss_path,auth_type="re_up",is_print=False)
        self.auth_dict = parse_info_from_token(self.auth_str)
        self.bucket_name = bucket_name
        self.auth = oss2.StsAuth(self.auth_dict["id"],self.auth_dict["secret"],self.auth_dict["stoken"])
        self.short_region = self.auth_dict['region'] # 比如 oss-cn-shanghai

        # 未指定region情况下，根据操作系统来默认
        if region is None:
            if sys_kind == "Linux":
                region = f"http://{self.short_region}-internal.aliyuncs.com"
            else:
                region = f"http://{self.short_region}.aliyuncs.com"
        else:
            region = region

        self.region= region
        self.bucket = oss2.Bucket(self.auth, region, bucket_name,connect_timeout=time_out)

    def check_is_empty_oss_folder(self,oss_key):
        assert oss_key.endswith("/") is True, "oss_key必须以/结尾"
        assert oss_key.startswith("/") is False, "oss_key不能以/开始"
        is_empty = True
        count = 1
        for obj in oss2.ObjectIterator(self.bucket, prefix=oss_key):
            # print("key",obj.key)
            if count > 2:
                break
            if obj.key != oss_key:
                is_empty = False
            count += 1

        return is_empty

    def list_bucket_files_deep(self, oss_path, suffix='',with_bucket_name=False):
        ### 忽略临时文件和隐藏文件,忽略文件夹
        if oss_path.endswith("/") ==False:
            oss_path = oss_path+"/"

        path_list = []
        ignore_list = []
        for obj in oss2.ObjectIterator(self.bucket, prefix=oss_path):
            if obj.key.endswith("/")==False and obj.key!=oss_path and obj.key.endswith(suffix):
                basename =obj.key.split("/")[-1]
                if basename.startswith((".","~")):
                    ignore_list.append((obj.key))
                else:
                    path_list.append(obj.key)

        if len(ignore_list)!=0:
            print(f"!请注意:{oss_path}下已自动忽略文件: {ignore_list}")

        if with_bucket_name ==True:
            return [ f"/{self.bucket_name}/"+x  for x in path_list]
        elif with_bucket_name ==False:
            return path_list
        else:
            raise Exception("oss api with_bucket_name定义错误")

    def list_bucket_folders_deep(self, oss_path,with_bucket_name=False):
        if oss_path.endswith("/") ==False:
            oss_path = oss_path+"/"

        path_list = []
        for obj in oss2.ObjectIterator(self.bucket, prefix=oss_path):
            if obj.key.endswith("/") and obj.key!=oss_path:
                # 获取当前目录下所有的目录
                fd_list = self.list_bucket_current(oss_path=obj.key, list_type="folder")
                if len(fd_list) == 0:
                    path_list.append(obj.key)
        assert len(path_list) == len(set(path_list)), "folder出现重复"

        if with_bucket_name ==True:
            return [f"/{self.bucket_name}/"+x for x in path_list]
        elif with_bucket_name ==False:
            return path_list
        else:
            raise Exception("oss api with_bucket_name定义错误")


    def list_bucket_current(self, oss_path,list_type,suffix='',full_path=True):  ### suffix只有list_type是文件的时候才生效
        ### list_type 是 folder或者file
        if oss_path.endswith("/") == False:
            oss_path = oss_path + "/"
        if list_type =='folder':
            fd_list =  [obj.key for obj in oss2.ObjectIterator(self.bucket,prefix=oss_path, delimiter= '/') if obj.key.endswith("/")==True and obj.key!=oss_path]
            if full_path ==True:
                return fd_list
            elif full_path==False:
                ##截取调最后的/再
                return [os.path.basename(x[:-1]) for x in fd_list]
            else:
                raise Exception("oss api参数定义错误")
        elif list_type =='file':
            path_list = []
            ignore_list = []
            for obj in  oss2.ObjectIterator(self.bucket, prefix=oss_path, delimiter='/'):## 只遍历当前文件夹
                if obj.key.endswith("/")==False and obj.key != oss_path and obj.key.endswith(suffix):
                    basename = obj.key.split("/")[-1]
                    if basename.startswith((".", "~")):
                        ignore_list.append((obj.key))
                    else:
                        path_list.append(obj.key)

            if len(ignore_list) != 0:
                print(f"!请注意:{oss_path}下已自动忽略文件: {ignore_list}")
            return path_list


    # meta_header {'Content-Type': 'image/jpg', "Content-Disposition": "inline", "Cache-Control": "no-cache"}
    # meta_header设置为空 {}
    def set_obj_meta(self,filename_list,meta_header):
        print(f"即将更新meta信息 {meta_header} ,文件数量{len(filename_list)},过程可能较长")
        for fl in filename_list:
            self.bucket.update_object_meta(fl,headers=meta_header)
        print('meta信息更新完成.')

    # def save_to_oss_url(self, bytes_data, oss_path=None, suffix_type=None, force=False):
    #     '''返回url'''
    #     if oss_path is None:
    #         if suffix_type is None:
    #             raise Exception("路径不指定的情况，必须指定后缀类型")
    #         elif not suffix_type.startswith("."):
    #             raise Exception("后缀必须以.结尾")
    #         else:
    #             oss_path = f"upload_url/{gen_uuid()}/{gen_uuid()}{suffix_type}"
    #
    #     ### 检查文件是否已存在
    #     if force == False:
    #         if self.bucket.object_exists(oss_path) is True:
    #             raise Exception("文件已存在请确认")
    #
    #     ### 写入文件
    #     rs = self.bucket.put_object(oss_path, bytes_data)
    #     if rs.status != 200:
    #         raise Exception("OSS数据写入失败")
    #
    #     prefix_url = f"https://{self.bucket_name}.oss-cn-shanghai.aliyuncs.com/"
    #     url = prefix_url + quote(oss_path)
    #     og_url = prefix_url + oss_path
    #
    #     return url, og_url


    def copy_big_file(self, src_key, dest_key, src_bucket_name):
        """
        复制大于1G的文件
        ！！！注意 初始化的bucket 应该是 复制文件的目标bucket
        参考 https://help.aliyun.com/document_detail/88465.html
        @param src_key: 原始文件key
        @param dest_key: 目标文件key
        @param src_bucket_name: 原始文件bucket name
        @return: status code
        """

        if src_bucket_name == self.bucket_name:
            src_bucket = self.bucket
        else:
            src_bucket = oss2.Bucket(self.auth, self.region, src_bucket_name)

        # 获取要复制的文件size
        head_info = src_bucket.head_object(src_key)
        total_size = head_info.content_length

        # determine_part_size方法用来确定分片大小。
        part_size = determine_part_size(total_size, preferred_size=100 * 1024)

        # 初始化分片。
        upload_id = self.bucket.init_multipart_upload(dest_key).upload_id
        parts = []

        # 逐个上传分片。
        part_number = 1
        offset = 0
        while offset < total_size:
            num_to_upload = min(part_size, total_size - offset)
            end = offset + num_to_upload - 1
            # headers = dict()
            # 指定拷贝的源地址。
            # headers[OSS_COPY_OBJECT_SOURCE] = '/example-bucket-by-util/recode-test.txt'
            # 指定源Object的拷贝范围。例如设置bytes=0~1023，表示拷贝1~1024字节的内容。
            # headers[OSS_COPY_OBJECT_SOURCE_RANGE] = 'bytes=0~1023'
            # 如果源Object的ETag值和您提供的ETag相等，则执行拷贝操作，并返回200 OK。
            # headers['x-oss-copy-source-if-match'] = '5B3C1A2E053D763E1B002CC6****'
            # 如果源Object的ETag值和您提供的ETag不相等，则执行拷贝操作，并返回200 OK。
            # headers['x-oss-copy-source-if-none-match'] = '5B3C1A2E053D763E1B002CC6****'
            # 如果指定的时间等于或者晚于文件实际修改时间，则正常拷贝文件，并返回200 OK。
            # headers['x-oss-copy-source-if-unmodified-since'] = '2021-12-09T07:01:56.000Z'
            # 如果指定的时间早于文件实际修改时间，则正常拷贝文件，并返回200 OK。
            # headers['x-oss-copy-source-if-modified-since'] = '2021-12-09T07:01:56.000Z'
            # result = bucket.upload_part_copy(src_bucket_name, src_object_name, (offset, end), dest_object_name, upload_id, part_number, headers=headers)

            result = self.bucket.upload_part_copy(src_bucket_name, src_key, (offset, end), dest_key,
                                                  upload_id, part_number)
            # 保存part信息。
            parts.append(PartInfo(part_number, result.etag))

            offset += num_to_upload
            part_number += 1

        # 完成分片拷贝。
        result = self.bucket.complete_multipart_upload(dest_key, upload_id, parts)

        # 获取文件元信息。
        head_info = self.bucket.head_object(dest_key)

        # 查看目标Object大小。
        dest_object_size = head_info.content_length

        # 对比源Object和目标Object的大小。
        assert dest_object_size == total_size

        return result.status
