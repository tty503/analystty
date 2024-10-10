# -*- coding: UTF-8 -*-

'''
Author: Henry Wang
Date: 2021-09-18 13:09
Short Description:

Change History:

'''

def remove_key_if_exists(info_dict: dict, rm_list: list):
    for rm_name in rm_list:
        if rm_name in info_dict:
            del info_dict[rm_name]
    return info_dict


def get_name_without_suffix_from_path(path_like, ignore=False):
    # print(path_like)
    name = path_like.split("/")[-1]
    if ignore == False:
        assert name.count(".") == 1, "文件名存在多个.后缀或者没有.，请确认处理方式"
        name_without_suffix = name.split(".")[0]
    else:
        name_without_suffix = '.'.join(name.split(".")[:-1])
    return name_without_suffix
