# -*- coding: UTF-8 -*-

'''
Author: Henry Wang
Date: 2022-05-30 13:08
Short Description:

Change History:

'''
from urllib.parse import unquote

import requests
from oss2 import defaults, Session
from urllib3 import Retry

from peutils.ossutil import OSS_STS_API
from requests.adapters import HTTPAdapter
import inspect
import json
from peutils.textutil import gen_uuid
from typing import Dict, List, Union
import oss2
import os
import json


class DotDict(dict):
    def __init__(self, *args, **kwargs):
        super(DotDict, self).__init__(*args, **kwargs)

    def __getattr__(self, key):
        value = self[key]
        if isinstance(value, dict):
            value = DotDict(value)
        return value


# print(json.dumps(DotDict()))
# print(json.dumps(a))
# print(a["a"])
# a = DotDict()
# a["a"] = 1
#
# print(a)
# print(bool(DotDict()))

def get_session(retry=3):
    session = requests.Session()
    session.mount('http://', HTTPAdapter(max_retries=retry))
    session.mount('https://', HTTPAdapter(max_retries=retry))

    return session


class OssSession(Session):
    def __init__(self):
        super().__init__()
        psize = defaults.connection_pool_size
        retries = Retry(total=defaults.request_retries,
                        backoff_factor=0.5,
                        status_forcelist=[500, 502, 503, 504],
                        allowed_methods=["GET"])
        self.session.mount('http://', requests.adapters.HTTPAdapter(pool_connections=psize, pool_maxsize=psize,
                                                                    max_retries=retries))
        self.session.mount('https://', requests.adapters.HTTPAdapter(pool_connections=psize, pool_maxsize=psize,
                                                                     max_retries=retries))


# print(inspect.isbuiltin(int))

def dict_adapter(d: dict, out_adapter=None, rename: dict = None):
    d = {k: v for k, v in d.items()}
    if out_adapter is not None:
        if inspect.isfunction(out_adapter):
            for k, v in d.items():
                d[k] = out_adapter(v)
        elif isinstance(out_adapter, dict):
            for key, out_func in out_adapter.items():
                d[key] = out_func(d[key])
        else:
            raise Exception("参数必须是函数或者字典. 如果是字典，那么就是对应的值是方法")

    if rename is not None:
        ## 重写一遍所有的，但是这边不能有原来存在过的键，否则会冲突
        if len(set(rename.values()) & set(d.keys())) > 0:
            raise Exception(f"新的名称不能存在之前的名称中 {repr(set(rename.values()) & set(d.keys()))}")
        else:
            d = {rename.get(k, k): v for k, v in d.items()}
    return d


### 不兼容老的Plss模版，只兼容新的模版.
### 都存在的 id, msg, category(可选). number(可选). frameNum(可选，如果单帧就是0)
class ErrorUnit():
    def __init__(self, id, message, info=None, category=None, number=None, frameNum: Union[List[int], int, None] = None,
                 block=True):
        self.id = id
        self.message = message
        self.category = category
        self.number = number
        self.frameList = self.get_frameList(frameNum)
        self.block = block
        self.info = info

    def get_frameList(self, frameNum):
        if frameNum is None:
            return [0]
        elif isinstance(frameNum, int):
            return [frameNum]
        elif isinstance(frameNum, list):
            return list(frameNum)
        else:
            raise Exception(f"不正确的frameNum定义 {frameNum}")

    def __repr__(self):
        if self.frameList != [0]:
            err_str = f"帧:{[x + 1 for x in self.frameList]} ID:{self.id} Message:{self.message} "
        else:
            err_str = f"ID:{self.id} Message:{self.message} "

        if self.category != "":
            err_str += f"物体:{self.category} {self.number}"

        return err_str


