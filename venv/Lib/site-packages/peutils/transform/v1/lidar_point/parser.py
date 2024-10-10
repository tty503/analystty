# -*- coding: UTF-8 -*-

'''
Author: Henry Wang
Date: 2022-06-08 15:44
Short Description:

Change History:

'''
from peutils.transform.v1.base import *
import json
from peutils.datautil import gen_uuid_seq


class LidarPointFrame():
    def __init__(self,frameId,frameUrl,isValid,isSpecial,frameUrlInternal,frameUrlExternal,totalPointCount,
                 imageAttributes,
                 frame_attr,items,images,
                 config,relations):
        self.frameId = frameId
        self.frameUrl = frameUrl
        self.isValid = isValid
        self.isSpecial = isSpecial
        self.frameUrlInternal = frameUrlInternal
        self.frameUrlExternal = frameUrlExternal
        self.totalPointCount = totalPointCount
        self.log = ErrorMsgLogV1()

        self.config = config
        if self.config.parse_id_col =="fid":
            self.config.seq_func = gen_uuid_seq(start=self.config.seq_start)

        self.frame_attr = frame_attr
        self.imageAttributes = imageAttributes
        self.lidar_dict,self.real_count = self.get_lidar_dict(items)

        if self.config.leak_check ==True:
            if self.totalPointCount != self.real_count:
                self.log.create_error(f"帧{self.frameId},点云未全部标注")

        self.camera_list,self.camera_meta,self.images_dict,self.images_list= self.get_images_dict(images)

        ### 如果是全景标注，可以生成一个完整的category对象

        self._img_idset = self.get_img_idset(self.images_dict)
        self.only_lidar_idset= self.lidar_dict.keys() - self._img_idset # 只有3D 没有出现在2D的ID
        self.only_image_idset = self._img_idset -  self.lidar_dict.keys() # 只出现在2D没有出现在3D中的ID
        self.has_23d_idset = self.lidar_dict.keys() & self._img_idset # 2D和3D都出现
        self.relations = relations



    def get_fullpoint_map_list(self):
        if self.config.leak_check ==False and self.config.fill_category is None:
            raise Exception("未开启漏点检查的情况下，必须提供补充的category,否则不可使用此方法")

        # [{"pidx":0,"category":"地面"}] # 按照原始点的顺序进行排序.
        ### 如果有fill_category,允许补标签
        out_list = []
        seen_idx = set()
        for k,v in self.lidar_dict.items():
            category = v.category
            for p in v.points:
                out_list.append({
                    "pidx":p,
                    "category":category
                })
                seen_idx.add(p)
        ### 补其他点
        leak_idx = {x for x in range(self.totalPointCount)} - seen_idx
        for lk in leak_idx:
            out_list.append({
                "pidx":lk,
                "category":self.config.fill_category
            })
        #检查点的数量
        if len(out_list) != self.totalPointCount:
            self.log.create_error(f"{self.frameId}帧 补点数量不正确")

        out_list.sort(key=lambda x : x["pidx"]) ## 排序非常关键
        return out_list



    @staticmethod
    def get_img_idset(images_dict):
        img_idset = set()
        for _,v in images_dict.items():
            img_idset = img_idset | v.keys()
        return img_idset

    def get_img_obj_list(self,id,keep_nan=False):
        lst = []
        for cam in self.camera_list:
            obj = self.images_dict[cam].get(id)
            if keep_nan == True:
                lst.append(obj)
            else:
                if obj:
                    lst.append(obj)
        return lst


    def parse_lidar_by_item(self,item):

        '''
        检查逻辑
        1.如果yaw_only True,检查 rotation x 和 y都是0
        2.检查points长度和pointCount一样
        '''
        lidar_obj = LidarPointObj(
            frameNum = self.frameId,
            id = item["id"],
            category=item["category"],
            number=item["number"],
            points= item["points"],
            point_attr = json.loads(item["labels"]) if item.get("labels") else dict(),
            pointsLabels=item["pointsLabels"],
            pointCount = item["pointCount"],
            type = item["type"],
            pointsInfo = item.get("pointsInfo", []),
        )

        if self.config.parse_id_col =="id":
            key = item["id"]
        elif self.config.parse_id_col in ("gid","fid"):
            key = self.config.seq_func(item["id"])
        else:
            raise Exception("parse_id_col解析模式错误")

        ####业务检查
        if len(item["points"]) != item["pointCount"]:
            self.log.create_error(msg="点数量和数组不一致",obj=lidar_obj)


        return key,lidar_obj,item["pointCount"]

    def parse_img_by_item(self,item,width,height):

        '''
        检查逻辑
        1.图像是否超出边界外

        '''
        # if item["type"] =="polyline":
        if item["type"] in ["polyline", "polygon2", "plane3d"]:
            img_obj = LidarPointPolyline(
                frameNum=item["frameNum"],
                imageNum=item["imageNum"],
                id=item["id"],
                number=item["number"],
                type=item["type"],
                category=item["category"],
                points=item["points"],
                img_attr=json.loads(item["labels"]) if item.get("labels") else dict(),
            )
        else:
            # 暂时不会遇到
            img_obj =None

        if self.config.parse_id_col == "id":
            key = item["id"]
        elif self.config.parse_id_col in ("gid","fid"):
            key = self.config.seq_func(item["id"])
        else:
            raise Exception("parse_id_col解析模式错误")

        return key, img_obj


    def get_lidar_dict(self,items):
        lidar_dict = dict()
        real_count = 0

        for item in items:
            key,lidar_obj,pointCount =self.parse_lidar_by_item(item=item)
            lidar_dict[key] = lidar_obj
            real_count += pointCount

        if len(items) != len(lidar_dict):
            raise Exception(f"{self.config.parse_id_col} 解析模式下数量不等，请检查使用参数")
        return lidar_dict,real_count

    def get_single_image_dict(self,items,width,height):
        single_image_dict = dict()

        for item in items:
            # if item["type"] =="polyline":
            if item["type"] in ["polyline", "polygon2", "plane3d"]:
                key,img_obj = self.parse_img_by_item(item,width,height)
                single_image_dict[key] = img_obj
            else:
                # raise Exception("目前图像物体仅支持polyline,其他类型还在开发中")
                raise Exception("目前图像物体仅支持polyline,polygon2,plane3d,其他类型还在开发中")

        if len(items) != len(single_image_dict):
            raise Exception(f"{self.config.parse_id_col} 解析模式下数量不等，请检查使用参数")
        return single_image_dict

    def get_images_dict(self,images):
        ### 先解析出镜头数量
        images_dict = dict() #{cam:dict1,cam2:dict2,...}
        images_list = [] #[dict1,dict2,..]
        camera_list = []
        camera_meta = dict()

        for img in images:
            image_path = img["image"]
            camera_name = image_path.split("/")[-2]
            camera_list.append(camera_name)

            camera_meta[camera_name]= {
                "image_path":image_path,
                "imageUrlInternal":img["imageUrlInternal"],
                "imageUrlExternal":img["imageUrlExternal"],
                "width": img["width"],
                "height": img["height"],

            }
            sg_img_dict = self.get_single_image_dict(img["items"],width=img["width"],height = img["height"])
            images_dict[camera_name] = sg_img_dict
            images_list.append(sg_img_dict)

        ## check
        if len(camera_list) != len(images):
            raise Exception("找到的镜头数量和原始不一致")

        return camera_list,camera_meta,images_dict,images_list


    def __repr__(self):
        return f'Frame {self.frameId}: {self.totalPointCount}T {self.real_count}P'



