# -*- coding: UTF-8 -*-

"""
Author: Henry Wang
Date: 2022/10/13 11:22 AM
Short Description:

Change History:

继承这个类
补充自己的detail 方法
继承这个类，并且实现自己的方法如果是加明细字段，那么

"""
from abc import ABC, abstractmethod
import pandas as pd
from peutils.transform.v1.base import ErrorMsgLogV1, gen_format_progress_seq, deco_execution_time
from typing import List, Optional, Union
from concurrent import futures
import os, sys
from peutils.textutil import gen_uuid


class AbstractReportRow(ABC):
    def __init__(self, idx, row, users_param=None):
        self.log = ErrorMsgLogV1()
        self.idx = idx
        self.row = row
        self.users_param = users_param

    @property
    def row_flag(self):
        if len(self.log.error_list) > 0:
            return 0
        else:
            return 1

    def run_fields(self):
        for i in dir(self):
            if i.startswith("add_col_"):
                field_name = "".join(i.split("add_col_")[-1:])
                if field_name in self.row:
                    # print(field_name)
                    raise Exception(f"{field_name}已经存在当前的行中,名称冲突!")
                else:
                    try:
                        func = getattr(self, i)
                        # 保存这个列的结果
                        self.row[field_name] = func()
                    except Exception as e:
                        self.log.create_error(msg=f"运行错误: {e}")


class SummaryConfig(object):
    def __init__(self, name, group_fields: List[str], agg_fields: List[str],
                 agg_methods: Union[List[str], None] = None):
        self.name = name
        # 根据什么来聚合

        self.group_fields = group_fields
        # 聚合哪些字段
        self.agg_fields = list(set(group_fields + agg_fields))
        # 聚合方法,如果不提供默认sum
        if agg_methods is None:
            self.agg_methods = ["sum"]
        else:
            self.agg_methods = agg_methods


class ReportTaskV1(object):
    def __init__(self, row_cls: type, summary_config: Union[List[SummaryConfig], None] = None, max_worker=16):
        self.RowReport = row_cls
        self.summary_config = summary_config
        self.max_worker = max_worker
        self.format_progress = lambda: None

    def process_unit(self, idx, row, users_param):
        row_task = self.RowReport(idx=idx, row=row, users_param=users_param)
        # 执行检查逻辑,将错误输出到log 执行方法,捕捉未知错误
        try:
            row_task.run_fields()  # !重要生成对应的字段到line的row中
        except Exception as e:
            row_task.log.create_error(msg=repr(e))

        # 这行所有错误的集合
        errors = row_task.log.fomart_error_str()
        return row_task.row_flag, row, errors

    # 单个文件的处理
    @deco_execution_time
    def process_file(self, file, user_kw):
        """
        第一步 先跑明细
        第二步 按照配置生成汇总报表(如果有的话)
        """
        task_df = pd.read_csv(file, encoding='utf-8-sig')
        self.format_progress = gen_format_progress_seq(total=len(task_df), split_part=10)
        header = task_df.columns
        df_error = pd.DataFrame(columns=["errors", *header])  # 带错误的结果信息
        df_out = pd.DataFrame(columns=[*header])

        with futures.ThreadPoolExecutor(min(self.max_worker, len(task_df))) as executor:
            tasks = [executor.submit(self.process_unit, idx=idx, row=row, users_param=user_kw)
                     for idx, row in task_df.iterrows()]
            for future in futures.as_completed(tasks):
                row_flag, row, errors, = future.result()  # flag 1代表是成功，0代表失败，失败后所有的数据，写入csv
                self.format_progress()
                df_out = df_out.append({**row}, ignore_index=True)
                if row_flag == 0:
                    df_error = df_error.append({"errors": errors, **row, }, ignore_index=True)

            og_name = '.'.join(os.path.basename(file).split('.')[:-1])
            uuid_str = gen_uuid()
            df_out.to_csv(f"result_{uuid_str}_{og_name}.csv", index=False, encoding="utf-8-sig")
            if len(df_error) > 0:
                print(f"{file} 发现异常{len(df_error)}，请检查输出文件中的异常明细", file=sys.stderr)
                df_error.to_csv(f"error_{uuid_str}_{og_name}.csv",
                                index=False, encoding="utf-8-sig")

        # 将df_out 根据配置进行聚合输出
        if self.summary_config is not None:
            with pd.ExcelWriter(f"summary_{uuid_str}_{og_name}.xlsx") as wt:
                for cfg in self.summary_config:
                    sheet_name = cfg.name
                    # df[["产品明细", "官网价"]].groupby(by=["产品明细"]).agg(["sum"])
                    df_out[cfg.agg_fields].groupby(by=cfg.group_fields).agg(cfg.agg_methods).to_excel(wt, sheet_name)

    # process 方法的入口
    @deco_execution_time
    def process_func(self, files, **user_kw):
        if isinstance(files, list) is True:
            for file in files:
                self.process_file(file, user_kw)
        else:
            self.process_file(files, user_kw)


if __name__ == "__main__":
    from peutils.transform.v1.audio_seg.parser import AudioSegParse, AudioSegDataConfig

    class ReportRow(AbstractReportRow):
        def __init__(self, idx, row, users_param=None):
            super().__init__(idx, row, users_param=users_param)

            # 根据自己的需要写每一行的方法
            self.parse_obj = AudioSegParse(url=row['annotation'],
                                           config=AudioSegDataConfig(
                                               segment_mode="continuous",
                                               number_adpter_func=lambda i: round(i, 5)
                                           ))
            self.log.error_list.extend(self.parse_obj.check_frames_error())

        # 使用add_开头的方法添加自己需要的列的结果
        def add_col_valid_time(self):
            validTime = 0
            assert len(self.parse_obj.frames_lst) == 1, "发现帧数不为1"
            frame = self.parse_obj.frames_lst[0]
            is_valid = frame.frame_attr['is_valid']
            if is_valid == 'valid':
                for obj in frame.frame_obj_list:
                    if obj.line_contents[0]['attributes']['Category'] in ['SPEECH', 'MUSIC', 'OVERLAP'] and \
                            obj.line_contents[0]["text"] != "":
                        validTime += (obj.end - obj.start)

            return validTime


    # ct = ReportTaskV1(row_cls=ReportRow)

    ct = ReportTaskV1(row_cls=ReportRow, summary_config=[
        SummaryConfig(name="abc", group_fields=["Annotation Worker Email"], agg_fields=["valid_time"])
    ])
    ct.process_file("/Users/hwang2/Downloads/6909.csv", user_kw=None)