'''
平台错误的格式
1. 音频类项目
- 目前没有特别的要求，按照规则，需要关联的

2. 通用图像平台要求
是通过info来进行定位和提示，框架在提供了obj的情况下会自动构造，增加instanceId和instanceItemId
图像可以通过覆盖info来达到只提示实例，或者其他像素高量等功能
info={
    "instanceId": obj.instance.id, # 实例的ID 一般需要提供
    "instanceItemId": obj.id, # 可选 物体的ID
    "type": "highlight", # 可选，highlight是高亮功能
    "pixels": RLE # 可选，可以提供RLE格式达到高亮效果
}

3. 3D点云拉框
info={
    "type":"cube", # 必须 cube 代表3D框，cast 代表图像中的框
    "id":"uuid"  # 如果是提示点云，提供点云id,如果是图像框就是图像物体的ID
    "category":"卡车" # 可选，会拼到提示里，最好提供 
    "number":1   #可选，会拼到提示里，最好提供 对应物体的number，
    "imageNum":0 # 对应镜头索引，从0开始，如果是cast 类型必须提供
}

4. 3D点云语义分割
说是和上面一样，2D中可能有车道线，目前和3D点云拉框一样处理，有具体的项目，到时候再看下



create_error在使用时
1. 如果提供obj,那么会产生关联错误，提供定位的功能,如果不提供obj会有一个未关联的错误,有关联性的一定要提供obj
2. 一般音频检查不需要提供info可以通过id直接定位,图像和3D需要info才能定位，框架在提供了obj的情况下会自动构造，不需要提供额外的info信息。
3. info信息可以另外提供，提供了info就不能提供，obj 这两者是冲突的，如果自己构造info,务必保证内容和关系的正确性

'''


class ErrorMsgLogV1():

    def __init__(self):
        self.error_list = []

    def create_error(self, msg, obj=None, info=None, frameNum: Union[List[int], int, None] = None, block=True):

        # 当是obj图像的实例时候，如果指定了info，那么根据info来显示，如果 没有指定当给定obj的时候默认
        # 如果给了指定的

        if obj is not None and info is not None:
            raise Exception("开发错误:创建错误记录时，参数不能同时提供obj和info")

        if obj is None:
            self.error_list.append(ErrorUnit(
                id="common-" + gen_uuid(),
                message=msg,
                category="",
                number="",
                frameNum=frameNum,
                info=info,
                block=block
            ))
        else:
            if info is None:
                # 2D框自动加内容
                if isinstance(obj, Img2Dobj):
                    info = {
                        "instanceId": obj.instance.id,
                        "instanceItemId": obj.id
                    }
                elif isinstance(obj, Lidar3dObj) or isinstance(obj, Lidar3dPolygonObj) or isinstance(obj,
                                                                                                     LidarPointObj) or isinstance(
                    obj, Lidar3dCamCube):
                    info = {
                        "type": "cube",
                        "id": obj.id,
                        "category": obj.category,
                        "number": obj.number
                    }
                elif isinstance(obj, Lidar3dImageRect) or isinstance(obj, LidarPointPolyline):
                    info = {
                        "type": "cast",
                        "id": obj.id,
                        "category": obj.category,
                        "number": obj.number,
                        "imageNum": obj.imageNum
                    }

                # 提供的话 就不覆盖
            self.error_list.append(ErrorUnit(
                id=obj.id,
                message=msg,
                category=obj.category,
                number=obj.number,
                frameNum=obj.frameNum,
                info=info,
                block=block
            ))

    def fomart_error_str(self) -> str:
        return "\n".join([repr(e) for e in self.error_list])
        # 如果frame是0，不打印。

    def format_a9_error_str(self) -> str:
        # 平台只接受id,message,frames,block四个属性。
        err_lst = []
        for e in self.error_list:
            eu = {
                "id": e.id,
                "message": e.message,
                "frames": e.frameList,
                "blockSubmit": e.block
            }
            if e.info:
                eu["info"] = e.info
            err_lst.append(eu)

        return json.dumps(err_lst, ensure_ascii=False)