class LidarPointParse(CommonBaseMixIn):

    ### 继承session属性 用来读取url
    def __init__(self,url,config):
        self.url = url
        self.config = config
        if self.config.parse_id_col == "gid":
            self.config.seq_func = gen_uuid_seq(start=self.config.seq_start)

        self.raw_data = self.get_raw_data(url) # 获取JSON字典数据数据
        self.frames_lst,self.frame_length = self.parse_by_frame()


    def check_frames_error(self):
        all_errors = []
        for frame in self.frames_lst:
            all_errors.extend(frame.log.error_list)
        return all_errors


    def parse_by_frame(self):
        '''
        返回解析后的frame列表，对应的数据
        '''
        #
        frames_lst = []
        for raw_frame in self.raw_data["results"]:

            ### 属性
            attribute = raw_frame.get("attribute")
            if attribute:
                frame_attr = json.loads(attribute)
            else:
                frame_attr = dict()

            frame = LidarPointFrame(
                frameId=raw_frame["frameId"],
                frameUrl=raw_frame["frameUrl"],
                isValid= raw_frame["attributes"]["valid"],
                isSpecial =raw_frame["attributes"]["special"],
                frameUrlInternal=raw_frame["frameUrlInternal"],
                frameUrlExternal=raw_frame["frameUrlExternal"],
                totalPointCount=raw_frame["totalPointCount"],
                frame_attr = frame_attr,
                items = raw_frame["items"],
                images = raw_frame["images"],
                imageAttributes=raw_frame["imageAttributes"],
                config= self.config,
                relations=raw_frame.get("relations", [])
            )
            frames_lst.append(frame)
        return frames_lst,len(frames_lst)


class LidarPointDataConfig():
    def __init__(self,leak_check=False,number_adpter_func=None,fill_category=None,
                 parse_id_col="id",seq_start=0,overflow=False):
        self.leak_check = leak_check # 为True的时候会检查点是否完整
        self.number_adpter_func = number_adpter_func
        self.fill_category = fill_category
        self.parse_id_col = parse_id_col # id或g_id, frame_id  # 这里没有number选项，因为默认是分类编号
        self.seq_start = seq_start
        self.overflow = overflow # 这里暂时没做检查

from pprint import pprint

if __name__ =="__main__":
    ## 单帧
    from pprint import pprint
    lidarpoint = LidarPointParse(url="https://oss-prd.appen.com.cn:9001/tool-prod/2bcdc0ebda8758cf9caeb29ba7cfa408/R.1654659117117.lidar.seg.2df039af-a185-49cf-84e7-be8b295b7077.COSPsAIQDA3d3d_2022-06-08T033126Z.14513.QA_RW.f8d93205-4c8f-47ee-9a3c-3ae80f7d90e5.8308b8d5ec23225be41513692c55b8cc.review.json",
                         config =LidarPointDataConfig(
                             leak_check = False,  ## 检查点的数量是否和总点的数量一样.
                             fill_category= "背景", # 对于未标注的数据默认的标签，如果不需要的时候就是None
                             number_adpter_func=None, #lambda i: round(i,3), # 默认None
                             parse_id_col = "id",
                             seq_start = 0, # 如果是 gid,fid,或者frame_id 需要提供seq_start， 如果是0就是从1开始编号，如果是-1就是从0开始编号
                             overflow= False
                         ))
    pprint(lidarpoint.frames_lst[0])#.lidar_dict)
    pprint(lidarpoint.frames_lst[0].lidar_dict)
    print(lidarpoint.frames_lst[0].log.error_list)
    pprint(lidarpoint.frames_lst[0].images_dict)

    # pprint(lidarpoint.frames_lst[0].get_fullpoint_map_list()) # 获取点的category排序后的完整结果
    # print(lidarpoint.frames_lst[0].totalPointCount)
