# -*- coding: UTF-8 -*-

'''
Author: Henry Wang
Date: 2020-11-10 16:41
Short Description:

Change History:

'''

### 解压文件
def unzipfile(zip_file_path):
    import zipfile
    import os
    dir_name = os.path.dirname(zip_file_path)
    with zipfile.ZipFile(zip_file_path, 'r') as z:
        for x in z.filelist:
            if x.filename.split("/")[-1].startswith('.')==False:
                z.extract(x.filename, dir_name)
    return dir_name


### 指定输出路径和列表，打包路径
def packzipfile(outpath,pack_name_list):
    import zipfile
    import os
    with zipfile.ZipFile(outpath, 'w') as myzip:
        for fname in pack_name_list:
            myzip.write(fname,os.path.basename(fname))



from argparse import ArgumentParser,FileType
import zipfile
import sys
import os
from .fileutil import list_files_deep
from pathlib import Path


'''
支持单个压缩包文件中存放单种类型的文件(不支持zip种存放zip)
支持文件逐一处理

def process_func(filename,**kw):
    print(filename,kw)
    print(kw["arg1"],kw["choicearg2"],kw["optionarg"])

other_params ={
    "arg1":{
        "help":"arg1",
        "type":str,
    },
    "choicearg2":{
        "help":"i am a choice",
        "choices":["a","b","c"],

    },
    "-optionarg":{
        "help":"option args",
        "type":str
    },
}

h = WooeyBaseZipFileiHander("test template with zip class",".csv",process_func=process_func,other_params=other_params)


'''


class WooeyBaseZipHandlerFile():
    '''
    project_desc: str
    need_process_suffix : str
    process_func function
    other_params a list like {"arganeme":{}} if name start with -- means option param
    {
        "arg1":{
            "help:"arg help", #not empty
            "type":int ,# not empty when it not choices.
            "default":'', #option
            "choices":['a','b','c'] #option

        },
        "--arg2":{}, option arg2
        ...
    }
    ##
    '''
    def __init__(self,project_desc,need_process_suffix,process_func,other_params=None,chinese_filename_transcoding=False,chinese_filename_target_encoding_format='gbk'):
        self.project_desc=project_desc
        self.need_process_suffix = need_process_suffix
        self.process_func = process_func
        self.other_params = other_params
        self.chinese_filename_transcoding=chinese_filename_transcoding
        self.chinese_filename_target_encoding_format=chinese_filename_target_encoding_format

    def main(self):
        parser = ArgumentParser(description=self.project_desc)
        parser.add_argument('inputfile', help='Upload your file can be sigle file or a zipfile include mutifiles',
                            type=FileType('r'))
        if self.other_params:
            for k,v in self.other_params.items():
                parser.add_argument(k,**v)

        args = parser.parse_args()
        filename = args.inputfile.name
        assert self.need_process_suffix.endswith(".zip")==False,"内容文件不能是zip格式"

        # add other param
        users_param = {}
        if self.other_params:
            for k,v in self.other_params.items():
                # 移除非必须参数前面的-
                users_param[k] = getattr(args,k.lstrip("-") )


        if filename.endswith(self.need_process_suffix):
            self.process_func(filename,**users_param)

        elif filename.endswith(".zip"):
            print("ready to extract file")
            dir_name = os.path.dirname(filename)
            with zipfile.ZipFile(filename, 'r') as z:
                z.extractall(path=dir_name)
            print("extract finish... ready to process")
            # 解压完成后，读取文件
            files = list_files_deep(dir_name, suffix=self.need_process_suffix)
            print(f"发现待处理文件{len(files)}")

            if self.chinese_filename_transcoding:
                for f in files:
                    try:
                        f_name=os.path.basename(f)
                        f_dirname=os.path.dirname(f)
                        f_path=Path(f)
                        f_path.rename(os.path.join(f_dirname, f_name.encode('cp437').decode(self.chinese_filename_target_encoding_format)))
                    except Exception as e:
                        print('-' * 30)
                        print(f'文件名<{os.path.basename(f)}>转码失败，跳过')
                        print(e)
                        print('-' * 30)
                        continue
                files = list_files_deep(dir_name, suffix=self.need_process_suffix)


            for file in files:
                print(f"process file {file}")
                self.process_func(file,**users_param)
        else:
            raise Exception(f"file name suffix not endswith {self.need_process_suffix} or not zipfile")

'''
支持单个压缩包文件中存放单种类型的文件(不支持zip种存放zip)
文件批量读取后一起处理

def process_func(filelists,**kw):
    pass
'''

class WooeyBaseZipHandlerFileList():
    def __init__(self, project_desc, need_process_suffix, process_func, other_params=None):
        self.project_desc = project_desc
        self.need_process_suffix = need_process_suffix
        self.process_func = process_func
        self.other_params = other_params

    def main(self):
        parser = ArgumentParser(description=self.project_desc)
        parser.add_argument('inputfile', help='Upload your file can be sigle file or a zipfile include mutifiles',
                            type=FileType('r'))
        if self.other_params:
            for k, v in self.other_params.items():
                parser.add_argument(k, **v)

        args = parser.parse_args()
        filename = args.inputfile.name
        assert self.need_process_suffix.endswith(".zip") == False, "内容文件不能是zip格式"

        # add other param
        users_param = {}
        if self.other_params:
            for k, v in self.other_params.items():
                # 移除非必须参数前面的-
                users_param[k] = getattr(args, k.lstrip("-"))

        if filename.endswith(self.need_process_suffix):
            self.process_func([filename], **users_param)  ### 这里转变成列表

        elif filename.endswith(".zip"):
            print("ready to extract file")
            dir_name = os.path.dirname(filename)
            with zipfile.ZipFile(filename, 'r') as z:
                z.extractall(path=dir_name)
            print("extract finish... ready to process")
            # 解压完成后，读取文件
            files = list_files_deep(dir_name, suffix=self.need_process_suffix)
            print(f"发现待处理文件{len(files)}")

            self.process_func(files,**users_param)  ## 这里传入多个文件

        else:
            raise Exception(f"file name suffix not endswith {self.need_process_suffix} or not zipfile")