class Lidar3dObj():
    def __init__(self, frameNum, id, number, category, position, dimension, rotation=None, rotation2=None,
                 lidar_attr=None, quaternion=None, pointCount=None, vertices=None, type=None):
        self.frameNum = frameNum
        self.id = id
        self.number = number
        self.category = category
        self.position = DotDict(position)
        self.rotation = DotDict(rotation) if rotation else DotDict()
        self.rotation2 = DotDict(rotation2) if rotation2 else DotDict()
        self.dimension = DotDict(dimension)

        self.lidar_attr = DotDict(lidar_attr) if lidar_attr else DotDict()  # 属性
        self.quaternion = DotDict(quaternion) if quaternion else DotDict()
        self.pointCount = pointCount
        self.vertices = vertices
        self.type = type

    def __repr__(self):
        return f"{self.id} {self.category} {self.number}"

    def to_dict(self):
        _data_dict = {
            "frameNum": self.frameNum,
            "id": self.id,
            "number": self.number,
            "category": self.category,
            "position": self.position,
            "rotation": self.rotation if self.rotation else None,
            "rotation2": self.rotation2 if self.rotation2 else None,
            "quaternion": self.quaternion if self.quaternion else None,
            "dimension": self.dimension,
            # "labels": "" if self.lidar_attr else json.dumps(self.lidar_attr, ensure_ascii=False),
            "labels": json.dumps(self.lidar_attr, ensure_ascii=False) if self.lidar_attr else "",
        }
        if self.pointCount is None:
            _data_dict["pointCount"] = {}
        elif isinstance(self.pointCount, int):
            _data_dict["pointCount"] = {
                "lidar": self.pointCount
            }
        elif isinstance(self.pointCount, dict):
            _data_dict["pointCount"] = self.pointCount
        else:
            raise ValueError(f'pointCount参数error')
        return _data_dict


class Lidar3dCamCube():
    def __init__(self, frameNum, id, number, category, position, dimension, rotation=None, rotation2=None,
                 camCubeAttr=None, quaternion=None, pointCount=None, vertices=None, type=None, imageNum=None):
        self.frameNum = frameNum
        self.imageNum = imageNum
        self.id = id
        self.number = number
        self.category = category
        self.position = DotDict(position)
        self.rotation = DotDict(rotation) if rotation else DotDict()
        self.rotation2 = DotDict(rotation2) if rotation2 else DotDict()
        self.dimension = DotDict(dimension)

        self.camCubeAttr = DotDict(camCubeAttr) if camCubeAttr else DotDict()  # 属性
        self.quaternion = DotDict(quaternion) if quaternion else DotDict()
        self.pointCount = pointCount
        self.vertices = vertices
        self.type = type

    def __repr__(self):
        return f"{self.id} {self.category} {self.number}"

    def to_dict(self):
        _data_dict = {
            "frameNum": self.frameNum,
            "id": self.id,
            "number": self.number,
            "category": self.category,
            "position": self.position,
            "rotation": self.rotation if self.rotation else None,
            "rotation2": self.rotation2 if self.rotation2 else None,
            "quaternion": self.quaternion if self.quaternion else None,
            "dimension": self.dimension,
            # "labels": "" if self.lidar_attr else json.dumps(self.lidar_attr, ensure_ascii=False),
            # "labels": json.dumps(self.camCubeAttr, ensure_ascii=False) if self.camCubeAttr else "",
            # 注意CamCube的labels是dict类型
            "labels": self.camCubeAttr if self.camCubeAttr else dict(),
        }
        return _data_dict


