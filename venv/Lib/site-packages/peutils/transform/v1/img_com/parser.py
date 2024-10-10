# -*- coding: UTF-8 -*-

'''
Author: Henry Wang
Date: 2022-06-09 14:51
Short Description:

Change History:

'''
from peutils.transform.v1.base import *
import json
from peutils.datautil import gen_uuid_seq
from PIL import Image
from io import BytesIO


class ImgComFrame():
    def __init__(self,frameId,frameUrl,isValid,imageWidth,imageHeight,
                 rotation,
                 frame_attr,
                 config):
        self.frameId = frameId
        self.frameUrl = frameUrl
        self.isValid = isValid
        self.imageWidth = imageWidth
        self.imageHeight = imageHeight
        self.rotation = rotation

        self.log = ErrorMsgLogV1()
        self.config = config
        self.frame_attr = frame_attr
        self.frame_items = []
        self.frame_dict = dict()

    def add_frame_obj(self,obj:Img2Dobj):
        if obj.order is None:
            self.log.create_error("order检查模式下不能缺失",obj=obj)
        self.frame_items.append(obj)

        if self.config.parse_id_col == 'id':
            self.frame_dict[obj.id] = obj
        elif self.config.parse_id_col == "number":
            self.frame_dict[obj.number] = obj
        else:
            raise Exception(f"parse_id_col not defined: {self.config.parse_id_col}")


    # def to_pre_dict(self):
    #     _pre_dict = {
    #         "frameId":self.frameId,
    #         "frame_attr":self.frame_attr,
    #         "frame_items":self.frame_items
    #     }
    #     return _pre_dict


    def __repr__(self):
        return f'Frame {self.frameId} {len(self.frame_items)}T'


class ImgComParse(CommonBaseMixIn):

    ### 继承session属性 用来读取url
    def __init__(self,url,config):
        self.config = config
        self.url = url
        if self.config.use_oss == False:
            self.raw_data = self.get_raw_data(url) # 获取JSON字典数据数据
        else:
            self.raw_data = self.get_oss_data(url)

        self.cameras_lst = [x["camera"] for x in self.raw_data["frames"]]  # 所有镜头名称

        self.instance_dict, self.instance_lst, self.object_lst = self.parse_by_instance()
        self.frames_lst, self.frame_length = self.parse_by_frame()



    def check_frames_error(self):
        all_errors = []
        for frame in self.frames_lst:
            all_errors.extend(frame.log.error_list)
        return all_errors

    def parse_by_frame(self):
        if self.config.camera not in self.cameras_lst:
            raise Exception(f"{self.config.camera} 不在当前的已有镜头中,{self.cameras_lst}")

        frames_lst = []
        cam_idx = self.cameras_lst.index(self.config.camera)
        for raw_frame in self.raw_data["frames"][cam_idx]["frames"]: # 先解析default cam
            if self.config.parse_img_size == "default":
                imageWidth = raw_frame["imageWidth"]
                imageHeight = raw_frame["imageHeight"]
            elif self.config.parse_img_size == "imageIO":
                if "imageWidth" in raw_frame:
                    imageWidth = raw_frame["imageWidth"]
                    imageHeight = raw_frame["imageHeight"]
                else:
                    response = requests.get(raw_frame['imageUrl'])
                    img = Image.open(BytesIO(response.content))
                    imageWidth, imageHeight = img.size
            elif self.config.parse_img_size == "firstFrame":
                if raw_frame["frameIndex"] == 0:
                    if "imageWidth" in raw_frame:
                        imageWidth = raw_frame["imageWidth"]
                        imageHeight = raw_frame["imageHeight"]
                    else:
                        response = requests.get(raw_frame['imageUrl'])
                        img = Image.open(BytesIO(response.content))
                        imageWidth, imageHeight = img.size
                    frameImageWidth = imageWidth
                    frameImageHeight = imageHeight
                else:
                    imageWidth = frameImageWidth
                    imageHeight = frameImageHeight
            else:
                raise Exception(f"图像尺寸{self.config.parse_img_size} 解析模式error")

            frame = ImgComFrame(
                frameId= raw_frame["frameIndex"],
                frameUrl= raw_frame["imageUrl"],
                imageWidth = imageWidth,
                imageHeight = imageHeight,
                isValid= raw_frame["valid"],
                rotation = raw_frame["rotation"],
                frame_attr= DotDict(raw_frame.get("attributes")) if raw_frame.get("attributes") else DotDict(),
                config=self.config
            )
            frames_lst.append(frame)

        for obj in self.object_lst:
            frames_lst[obj.frameNum].add_frame_obj(obj)

        # 对frame增加相关的obj,并且进行解析数量的检查
        for f in frames_lst:
            if len(f.frame_items) != len(f.frame_dict):
                f.log.create_error(f"{self.config.parse_id_col}解析模式下发现数量不等,请检查")

        ### 对order进行检查并且排序数据,缺失的数据排在最前面.
        for f in frames_lst:
            f.frame_items.sort(key=lambda i: -1 if i.order is None else i.order)

        return frames_lst,len(frames_lst)

    def parse_by_instance(self):

        instance_lst = []
        instance_dict = dict()
        all_obj_lst = []
        for instance in self.raw_data["instances"]:
            dynamic_attr = dict()
            if instance.get("dynamicAttributes"):
                for da in instance["dynamicAttributes"]:
                    if da["camera"] == self.config.camera:
                        for frame in da["frames"]:
                            if frame["attributes"]:
                                dynamic_attr[frame["frameIndex"]] = frame["attributes"]

            ist = ImgInstance(
                id=instance["id"],
                category = instance["category"],
                categoryName = instance["categoryName"],
                # categoryColor = instance["categoryColor"],
                number = instance["number"],
                ist_attr = DotDict(instance.get("attributes")) if instance.get("attributes") else DotDict(),
                ist_dynamic_attr = dynamic_attr
            )
            obj_list = []
            for ch in instance["children"]:
                for camera_obj in ch["cameras"]:
                    if camera_obj["camera"] == self.config.camera:
                        for obj in camera_obj["frames"]:
                            imgobj = Img2Dobj(
                                instance=ist,
                                frameNum=obj["frameIndex"],
                                id=ch["id"],
                                number=ch["number"],
                                category=ch["name"],
                                displayName=ch["displayName"],
                                color=ch["displayColor"],
                                shapeType=obj["shapeType"],
                                shape=obj["shape"],
                                order=obj.get("order"),
                                layer= obj.get("layer",0),
                                # 测试None if ch["id"] =="faeb43ff-546b-4f80-b99b-8e4eeb62f112" else obj.get("order"),
                                img_attr=obj.get("attributes", dict()),
                                isOCR=obj.get("isOCR", False),
                                OCRText=obj.get("OCRText", ""),
                                isRaw=obj.get("isRaw", None),
                            )
                            obj_list.append(imgobj)

            # 加到ist实例中
            all_obj_lst.extend(obj_list)
            ist.obj_list.extend(obj_list)
            ### 最后再加
            instance_lst.append(ist)
            instance_dict[ist.id] = ist

        return instance_dict,instance_lst,all_obj_lst



