# -*- coding: UTF-8 -*-

'''
Author: Henry Wang
Date: 2022-06-13 11:20
Short Description:

Change History:

'''
from peutils.transform.v1.base import *
import json


class AudioSegFrame():
    def __init__(self,frameId,frameUrl,duration,
                 frame_attr,  #  对应audios中attributes 就是全局属性配置
                 config):
        self.frameId = frameId
        self.frameUrl = frameUrl
        self.duration = duration

        self.log = ErrorMsgLogV1()
        self.config = config
        self.frame_attr = frame_attr
        self.frame_obj_list = []


    def add_frame_obj(self,obj:AudioCutObj):
        ## 如果是连续模式，每次应该是等于上一个
        ## 如果是另外一种，每次的start应该是小于等于上一个
        if self.config.segment_mode =="continuous":
            if len(self.frame_obj_list) != 0:
                if obj.start != self.frame_obj_list[-1].end:
                    self.log.create_error("连续模式下新增切分段开始时间必须等于上一个结束时间",obj=obj)
        elif  self.config.segment_mode =="individual":
            if len(self.frame_obj_list) != 0:
                if obj.start < self.frame_obj_list[-1].start:
                    self.log.create_error("分段模式下，每个开始时间必须大于上一个结束时间",obj=obj)
        self.frame_obj_list.append(obj)


    def __repr__(self):
        return f'Frame {self.frameId} {len(self.frame_obj_list)}T'


class AudioSegParse(CommonBaseMixIn):

    ### 继承session属性 用来读取url
    def __init__(self,url,config):
        self.url = url
        self.config = config
        self.raw_data = self.get_raw_data(url) # 获取JSON字典数据数据
        self.frames_lst, self.frame_length = self.parse_by_frame()

    def check_frames_error(self):
        all_errors = []
        for frame in self.frames_lst:
            all_errors.extend(frame.log.error_list)
        return all_errors

    def parse_by_frame(self):
        frames_lst = []
        for idx,raw_frame in enumerate(self.raw_data["audios"]):
            frame = AudioSegFrame(
                frameId= idx,
                frameUrl= raw_frame["url"],
                duration = raw_frame["duration"],
                frame_attr= raw_frame.get("attributes") if raw_frame.get("attributes") else dict(),
                config= self.config
            )
            frames_lst.append(frame)

        for idx,raw_frame_obj_list in enumerate(self.raw_data["results"]):
            for obj_idx, obj in enumerate(raw_frame_obj_list):
                audio_cut = AudioCutObj(
                    frameNum=idx,
                    id = obj["id"] ,
                    number = obj_idx + 1,
                    start = self.config.number_adpter_func(obj["start"]) if self.config.number_adpter_func else obj["start"],
                    end = self.config.number_adpter_func(obj["end"])if self.config.number_adpter_func else obj["end"],
                    block_attr= obj.get("attributes") if obj.get("attributes") else dict(),
                    line_contents= obj["content"],
                )
                frames_lst[idx].add_frame_obj(audio_cut)

        return frames_lst,len(frames_lst)


class AudioSegDataConfig():

    def __init__(self,segment_mode,parse_id_col="id",number_adpter_func=None,seq_start=0):
        assert segment_mode in {"continuous","individual"},"分段模式必须是 continuous 或者 individual "
        self.segment_mode = segment_mode  # continuous,individual
        self.number_adpter_func = number_adpter_func
        self.parse_id_col = parse_id_col, # 默认id ## 暂时不引入fid,gid
        self.seq_start = seq_start  # 暂时用不到


### 界面会根据顺序排序的

if __name__ =="__main__":
    ## 单帧
    from pprint import pprint
    ad = AudioSegParse(url="https://oss-prd.appen.com.cn:9001/tool-prod/preview-IvwN9qwWAujQfAbtkqWMw/preview-IvwN9qwWAujQfAbtkqWMw.long-audio_task.long-audio_record.result.json",
                         config =AudioSegDataConfig(
                             segment_mode="continuous",
                             number_adpter_func = lambda i: round(i,5)
                         ))
    # pprint(ad.frames_lst[0].frame_obj_list)

    for cut in ad.frames_lst[0].frame_obj_list:
        print(cut.start,cut.end,cut.line_contents[0]["text"])