class Lidar3dPolylineObj():
    def __init__(self, frameNum, id, number, category, interpolated, reviewKey, pointCount, labelsObj, lidar_attr=None,
                 vertices=None, type=None):
        self.frameNum = frameNum
        self.id = id
        self.number = number
        self.category = category
        self.interpolated = interpolated
        self.reviewKey = reviewKey
        self.pointCount = pointCount
        self.labelsObj = labelsObj
        self.lidar_attr = DotDict(lidar_attr) if lidar_attr else DotDict()  # 属性
        self.vertices = vertices
        self.type = type

    def __repr__(self):
        return f"{self.id} {self.category} {self.number}"

    def to_dict(self):
        _data_dict = {
            "frameNum": self.frameNum,
            "id": self.id,
            "number": self.number,
            "category": self.category,
            "interpolated": self.interpolated,
            "reviewKey": self.reviewKey,
            "pointCount": self.pointCount,
            "labelsObj": self.labelsObj,
            "vertices": self.vertices,
            "type": self.type,
            # "labels": "" if self.lidar_attr else json.dumps(self.lidar_attr, ensure_ascii=False),
            "labels": json.dumps(self.lidar_attr, ensure_ascii=False) if self.lidar_attr else "",
        }
        return _data_dict


class Lidar3dPolygonObj():
    def __init__(self, frameNum, id, number, category, lidar_attr=None, vertices=None, type=None):
        self.frameNum = frameNum
        self.id = id
        self.number = number
        self.category = category
        self.lidar_attr = DotDict(lidar_attr) if lidar_attr else DotDict()  # 属性
        self.vertices = vertices
        self.type = type

    def __repr__(self):
        return f"{self.id} {self.category} {self.number}"

    def to_dict(self):
        _data_dict = {
            "frameNum": self.frameNum,
            "id": self.id,
            "number": self.number,
            "category": self.category,
            "vertices": self.vertices,
            # "labels": "" if self.lidar_attr else json.dumps(self.lidar_attr, ensure_ascii=False),
            "labels": json.dumps(self.lidar_attr, ensure_ascii=False) if self.lidar_attr else "",
        }
        return _data_dict


class Lidar3dImageRect():
    def __init__(self, frameNum, id, number, type, category, position, dimension, imageNum=None,
                 img_attr=None, points=None, rect1=None, rect2=None, middle=None):
        '''
        VANISH_CUBE 灭点立体框才有points
        RECT_CUBE: 前后矩形框组成的立体框 只有这个才有rect1,rect2
        '''
        self.frameNum = frameNum
        self.imageNum = imageNum  # 图像的次序。从0开始
        self.id = id
        self.number = number
        self.type = type
        self.category = category
        self.position = DotDict(position)
        self.dimension = DotDict(dimension)

        self.img_attr = DotDict(img_attr) if img_attr else DotDict()  # 属性

        self.points = points
        self.rect1 = rect1
        self.rect2 = rect2
        self.middle = middle
        self.bbox = self.get_bbox()

    def get_bbox(self):
        # xmin ymin w h
        return [
            self.position["x"], self.position["y"],
            self.dimension["x"], self.dimension["y"]
        ]

    def get_dig_points(self):
        '''
        对角线点，左上角点和右下角点,2*2 数组
        '''
        if self.type != 'rectangle':
            raise Exception("非矩形框请不要使用对角坐标")
        else:
            return [
                [self.position["x"], self.position["y"]],
                [self.position["x"] + self.dimension["width"], self.position["y"] + self.dimension["height"]]
            ]

    def to_dict(self):
        _data_dict = {
            "type": self.type,
            "id": self.id,
            "number": self.number,
            "category": self.category,
            "position": self.position,
            "dimension": self.dimension,
            # "labels": "" if self.img_attr else json.dumps(self.img_attr, ensure_ascii=False),
            "labels": json.dumps(self.img_attr, ensure_ascii=False) if self.img_attr else "",
        }
        if self.type == "VANISH_CUBE":
            if self.points is None:
                raise Exception("灭点必须提供points")
            _data_dict["points"] = self.points

        if self.type == "RECT_CUBE":
            if self.rect1 is None or self.rect2 is None:
                raise Exception("RECT_CUBE 必须提供rect1和rect2")
            _data_dict["rect1"] = self.rect1
            _data_dict["rect2"] = self.rect2

        return _data_dict

    def __repr__(self):
        return f"{self.id} {self.category} {self.number} {self.imageNum}"


