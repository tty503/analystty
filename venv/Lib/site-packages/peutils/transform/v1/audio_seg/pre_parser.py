# -*- coding: UTF-8 -*-

'''
Author: Henry Wang
Date: 2022-06-14 14:33
Short Description:

Change History:

'''
from peutils.datautil import GenCategorySeq
from peutils.textutil import gen_uuid
import json
class AudioSegPre():
    def __init__(self,frame_length):
        self.audios_lst = [
            {"attributes":dict()} for i in range(frame_length)
        ]
        self.results = [
            [

            ] for i in range(frame_length)
        ]
        # self.frameorder_seq = GenCategorySeq()

    def add_audio_cut(self,frameNum,start,end,text=None,line_attr=None,block_attr=None,line_contents=None):
        ### 如果提供line_contents，那么就不用 text，line_atrr
        '''
        "content":[
                    {
                        "role":"none",
                        "text":"",
                        "attributes":{
                        }
                    }
                ]
        '''
        ###
        if line_contents is not None:
            if text is not None or line_attr is not None:
                raise Exception("提供了line_contents的情况下不需要再提供text和line_attr")
        else: # 为空的时候构建一个单行的
            line_contents = [{
                            "role":"none",
                            "text":text,
                            "attributes":line_attr if line_attr else dict()
                        }]
        self.results[frameNum].append(
            {
                "id":gen_uuid(),
                "start":start,
                "end":end,
                "attributes":block_attr if block_attr else dict(),
                "content":line_contents
            }
        )


    def dumps_data(self):
        _data = json.dumps({
            "results":self.results,
            "audios":self.audios_lst,
        },ensure_ascii=False)
        return _data


if __name__ =="__main__":
    adpre = AudioSegPre(frame_length=1)
    adpre.add_audio_cut(frameNum=0,start=1,end=2,text="abc")
    print(adpre.dumps_data())


