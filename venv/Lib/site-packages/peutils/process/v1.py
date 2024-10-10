# -*- coding: UTF-8 -*-

'''
Author: Henry Wang
Date: 2021-09-18 13:02
Short Description:

Change History:

'''

from abc import ABC,abstractmethod
import uuid
import os
import json
import traceback

def gen_uuid():
    uid = str(uuid.uuid4())
    suid = ''.join(uid.split('-'))
    return suid

class ErrorMsgLog():

    def __init__(self):
        self.error_list = []

    def create_error(self,msg,obj_id=None,group_id=None,only_group=False,frame_lst=None,block=True):
        '''
        如果plss模版，那么可以增加"info":{objectId:xx,groupId:xx}
        其他的直接使用obj_id即可
        '''
        plss_info=dict()

        if obj_id is None:
            obj_id = "common_" + gen_uuid()
        else:
            plss_info["objectId"] = obj_id

        if group_id is not None:
            plss_info["groupId"] = group_id

        if frame_lst is None:
            frame_lst = [0]

        err = {
            "id":obj_id,
            "message":msg,
            "frames":frame_lst,
            "blockSubmit":block
        }

        if plss_info !=dict():
            err["info"] = plss_info

        self.error_list.append(err)

    @staticmethod
    def single_errro(e)->str:

        base = f'''Id:{e["id"]}, Msg:{e["message"]}'''
        #如果frame是0，不打印。
        if e["frames"]==[0]:
            pass
        else:
            base += f", Frame:{repr(e['frames'])}"
        if e.get("info") is not None:
            if e["info"].get("groupId") is not None:
                base += f", Group:{e['info']['groupId']}"

        return base


    def fomart_error(self)->[]:
        return [self.single_errro(e) for e in self.error_list]
        # 如果frame是0，不打印。


class AbstractProcess(ABC):
    log = None

    def __init__(self,file,row_dict, users_param=None,split_frame_idx=None):
        self.file = file
        self.row_dict = row_dict
        self.users_param = users_param if users_param is not None else {}
        self.log = ErrorMsgLog()  # 这行的所有错误
        self.split_frame_idx = split_frame_idx if split_frame_idx is not None else 0


    @abstractmethod
    def check_row_on_a9(self)->None:
        """a9只能通过annotation进行检查 将内容输出到log"""

    @abstractmethod
    def check_row_addtional(self)->None:
        """额外的内容检查 将内容输出到log """

    def check_row_func(self,check_mode="all"): #check分a9的
        if self.log is None or isinstance(self.log,ErrorMsgLog) ==False:
            raise Exception("请定义log 并且使用ErrorMsgLog的实例")
        else:
            if check_mode=="a9_check":
                self.check_row_on_a9()
                return self.log.error_list  ##直接返回对象
            elif check_mode == "all":
                self.check_row_on_a9()
                self.check_row_addtional()
                return self.log.fomart_error() ##做格式化
            else:
                self.log.create_error(msg="未定义的check_mode")
                return self.log.fomart_error

    @abstractmethod
    def parse_row_func(self)->(str,str,str): # 输入的是json字符串.注意在方法中只使用annotation不要使用其他的参数
        """实现自定义的 parse_row_func方法  应该返回相对保存路径，保存文件名和 json的内容字字符串"""


def handler_by_cls(context, event,cls):

    code = 0  # code 200代表成功
    msg = ""
    errors = []
    output={}
    save_path = ""
    from_cache = False

    try:
        payload = event.body  # 这个会自动转成dict
        assert payload["mode"] in {"a9_check","parse","save"},"模式不对"

        h = cls(
            file=payload.get("file",""),
            row_dict=payload["data"]["row_dict"],
            users_param=payload["data"].get("users_param",None),
            split_frame_idx = payload["data"].get("split_frame_idx",None)
        )

        if payload["mode"] =='a9_check':
            check_errors = h.check_row_func(check_mode="a9_check")
            errors.extend(check_errors)  # 将错误添加到errors.
            if len(errors) ==0:
                code =200
        else: ## 这里就是parse和save两种情况
            check_errors = h.check_row_func()
            errors.extend(check_errors)
            if len(errors)!=0:
                #存在错误则不再转换
                pass
            else:
                use_cache = payload.get("use_cache",False)# 是否使用缓存
                # 缓存使用 version + data字符串作为key  output作为值

                # outdir = ""  # 相对路径
                # outfilename="" # 文件名
                # json_str="" # 内容

                if use_cache == True:
                    v_key = context.user_data.version + json.dumps(payload["data"], ensure_ascii=False)
                    v_value = context.user_data.my_redis.get(v_key)
                    if v_value is not None:
                        outdir, outfilename, json_str = json.loads(v_value)  # 存在redis中的就是这三个
                        from_cache = True
                    else:
                        outdir, outfilename, json_str = h.parse_row_func()
                        context.user_data.my_redis.set(v_key,
                                                       json.dumps([outdir, outfilename, json_str], ensure_ascii=False),
                                                       ex=86400)
                else:
                    outdir, outfilename, json_str = h.parse_row_func()

                if payload["mode"] == "parse":
                    output = {
                        "outdir": outdir,
                        "outfilename": outfilename,
                        "json_str": json_str
                    }
                elif payload["mode"] == "save":  ### 根据传入的路径保存文件
                    save_dir = payload.get("save_dir","")
                    assert save_dir!= "", "保存路径不能为空"
                    save_path = os.path.join(save_dir, outdir)
                    output = {
                        "outdir": outdir,
                        "outfilename": outfilename,
                    }
                    os.makedirs(save_path, exist_ok=True)
                    with open(os.path.join(save_path, outfilename), "w", encoding='utf-8') as fw:
                        fw.write(json_str)

                ##成功后更新code
                code = 200
                msg = "success"

    except:
        errors.append(traceback.format_exc())
    finally:
        # print(save_path)
        return context.Response(
            body={
                "code": code,
                "msg": msg,
                "version":"v1",
                "output":output,
                "save_path":save_path,
                "from_cache":from_cache,
                "errors":errors
            },
            headers={},
            content_type='application/json',  # text/plain
            status_code=200
        )