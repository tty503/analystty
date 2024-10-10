# -*- coding: UTF-8 -*-

'''
Author: Henry Wang
Date: 2022-06-03 06:38
Short Description:

Change History:

'''
from peutils.transform.v1.lidar_box.parser import LidarBoxParse,LidarBoxDataConfig
from peutils.transform.v1.task.executor import AbstractTask,CommonTaskV1

import logging
logging.basicConfig(level=logging.INFO)
import time
import random



class AfterParse(AbstractTask):

    def __init__(self,row,users_param=None):
        super().__init__(row,users_param)
        self.parse_obj = LidarBoxParse(row["annotation"], config=LidarBoxDataConfig(
                             yaw_only = True,
                             has_pointCount= True,
                             number_adpter_func=None, #lambda i: round(i,3), # 默认None
                             parse_id_col = "fid",
                             overflow= False
                         ))
        self.log.error_list.extend(self.parse_obj.check_frames_error())


    def check_row_on_a9(self) ->None:
        pass


        # self.log.create_error("发现错误")

    def check_row_addtional(self) ->None:
        pass




    def parse_row_func(self) ->None:
        logging.info("s")
        # print(self.log.error_list)
        # if len(self.log.error_list) >0:
        #     logging.error(self.log.error_list)
        # logging.error(self.log.error_list)

        # logging.debug("haha")
        # time.sleep(random.randint(1,10))
        # logging.info("_______ok_________ ")
        # from pprint import pprint
        # pprint(self.parse_obj.frames_lst[0].lidar_dict)

        # upload_group = self.row["upload_group"]
        # for frame in self.parse_obj.frames_lst:
        #     lidar_template = {
        #         "objects": []
        #     }
        #     for _,v in frame.lidar_dict.items():
        #         obj = {
        #             "id":""
        #         }





        # print(self.parse_obj.frames_lst)


        # print("_______ok_________")

#
# af = AfterParse(
#                 row={
#     "annotation":"http://oss.prd.appen.com.cn:9000/appen-lidar-prod/a019f71166e17533eb96741ebd0f0d0a/R.1653455556980.9f873b2b-71a8-4e85-9fef-9ec33e87d806.CMyfqgIQDw3d3d_2022-05-25T050329Z.49643.QA_RW.8b67819f-e6ad-4a1d-a087-1f35646a05fc.67f6a851b7317a4a1840f0b77f66703c.review.json"
# })
# af.parse_row_func()

### 并发执行
ct = CommonTaskV1(AfterParse)
ct.process_func("/Users/hwang2/Desktop/Result_2022-06-07T06_15_01.489694Z.csv",k1="v1",k2="v2")



