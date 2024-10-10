# -*- coding: UTF-8 -*-

'''
Author: Henry Wang
Date: 2022-06-02 22:12
Short Description:

Change History:

'''


from abc import ABC,abstractmethod
# import uuid
import os,sys
import json
import traceback
from peutils.transform.v1.base import ErrorMsgLogV1,gen_format_progress_seq,deco_execution_time
import pandas as pd
from concurrent import futures
from peutils.textutil import gen_uuid



## 单条数据的处理基类，可能是连续帧
class AbstractTask(ABC):

    def __init__(self,row,users_param=None):
        self.row= row # 原始csv这一行的数据
        self.users_param = users_param if users_param is not None else {} # 前端用户的参数
        self.log = ErrorMsgLogV1()  # 这行的所有错误
        # self.parse_obj = parse_cls(row["annotation"],config=config)

    @property
    def row_flag(self):
        if len(self.log.error_list)>0:
            return 0
        else:
            return 1

    @abstractmethod
    def check_row_on_a9(self)->None:
        """a9只能通过annotation进行检查 将内容输出到log"""

    @abstractmethod
    def check_row_addtional(self)->None:
        """额外的内容检查 将内容输出到log """

    def check_row_func(self,check_mode="all"): #check分a9的
        if self.log is None or isinstance(self.log,ErrorMsgLogV1) ==False:
            raise Exception("请定义log 并且使用ErrorMsgLog的实例")
        else:
            ### 将自带错误的解析方法放过去这个错误的方法
            # self.log.error_list.extend(self.parse_obj.check_frames_error())

            if check_mode=="a9_check":
                self.check_row_on_a9()
                return self.log.error_list  ##直接返回对象
            elif check_mode == "all":
                self.check_row_on_a9()
                self.check_row_addtional()
                return self.log.error_list ##做格式化
            else:
                raise Exception("未定义的check mode")


    @abstractmethod
    def parse_row_func(self)->None:
        """实现自定义的 parse_row_func方法  相当于单条数据的main函数"""



# def get_temp_path(by="nas"): # nas,oss
#
#     # 返回 需要授权的路径
#     pass

### 写一个方法，这个方法负责处理单行数据的逻辑
### csv所有的数据生成队列，按照并发去处理和完成，将所有的错误结果搜集，最后打印错误信息，并且输出到文件。
### 进度条功能
### OSS数据保存的功能

class CommonTaskV1():
    def __init__(self,row_cls:type,max_worker=16):
        self.RowTask = row_cls
        # self.parse_cls = parse_cls
        # self.config = config
        self.max_worker = max_worker
        self.format_progress = lambda: None


    def process_unit(self,row,users_param):
        row_task = self.RowTask(row=row,users_param=users_param)
        ## 执行检查逻辑,将错误输出到log

        ###执行方法,捕捉未知错误
        try:
            row_task.check_row_func()
            row_task.parse_row_func()
        except Exception as e:
            row_task.log.create_error(msg=repr(e))

        ### 这行所有错误的集合
        errors = row_task.log.fomart_error_str()

        return row_task.row_flag, row, errors

    ### 单个文件的处理
    @deco_execution_time
    def process_file(self,file,user_kw):
        ### 创建实例
        # row_task = self.RowTask(file=file,row_dict=)

        task_df = pd.read_csv(file,encoding='utf-8-sig')
        self.format_progress = gen_format_progress_seq(total=len(task_df), split_part=10)
        header = task_df.columns

        df_error = pd.DataFrame(columns=["errors",*header])
        # task_df = pd.DataFrame(columns=["col1", "col2"],
        #                        data=[{"col1": 1, "col2": "a"}, {"col1": 2, "col2": "b"},
        #                              {"col1": 3, "col2": "c"}, {"col1": 4, "col2": "d"}])

        with futures.ThreadPoolExecutor(min(self.max_worker, len(task_df))) as executor:

            tasks = [executor.submit(self.process_unit, row=row, users_param=user_kw) for _, row in task_df.iterrows()]

            for future in futures.as_completed(tasks):
                row_flag, row, errors, = future.result()  # flag 1代表是成功，0代表失败，失败后所有的数据，写入csv
                self.format_progress()
                if row_flag == 0:
                    df_error = df_error.append({"errors":errors,**row,},ignore_index=True)

            if len(df_error)>0:
                print(f"{file} 发现异常{len(df_error)}，请检查输出文件中的异常明细", file=sys.stderr)
                df_error.to_csv(f"error_{gen_uuid()}_{'.'.join(os.path.basename(file).split('.')[:-1])}.csv",index=False,encoding="utf-8-sig")
                # df_error.to_csv()


    ## process 方法的入口
    @deco_execution_time
    def process_func(self,files,**user_kw):

        if isinstance(files,list) == True:
            for file in files:
                self.process_file(file,user_kw)
        else:
            self.process_file(files,user_kw)