'''
categoryColor一般为空不要用，
'''


class ImgInstance():
    def __init__(self, id, category, number, categoryName=None, ist_attr=None, ist_dynamic_attr=None):
        # self.frameNum = frameNum  # frameNum用子物体的，因为一个实例会存在于连续真的多个数据中
        self.id = id
        self.category = category
        self.categoryName = categoryName
        self.number = number
        # self.categoryColor = categoryColor # 不用这个属性
        self.ist_attr = DotDict(ist_attr) if ist_attr else DotDict()
        self.ist_dynamic_attr = DotDict(ist_dynamic_attr) if ist_dynamic_attr else DotDict()
        self.obj_list = []

    def __repr__(self):
        return f"{self.id} {self.category} {self.number} {len(self.obj_list)}T"

    def to_pre_dict(self):
        _pre_data_dict = {
            "id": self.id,
            "category": self.category,
            "number": self.number,
            "attributes": self.ist_attr,
            "children": [
            ]
        }

        ## 计算child_dict
        child_dict = dict()

        if self.obj_list[0].cam_name == "default":
            for item in self.obj_list:
                child_id = item.id
                if child_id not in child_dict:
                    child_dict[child_id] = {
                        "id": item.id,
                        "name": item.category,
                        "number": item.number,
                        "cameras": [{
                            "camera": "default",
                            "frames": []
                        }]
                    }
                ## 添加这条数据到frames信息中
                pre_item = {
                    "frameIndex": item.frameNum,
                    "isKeyFrame": True,
                    "shapeType": item.shapeType,
                    "shape": item.shape,
                    "order": item.order,
                    "attributes": item.img_attr,
                    "layer": item.layer
                }
                if item.isOCR is not None:
                    pre_item["isOCR"] = item.isOCR
                if item.OCRText is not None:
                    pre_item["OCRText"] = item.OCRText

                child_dict[child_id]["cameras"][0]["frames"].append(pre_item)

        else:
            for item in self.obj_list:
                child_id = item.id
                if child_id not in child_dict:
                    child_dict[child_id] = {
                        "id": item.id,
                        "name": item.category,
                        "number": item.number,
                        "cameras": [{
                            "camera": item.cam_name,
                            "frames": []
                        }]
                    }

                else:
                    child_cameras = [c["camera"] for c in child_dict[child_id]["cameras"]]
                    if item.cam_name not in child_cameras:
                        child_dict[child_id]["cameras"].append({
                            "camera": item.cam_name,
                            "frames": []
                        })

                ## 添加这条数据到frames信息中
                pre_item = {
                    "frameIndex": item.frameNum,
                    "isKeyFrame": True,
                    "shapeType": item.shapeType,
                    "shape": item.shape,
                    "order": item.order,
                    "attributes": item.img_attr,
                    "layer": item.layer
                }
                if item.isOCR is not None:
                    pre_item["isOCR"] = item.isOCR
                if item.OCRText is not None:
                    pre_item["OCRText"] = item.OCRText

                idx = [c["camera"] for c in child_dict[child_id]["cameras"]].index(item.cam_name)
                child_dict[child_id]["cameras"][idx]["frames"].append(pre_item)
        for _, v in child_dict.items():
            _pre_data_dict["children"].append(v)
        return _pre_data_dict


