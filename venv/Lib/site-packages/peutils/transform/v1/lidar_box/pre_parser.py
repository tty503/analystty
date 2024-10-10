# -*- coding: UTF-8 -*-

'''
Author: Henry Wang
Date: 2022-06-01 15:33
Short Description:

Change History:


主要用于预处理的数据转成平台的格式,平台最少的数据格式
注意单帧合并成连续帧的时候，id不同，number也不能一样， id和number必须一一对应的。(特别是全局编号的模式下，id和number是一一对应的)

{

	"frames": [{
		"frameId": 0,
		"items": [{
			"id": "669b1f5a-8eeb-40fe-8945-2dd8cec688a1",
			"number": 1,
			"position": {
				"x": -2.9164659842583536,
				"y": -51.38931599127634,
				"z": -1.8388888888888877
			},
			"rotation": {
				"x": 0,
				"y": 0,
				"z": -1.6618072479377624
			},
			"dimension": {
				"x": 4.2,
				"y": 1.8,
				"z": 1.6
			},
			"category": "轿车",
			"labels": "...json字符串..."
		}],
		"images": [
			{
				"items": [{
					"type": "RECT",
					"id": "669b1f5a-8eeb-40fe-8945-2dd8cec688a1",
					"number": 1,
					"category": "轿车",
					"position": {
						"x": 944.9714187283353,
						"y": 712.9711061567027
					},
					"dimension": {
						"x": 71.2262093020197,
						"y": 58.792783067844766
					},
					"labels": "...json字符串..."

				}]
			}]


	}]

}

'''
from peutils.transform.v1.base import *
import json




class LidarBoxPre():
    ### 输入连续帧数量
    ### 镜头顺序，可根据新数据的manifest读取

    def __init__(self,frame_length,camera_list):
        self.frame_length = frame_length
        self.camera_list = camera_list  # 镜头顺序，可以从新的数据中取到。如果变换了之后可能会影响到数据的
        self.frame_list = [{
                                "frameId":i,
                                "items":[],
                                "images":[
                                    {
                                        "items":[]
                                    }
                                          for j in range(len(self.camera_list))]
                            } for i in range(self.frame_length)]  # 写完后的完整数据

    def add_lidar_obj(self,frameNum,lidar_obj):
        self.frame_list[frameNum]["items"].append(
            lidar_obj.to_dict()
        )

    def add_img_obj(self,frameNum,camera,img_obj):
        cam_idx = self.camera_list.index(camera)
        self.frame_list[frameNum]["images"][cam_idx]["items"].append(
            img_obj.to_dict()
        )

    def add_frame_obj(self, frameNum, **kwargs):
        # 指定帧数预处理"帧属性"、"(非)关键帧"···等
        self.frame_list[frameNum].update(**kwargs)

    def dumps_data(self):
        out_dict = {
            "frames":self.frame_list
        }
        return json.dumps(out_dict,ensure_ascii=False)



if __name__ =="__main__":
    pass


    # from peutils.transform.v1.lidar_manifest.parser import LidarManifestParse,LidarManifestConfig
    # msft = LidarManifestParse(base_url="https://projecteng.oss-cn-shanghai.aliyuncs.com/3d_json/test_shuima/2022-05-20-09-38-20-04/json/2022-05-20-09-38-20-04_1_50",
    #                           config=LidarManifestConfig())
    # ldboxpre2 = LidarBoxPre(frame_length=msft.frame_length,camera_list=msft.camera_list)
    #
    # from peutils.transform.v1.lidar_box.parser import LidarBoxParse,LidarBoxDataConfig
    # parse_obj = LidarBoxParse(url="https://projecteng.oss-cn-shanghai.aliyuncs.com/3d_json/test_shuima/2022-05-20-09-38-20-04/R.1655858875766.202.19671_2022-06-21T202615Z.599.QA_RW.27895.0f0425a96442183be87772da04b197a0.review.json",
    #                               config=LidarBoxDataConfig(
    #                                   yaw_only=False,
    #                                   has_pointCount=False,
    #                                   number_adpter_func=None,  # lambda i: round(i,3), # 默认None
    #                                   parse_id_col="id",
    #                                   seq_start=0,  # 如果是 gid,fid,或者frame_id 需要提供seq_start， 如果是0就是从1开始编号，如果是-1就是从0开始编号
    #                                   overflow=True
    #                               )
    # )
    # for _,lidar in parse_obj.frames_lst[0].lidar_dict.items():
    #     # lidar.p
    #     if lidar.dimension["x"] < lidar.dimension["y"]:
    #         new_x = lidar.dimension["y"]
    #         new_y = lidar.dimension["x"]
    #         lidar.dimension["x"]  = new_x
    #         lidar.dimension["y"] = new_y
    #
    #     ldboxpre2.add_lidar_obj(frameNum=0,lidar_obj=lidar)
    # for camera, img_dict in parse_obj.frames_lst[0].images_dict.items():  ##注意 这个cemra不一定准确
    #     for k,v in img_dict.items():
    #     # print(camera,img)
    #         ldboxpre2.add_img_obj(frameNum=0, camera=camera, img_obj=v)
    # # print(ldboxpre2)
    #
    #
    # print(ldboxpre2.dumps_data())
    # with open("review_replace_xy.json","w",encoding="utf-8") as f:
    #     f.write(ldboxpre2.dumps_data())



    # ldboxpre = LidarBoxPre(frame_length = 50,camera_list=['front_middle_camera', 'lf_wide_camera', 'lr_wide_camera', 'rear_middle_camera', 'rf_wide_camera', 'rr_wide_camera'])
    # print(ldboxpre.dumps_data())

    # self.frames = {}

    ### 在0，0，0 点 写入一个 长宽高
    # from peutils.transform.v1.lidar_manifest.parser import LidarManifestParse,LidarManifestConfig
    # from peutils.transform.v1.base import Lidar3dObj
    # ldboxpre3 = LidarBoxPre(frame_length=1, camera_list=[])
    # ldboxpre3.add_lidar_obj(frameNum=0, lidar_obj=Lidar3dObj(
    #     frameNum=0,
    #     id="1",
    #     number=1,
    #     category="Car",
    #     position={"x":0,"y":0,"z":0},
    #     rotation={"x":0,"y":0,"z":0},
    #     dimension={"x":20,"y":5,"z":1}
    # ))
    # print(ldboxpre3.dumps_data())