class ImgComDataConfig():
    def __init__(self,parse_id_col="id",number_adpter_func=None,seq_start=0,check_order=True,overflow=False,camera="default",parse_img_size="default",use_oss=False):
        self.number_adpter_func = number_adpter_func
        self.parse_id_col = parse_id_col  # 默认id ## 暂时不引入fid,gid
        self.check_order = check_order # 检查order 是否都存在
        self.seq_start = seq_start  # 暂时用不到
        self.overflow = overflow # 默认不允许超出图像边界
        self.camera = camera
        self.parse_img_size = parse_img_size #支持三种模式  default:从平台取   firstFrame:取首帧  imageIO:实时在线读取
        self.use_oss = use_oss # False,不走oss, True 从OSS使用sdk的方式读取数据，在大文件的情况下推荐这种方式,注意只读平台tool-prod的数据



if __name__ =="__main__":

    from pprint import pprint
    # ### 单镜头
    # img = ImgComParse(url="https://oss-prd.appen.com.cn:9001/tool-prod/a2a3ef0c-55c4-4d15-8cc2-ff6aeb7878dd/R.1650783983510.a2a3ef0c-55c4-4d15-8cc2-ff6aeb7878dd.CODU4AEQEg3d3d_2022-04-24T070156Z.18107.result.json",
    #                      config =ImgComDataConfig(
    #                      ))
    # print(img.cameras_lst)
    # pprint(img.instance_dict)
    # print(img.frames_lst[0].frame_dict,len(img.frames_lst[0].frame_dict))
    # print(img.frames_lst[0].frame_items,len(img.frames_lst[0].frame_dict))

    ### 多镜头
    # img = ImgComParse(url="https://oss-prd.appen.com.cn:9001/tool-prod/preview-eqijvSUEhq-kogoQOP_9t/preview-eqijvSUEhq-kogoQOP_9t.video-track-v2_task.video-track-v2_record.result.json",
    #                      config =ImgComDataConfig(
    #                          camera="wide" # far or wide
    #                      ))
    # print(img.cameras_lst)
    # pprint(img.instance_dict)
    # pprint(img.object_lst)
    # pprint(img.)


    # print(img.frames_lst[0].frame_items)

    # pprint(img.instance_lst)
    # pprint(img.instance_lst[0].obj_list)
    # pprint(img.object_lst)

    # pprint(img.frames_lst[0].frame_items)
    # for item in img.frames_lst[0].frame_items:
    #     print(item.instance)

    # pprint(img.frames_lst[0].)
    # img.frames_lst[9].frame_obj_list.sort(key=lambda i: i.order)
    # pprint(img.frames_lst[9].frame_items)
    # pprint(img.frames_lst[9].log.error_list)
    # pprint(img)
    # pprint(img.object_lst)

    # for frame in img.frames_lst:
    #     # print(frame.imageWidth)
    #     # print(frame.frame_obj_list)
    #     # print(frame.log.error_list)
    #     pprint(frame)
    # pprint(lidar.frames_lst[49].lidar_dict)