class Img2Dobj():
    def __init__(self, instance: ImgInstance,
                 frameNum, id, number, category,
                 shapeType, order=None, shape=None, img_attr=None,
                 displayName="", color="",
                 isOCR=None, OCRText=None, cam_name="default", layer=0, isRaw= None
                 ):
        self.instance = instance
        self.frameNum = frameNum
        self.id = id
        self.category = category
        self.displayName = displayName
        self.number = number
        self.color = color
        self.shapeType = shapeType
        self.shape = DotDict(shape) if shape else DotDict()
        self.order = order
        self.img_attr = DotDict(img_attr) if img_attr else DotDict()
        self.isOCR = isOCR
        self.OCRText = OCRText
        self.cam_name = cam_name
        self.layer = layer
        if isRaw is not None:
            self.isRaw = isRaw

    def get_bbox(self):
        # xmin ymin w h

        if self.shapeType != 'rectangle':
            raise Exception("非矩形框请不要使用bbox")
        else:
            return [
                self.shape["x"], self.shape["y"],
                self.shape["width"], self.shape["height"]
            ]

    def get_dig_points(self):
        '''
        对角线点，左上角点和右下角点,2*2 数组
        '''
        if self.shapeType != 'rectangle':
            raise Exception("非矩形框请不要使用对角坐标")
        else:
            return [
                [self.shape["x"], self.shape["y"]],
                [self.shape["x"] + self.shape["width"], self.shape["y"] + self.shape["height"]]
            ]

    def __repr__(self):
        return f"F{self.frameNum} {self.id} {self.category} {self.number} {self.shapeType} Order:{self.order} <-[{self.instance.category}]"


class AudioCutObj():
    def __init__(self, frameNum, id, number, start, end, block_attr, line_contents, category=""):
        self.frameNum = frameNum
        self.id = id
        self.number = number
        self.category = category
        self.start = start
        self.end = end
        self.block_attr = DotDict(block_attr) if block_attr else DotDict()
        self.line_contents = line_contents  # 对应content字段

    def __repr__(self):
        return f"{self.id} {self.category} {self.number} {self.start} {self.end}"


# type points 点,polyline 线
# pointCount 最好根据数组长度重新算下
# 点云分割只有实例模式
'''
pointsLabels
[ 
    [
       12.747154235839844,
       5.126907825469971,
       -1.3931894302368164,
       86
    ],
    ...
]
'''


class LidarPointObj():
    def __init__(self, frameNum, id, category, number, points, point_attr, pointsLabels, pointCount, type, pointsInfo):
        self.frameNum = frameNum
        self.id = id
        self.category = category
        self.number = number
        self.points = points
        self.point_attr = point_attr
        self.pointsLabels = pointsLabels  # 这个是点的 坐标和反射率信息的数组
        self.pointCount = pointCount
        self.type = type  # 平台工具多变形，笔刷，单点，都是point,折线是polyline
        self.pointsInfo = pointsInfo

    def __repr__(self):
        return f"{self.id} {self.category} {self.number} {len(self.points)}P"


class LidarPointPolyline():
    def __init__(self, frameNum, imageNum, id, number, type, category, points,
                 img_attr=None):
        self.frameNum = frameNum
        self.imageNum = imageNum  # 图像的次序。从0开始
        self.id = id
        self.number = number
        self.type = type
        self.category = category
        self.points = points
        self.img_attr = img_attr  # 属性

    def to_dict(self):
        _data_dict = {
            "type": self.type,
            "id": self.id,
            "number": self.number,
            "category": self.category,
            "points": self.points,
            # "labels": "" if self.img_attr is None else json.dumps(self.img_attr, ensure_ascii=False),
            "labels": json.dumps(self.img_attr, ensure_ascii=False) if self.img_attr is None else "",
        }
        return _data_dict

    def __repr__(self):
        return f"{self.id} {self.category} {self.number} {self.imageNum}"


