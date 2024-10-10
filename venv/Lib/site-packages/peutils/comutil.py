# -*- coding: UTF-8 -*-

'''
Author: Henry Wang
Date: 2021-03-05 15:53
Short Description:

Change History:

'''

import logging
from logging import handlers


class Logger(object):
    level_relations = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }  # 日志级别关系映射

    def __init__(self, filename, level='info', when='D', backCount=5,
                 fmt='%(asctime)s %(levelname)s || Message:%(message)s'):
        self.logger = logging.getLogger(filename)
        format_str = logging.Formatter(fmt)  # 设置日志格式
        self.logger.setLevel(self.level_relations.get(level))  # 设置日志级别
        # sh = logging.StreamHandler()#往屏幕上输出
        # sh.setFormatter(format_str) #设置屏幕上显示的格式
        th = handlers.TimedRotatingFileHandler(filename=filename, when=when, backupCount=backCount,
                                               encoding='utf-8')  # 往文件里写入#指定间隔时间自动生成文件的处理器
        # 实例化TimedRotatingFileHandler
        # interval是时间间隔，backupCount是备份文件的个数，如果超过这个个数，就会自动删除，when是间隔的时间单位，单位有以下几种：
        # S 秒
        # M 分
        # H 小时、
        # D 天、
        # W 每星期（interval==0时代表星期一）
        # midnight 每天凌晨
        th.setFormatter(format_str)  # 设置文件里写入的格式
        # self.logger.addHandler(sh) #把对象加到logger里
        self.logger.addHandler(th)


'''
# how to use logger

if __name__ == '__main__':
    infolog = Logger('all.log',level='debug').logger
    infolog.debug('debug')
    infolog.info('info')
    infolog.warning('警告')
    infolog.error('报错')
    infolog.critical('严重')
    
'''




