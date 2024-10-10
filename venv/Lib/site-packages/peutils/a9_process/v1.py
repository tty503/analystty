# -*- coding: UTF-8 -*-

'''
Author: Henry Wang
Date: 2021-09-22 11:19
Short Description:

Change History:

'''
# -*- coding: UTF-8 -*-

'''
Author: Henry Wang
Date: 2021-09-02 14:09
Short Description:

Change History:




'''

import asyncio
import aiohttp
import uvloop
import os,sys
import pandas as pd
import json
import csv


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


def gen_uuid():
    import uuid
    uid = str(uuid.uuid4())
    suid = ''.join(uid.split('-'))
    return suid

def saveCsvData(savePath, data: list, header=None, newline='\n'):
    csv.field_size_limit(500 * 1024 * 1024)
    with open(savePath, 'w', encoding='utf-8-sig', newline=newline) as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL, lineterminator="\n")
        if header:
            writer.writerow(header)
        writer.writerows(data)


'''
输入 
    a9的csv 
    a9不支持其他参数的输入
'''




class A9CommonDataParseV1():
    project_desc = None
    need_process_suffix = ".csv"
    # other_params =dict()

    cols = ["Batch Num", "Record ID", "annotation"]
    parse_url = None

    ###以下参数一般不要改
    headers = {"Content-Type": "application/json"}
    async_task_nums = 1
    mode="parse"



    def __init__(self):
        self.temp_dir,self.work_dir = self.get_temp_dir_and_work_dir()
        self.resource_file = sys.argv[1]


    def get_temp_dir_and_work_dir(self):
        temp_dir = os.getcwd()
        resut_dir = os.path.join(temp_dir, "result")
        return temp_dir, resut_dir

    # 获取所有需要处理的任务，然后把任务加到任务池
    def get_all_tasks(self,taks_files):
        for file in taks_files:
            df = pd.read_csv(file,encoding='utf-8-sig')
            for _,row in df.iterrows():
                yield file, row,None # 最后一个是split_frame_idx

    async def request_data(self,session, url, data):
        async with session.post(url, json=data, headers=self.headers) as resp:
            # print(resp.status)
            rs = await resp.text()
            return resp.status, rs

    async def request_data_with_retry(self,session, url,data):
        tries = 3
        while tries > 0:
            try:
                return await self.request_data(session, url, data)
            except aiohttp.ClientResponseError:
                if tries <= 0:
                    raise Exception("请求错误超过3次")
            tries -= 1

    ### 执行单个异步任务，根据具体的业务覆盖这个方法
    async def process_func(self,file,task_row,split_frame_idx,semaphore):
        async with semaphore:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "file":file,
                    "data":{
                        "row_dict": task_row[self.cols].to_dict(),
                        "split_frame_idx": split_frame_idx,
                    },
                    "mode":self.mode,
                }
                statu,rs = await self.request_data_with_retry(session, url=self.parse_url, data=payload)

                return file,task_row,statu,rs  # 文件名，原始行数据，以及API返回的结果

    def get_process_task_files(self,inputfilename):

        assert self.need_process_suffix.endswith(".csv")==True,"必须是csv格式"
        if inputfilename.endswith(self.need_process_suffix):
            return [inputfilename]
        else:
            return []


    async def process_all_tasks(self,task_files):
        semaphore = asyncio.Semaphore(self.async_task_nums)
        task_list = []

        print("获取任务明细...")
        for file,task_row,split_frame_idx in self.get_all_tasks(task_files):
            task = asyncio.create_task(self.process_func(file,task_row,split_frame_idx,semaphore))
            task_list.append(task)
        print("总任务数量:",len(task_list))

        res = await asyncio.gather(*task_list)
        return res

    # @deco_execution_time
    def check_all_tasks_result(self):
        pass

    # @deco_execution_time
    def handler_tasks_result(self):
        pass

    def save_rs_on_a9(self,reloutdir,outfilename,json_str):
        json_dict = json.loads(json_str)
        os.makedirs(reloutdir,exist_ok=True)
        with open(os.path.join(reloutdir,outfilename),'w',encoding='utf-8') as fw:
            json.dump(json_dict,fw,ensure_ascii=False,indent=4)




    def main(self):
        print("start ...")
        task_files = self.get_process_task_files(self.resource_file)
        # task_files = self.get_process_task_files("/Users/hwang2/Downloads/result_report_A4141-Li66571_2021-08-03T08_00_07.010205Z[UTC].csv")

        # 异步执行所有任务并拿到结果
        print("ready to process taskfiles",task_files)
        res = asyncio.run(self.process_all_tasks(task_files))


        # 执行结果分析和处理 r如果有error 把错误写到csv文件中
        error_header = ["file","record_id","batch_num","image_url",'annotation','http_code',"errors"]
        error_lines = []

        for file,task_row,statu,rs in res:
            # print(file,task_row,statu,rs)
            record_id = task_row["Record ID"]
            batch_num = task_row["Batch Num"]
            image_url = task_row.get("image_url")
            annotation = task_row.get("annotation")
            http_code = statu
            if statu !=200:
                errors = "网络或接口异常"
                error_lines.append([file,record_id,batch_num,image_url,annotation,http_code,errors])

            else:
                rs_dict = json.loads(rs)
                if rs_dict["code"]!=200:
                    errors = json.dumps(rs_dict["errors"],ensure_ascii=False)
                    error_lines.append([file,record_id, batch_num, image_url, annotation, http_code, errors])
                else:
                    self.save_rs_on_a9(rs_dict["output"]["outdir"],rs_dict["output"]["outfilename"],rs_dict["output"]["json_str"])


        if len(error_lines)==0:
            print("未发现异常")
        else:
            print(f"发现异常{len(error_lines)}，请检查输出文件中的异常明细",file=sys.stderr)
            saveCsvData(os.path.join(self.temp_dir,f"ERROR_{gen_uuid()}.csv"),error_lines,error_header)




# class A9CommonAfter(A9CommonDataParseV1):
#     project_desc = "毫末2D鱼眼车道线后处理"
#     # need_process_suffix = ".csv"  # A9不支持其他 不需要改
#
#     # other_params = dict() #默认参数 不支持其他参数，不要改
#
#
#     cols = ["annotation","json_name","raw_json_result"]
#
#     # api_use_cache = False # 默认是False  默认即可不要改
#
#
#     # save_way = "" # A9没有保存差异的方式
#
#
#     # async_task_nums = 10  # 默认10 一般不需要改
#     parse_url = f"https://process-api.appen.com.cn/haomo-2d-fisheye"