class CommonBaseMixIn():
    session = get_session(3)

    def parse_from_private_path(self, private_path):
        private_path = private_path.replace("appen://", "")
        route_list = private_path.split("/")
        bucket_name = route_list[0]
        private_real_path = '/'.join(route_list[1:])
        assert private_real_path != '', 'real_path为空'
        return bucket_name, private_real_path

    def get_raw_data(self, url):
        if url.startswith(("http://", "https://")):
            rs = self.session.get(url).json()
            return rs
        elif url.startswith("appen://appen-platform"):
            auth = oss2.Auth(os.getenv("MATRIXGO_RESULT_KEY"), os.getenv("MATRIXGO_RESULT_SECRET"))
            oss_session = OssSession()
            if url.startswith("appen://appen-platform-dev"):
                bucket = oss2.Bucket(auth, "http://oss-cn-zhangjiakou.aliyuncs.com", "appen-platform-dev",
                                     session=oss_session)
            else:
                bucket = oss2.Bucket(auth, "http://oss-cn-hangzhou.aliyuncs.com", "appen-platform", session=oss_session)
            _, private_real_path = self.parse_from_private_path(url)
            rs = json.loads(bucket.get_object(private_real_path).read())
            return rs
        else:
            raise Exception("请检查annotation数据路径")

    def get_raw_data_by_oss_api(self, url,oss_client=None):
        url = unquote(url).split("?Expires=")[0]
        assert url.startswith("https://appen-data.oss-cn-shanghai.aliyuncs.com/"), "http bucket error"
        oss_key = url.replace("https://appen-data.oss-cn-shanghai.aliyuncs.com/", "")
        # oss_api = OSS_STS_API(bucket_name="appen-data")
        if not oss_client:
            oss_client=OSS_STS_API(bucket_name="appen-data")
        rs = json.loads(oss_client.bucket.get_object(oss_key).read())
        return rs

    def get_oss_data(self, url):
        auth = oss2.Auth(os.getenv("PE_OSS_AK"), os.getenv("PE_OSS_SK"))
        bucket = oss2.Bucket(auth, "http://oss-cn-hangzhou.aliyuncs.com", "tool-prod")
        if url.startswith("https://oss-prd.appen.com.cn:9001/tool-prod/"):
            oss_key = url.split("https://oss-prd.appen.com.cn:9001/tool-prod/")[1]
            rs = json.loads(bucket.get_object(oss_key).read())
            return rs
        elif url.startswith("https://tool-prod.oss-cn-hangzhou.aliyuncs.com/"):
            oss_key = url.split("https://tool-prod.oss-cn-hangzhou.aliyuncs.com/")[1]
            rs = json.loads(bucket.get_object(oss_key).read())
            return rs
        else:
            raise Exception("请检查annotation数据路径")


import math


def gen_format_progress_seq(total, split_part=10):
    ###初始化
    total = total  # 总的数量
    split_part = split_part  # 分片数量
    every_part_num = math.ceil(total / split_part)  # 总打印的分片数量

    finish = 0  # 当前完成的数量
    finish_part = 0  # 分配开始的进度数量

    # 分片数量，假如 总量是102，分片是10
    def update(step=1):
        nonlocal finish, finish_part
        finish += step  # 每调用一次 加1
        if finish // every_part_num > finish_part and finish // every_part_num <= split_part:
            finish_part += 1  # 分片数量加 1
            print("[", ("*" * finish_part).ljust(split_part, "_"), "]")
        # 根据完成数量update进度

    return update


import time


def deco_execution_time(func):
    def wrapper(*args, **kw):
        t_begin = time.time()
        res = func(*args, **kw)
        t_end = time.time()

        if t_end - t_begin < 60:
            print('%s executed in %s (s)' % (func.__name__, round(t_end - t_begin, 2)))
        elif t_end - t_begin < 3600:
            print('%s executed in %s (min)' % (func.__name__, round((t_end - t_begin) / 60, 2)))
        else:
            print('%s executed in %s (h)' % (func.__name__, round((t_end - t_begin) / 3600, 2)))

        return res

    return wrapper


def remove_key_if_exists(info_dict: dict, rm_list: list):
    for rm_name in rm_list:
        if rm_name in info_dict:
            del info_dict[rm_name]

    return info_dict