import oss2
from .fileutil import list_files_deep
import os
class OSS_Class():
    def __init__(self, oss_path, ak, sk, ossBucket='projecteng', ossurl='http://oss-cn-shanghai.aliyuncs.com'):
        self.ak = ak
        self.sk = sk
        self.bucketName = ossBucket
        self.ossurl = ossurl
        self.oss_path = oss_path.strip()
        self.bucket = self.get_bucket()
    def get_bucket(self):
        print(f"当前空间地址:{self.oss_path}")
        auth = oss2.Auth(self.ak, self.sk)
        bucket = oss2.Bucket(auth, self.ossurl, self.bucketName)
        assert self.oss_path[0] not in ('/', "\\"), "路径第一位不需要'/';"
        assert self.oss_path[-1] == '/', "路径最后一位必须携带'/' "
        return bucket

    def get_current_folders(self):
        folders = []
        for obj in oss2.ObjectIterator(self.bucket,prefix=self.oss_path, delimiter = '/'):
            # print(obj)
            if obj.is_prefix():  # 判断obj为文件夹。
                folders.append(obj.key)
        return folders

    def get_bucket_filenames(self, suffix=''):
        all_names = [obj.key for obj in oss2.ObjectIterator(self.bucket, prefix=self.oss_path) if
                     obj.key.endswith(suffix)]
        if self.oss_path in all_names:
            all_names.remove(self.oss_path)
        # print(all_names)
        return all_names
    def downloadFile(self,filePath,saveFolder):
        # filePath 输入相对路径
        targetPath = self.oss_path + filePath.replace("\\", "/")
        self.bucket.get_object_to_file(targetPath,os.path.join(saveFolder, filePath))
        print(filePath+'download success')
    def deleteFile(self, files,headers=None):
        self.bucket.batch_delete_objects(files, headers)

    def upload_by_local_filename(self,local_file):
        base_name = os.path.basename(local_file)
        r= self.bucket.put_object_from_file(self.oss_path+base_name,local_file)
        if r.status != 200:
            raise Exception(f'oss返回状态不等于200 {r.status}')

    def upload_by_local_path(self, local_file_path, suffix='', log=None):
        # 检查前先提示，如果路径下的内容不为空，提示
        # 可接收消息队列，返回形式为列表[str,color]
        origin_filenames = self.get_bucket_filenames(suffix=suffix)
        if len(origin_filenames) != 0:
            print(f'Warning 当前目录不为空，已有 {len(origin_filenames)} 条数据，请确认！{origin_filenames}')
            if log: log(f'Warning 当前目录不为空，已有 {len(origin_filenames)} 条数据，请确认！{origin_filenames}', '#D4AF37')

        local_files = list_files_deep(local_file_path, suffix=suffix)
        target_files = [self.oss_path + os.path.relpath(x, start=local_file_path).replace("\\", "/") for x in
                        local_files]
        # print(local_files)
        # print(target_files)
        file_pares = zip(target_files, local_files)
        print(f"正在上传，请稍等 待上传总文件数:{len(local_files)}  上传后缀{suffix}")
        if log: log(f"正在上传，请稍等 待上传总文件数:{len(local_files)}  上传后缀{suffix}", "green")
        fileLength = len(local_files)
        for file_p,count in zip(file_pares,range(1,len(target_files)+1)):
            try:
                r = self.bucket.put_object_from_file(*file_p)
                if r.status != 200:
                    raise Exception(f'状态不等于200 {r.status}')

            except Exception as e:
                # print(file_p[0])
                print(e)
            print("上传进度:"+str(count)+'/'+str(fileLength))
            if log: log("上传进度:"+str(count)+'/'+str(fileLength), "green", "progressBar")
        print('上传完成，检查中，请稍等..')
        if log: log('上传完成，检查中，请稍等..', "green")

        uploaded = self.get_bucket_filenames(suffix=suffix)
        # checked = set(uploaded) ^ set(target_files)

        if len(origin_filenames) + len(local_files) != len(uploaded):
            print("\033[0;32;40m请注意！存在被覆盖图片\033[0m")
            if log: log("\033[0;32;40m请注意！存在被覆盖图片\033[0m", "#D4AF37")
        else:
            print(f"检查完毕，上传完成，上传总数量 {len(local_files)}")
            if log: log(f"检查完毕，上传完成，上传总数量 {len(local_files)}", "green")

    def set_obj_meta_and_check(self, suffix, meta_header, log=None):
        # 可接收消息队列，返回形式为列表[str,color]
        print(f"即将更新meta信息,后缀{suffix} {meta_header}")
        if log: log(f"即将更新meta信息,后缀{suffix} {meta_header}", "green")
        files = self.get_bucket_filenames(suffix)
        if len(files) != 0:
            print(f"发现 {suffix}文件数量： {len(files)},准备更新，执行过程可能较长，请耐心等待")
            if log: log(f"发现 {suffix}文件数量： {len(files)},准备更新，执行过程可能较长，请耐心等待", "green")
            fileLength = len(files)
            for count,filename in enumerate(files):
                self.bucket.update_object_meta(filename, headers=meta_header)
                print("更新进度:" + str(count) + '/' + str(fileLength))
                if log: log("更新进度:" + str(count+1) + '/' + str(fileLength), "green", "progressBar")
            print('更新完成 ,请进一步检查是否设置完整...')
            if log: log('更新完成 ,正在进一步检查是否设置完整...', "green")

            ### 执行检查过程
            error_files = []
            for count, filename in enumerate(files):
                meta = self.bucket.head_object(filename)
                metaheader = {k: v for k, v in meta.headers.items() if k in meta_header.keys()}
                if metaheader != meta_header:
                    error_files.append(filename)
                if log: log("检查进度:" + str(count+1) + '/' + str(fileLength), "green", "progressBar")
            if len(error_files) == 0:
                print("数据检查完毕，未发现问题")
                if log: log("数据检查完毕，未发现问题", "green")
            else:
                print(f"发现异常数据：{error_files}")
                if log: log(f"发现异常数据：{error_files}", "red")
        else:
            print(f"未发现{suffix}后缀文件")
            if log: log(f"未发现{suffix}后缀文件", "green")