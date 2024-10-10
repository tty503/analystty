# -*- coding: UTF-8 -*-

'''
Author: Henry Wang
Date: 2022-06-14 09:16
Short Description:

Change History:

预处理必须的数据结构
{
  "instances": [
    {
      "id": "xxx", // 唯一编号勿重复
      "category": "CAR", // 请对应模板配置中唯一值
      "number": 1, // 同一category下勿重复
      "children": [
        {
          "id": "yyy", // 唯一编号勿重复
          "name": "车身", // 对应模版中的唯一标识
          "number": 1, // 同一instance，同一name下勿重复
          "cameras": [
            {
              "camera": "default", // 请对应模板数据（若为单相机，则默认为default）
              "frames": [   //如果只有一个摄像头的话，这边。
                {
                  "frameIndex": 0,
                  "isKeyFrame": true, // 预标数据默认为关键帧true
                  "shapeType": "polygon",
                  "shape": {} // 图形数据（不同图形的数据结构不同，详情参考下方图形数据结构说明）
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}



'''
import json
from peutils.transform.v1.base import *
from collections import defaultdict
from operator import itemgetter
from itertools import groupby
from peutils.transform.v1.base import ImgInstance, Img2Dobj
from peutils.textutil import gen_uuid
from peutils.datautil import GenCategorySeq


class ImgComPre():
    ### 提供ImgComFrame实例对象frame_list，或者提供frame_length构造一个空的
    def __init__(self, frame_length, instance_lst=None, raw_frames=None, cam_names=None):

        self.frame_length = frame_length

        if raw_frames is not None:
            self.frames = [
                {
                    "frameIndex": f["frameIndex"],
                    "attributes": f.get("attributes", dict())
                }
                for f in raw_frames[0]["frames"]
            ]
        else:
            ### 构造一个空的属性
            self.frames = [
                {
                    "frameIndex": i,
                    "attributes": {}
                } for i in range(self.frame_length)]

        if instance_lst is not None:
            self.instance_lst = instance_lst
        else:
            self.instance_lst = []

        self.instance_seq = GenCategorySeq()
        self.imgobj_seq = GenCategorySeq()
        self.frameorder_seq = GenCategorySeq()
        if cam_names is None:
            self.cam_names = ["default"]
        else:
            assert isinstance(cam_names,list) is True,"cam_names必须是数组"
            assert "default" not in cam_names,"传入的镜头不能有default"
            self.cam_names = cam_names

    def add_instance_obj(self, p_category, p_attributes=None, ist_number=None, ist_id=None):
        "p_id 生成p number序列 从1开始。 按照分类生成"
        if ist_number is None:
            ist_number = self.instance_seq.up_seq(p_category)
        ist = ImgInstance(
            id=gen_uuid() if ist_id is None else ist_id,
            number=ist_number,
            category=p_category,
            ist_attr=p_attributes if p_attributes else dict(),
        )
        self.instance_lst.append(ist)
        return ist

    def add_img_obj(self, instance, uuid, frameNum, c_category, shapeType, shape, c_attributes=None, isOCR=None,
                    OCRText=None, cam_name="default",layer=0,isRaw=None):
        # child_seq = self.instance_seq.up_seq(c_category)
        ### 先判断uuid + c_category 当前有没有

        ### 按每一帧进行编号
        frame_order = self.frameorder_seq.up_seq(str(frameNum))
        # print("frame_order",frame_order)

        obj = None
        for o in instance.obj_list:
            if o.id == uuid:
                obj = o
        if obj is None:
            # 识别到新的ID边用c_category 获取一个新的编号
            child_number = self.imgobj_seq.up_seq(c_category)
        else:
            child_number = self.imgobj_seq.get_seq(c_category)

        instance.obj_list.append(
            Img2Dobj(
                instance=instance,
                frameNum=frameNum,
                id=uuid,
                number=child_number,
                category=c_category,
                shapeType=shapeType,
                shape=shape,
                img_attr=c_attributes if c_attributes else dict(),
                order=frame_order,
                isOCR=isOCR,
                OCRText=OCRText,
                cam_name=cam_name,
                layer = layer,
                isRaw = isRaw
            )
        )

    def dumps_data(self):
        _to_instances_dict = {
            "instances": [i.to_pre_dict() for i in self.instance_lst],
            "frames": [
                {
                    "camera": cam_name,
                    "frames": self.frames
                } for cam_name in self.cam_names
            ]
        }
        instances_data = json.dumps(_to_instances_dict, ensure_ascii=False)
        return instances_data


if __name__ == "__main__":
    from pprint import pprint

    ### 之前数据的加载
    from peutils.transform.v1.img_com.parser import ImgComParse, ImgComDataConfig

    img = ImgComParse(
        # url = "https://oss-prd.appen.com.cn:9001/tool-prod/preview--r9nHFGv7vcbBW7P-JQ7t/preview--r9nHFGv7vcbBW7P-JQ7t.video-track-v2_task.video-track-v2_record.result.json",
        url="https://oss-prd.appen.com.cn:9001/tool-prod/a2a3ef0c-55c4-4d15-8cc2-ff6aeb7878dd/R.1650783983510.a2a3ef0c-55c4-4d15-8cc2-ff6aeb7878dd.CODU4AEQEg3d3d_2022-04-24T070156Z.18107.result.json",
        config=ImgComDataConfig(
        ))
    imgpre = ImgComPre(frame_length=img.frame_length,
                       instance_lst=img.instance_lst, raw_frames=img.raw_data["frames"])
    print(imgpre.dumps_data())
    #### 加载之前的数据

    ### 创建新的数据
    from peutils.transform.v1.base import ImgInstance, Img2Dobj

    imgpre2 = ImgComPre(frame_length=img.frame_length)
    ist1 = imgpre2.add_instance_obj(p_category="小汽车", p_attributes={"a": 1})

    ### id如果和之前相同，那么这里写入的时候会当成同一个物体写入，有tracking的功能。
    ### 这边的c_category 注意是平台这个子组建下的名称，不要放错到其他实例中
    ### 如果相同id 但是c_category 不一样那么重新创建一个child.
    imgpre2.add_img_obj(instance=ist1, uuid="abc", frameNum=1, c_category="汽车头", shapeType="line", shape={"kk": 1},
                        c_attributes={"w": None})
    imgpre2.add_img_obj(instance=ist1, uuid="abc", frameNum=2, c_category="汽车头", shapeType="line2", shape={"kk": 2},
                        c_attributes={"w": "2"})

    ### 添加一个新的分类物体，但是标签相同
    imgpre2.add_img_obj(instance=ist1, uuid="dd", frameNum=1, c_category="汽车头", shapeType="line2", shape={"kk": 2},
                        c_attributes={"w": "2"})
    print(imgpre2.dumps_data())
    ### 先创建instance,写入这个instatnce所有的内容，再写入image对象。
