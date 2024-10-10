# -*- coding: UTF-8 -*-

'''
Author: rxu
Date: 2024-07-17 16:38
Short Description:

Change History:

'''

import urllib.parse

def get_clean_url(url):
    """
    获取纯净url

    类似
    https://appen-data.oss-cn-shanghai.aliyuncs.com/Sand%2FSand_MovingVehicle%2F20240628_135703770731%2F1054%2F202405181
    443393995530%2Fvelodyne_points%2Fvelodyne64.pcd?Expires=1721959200&OSSAccessKeyId=LTAI5tB2Etp2wUEVtkT7zckM&Signature
    =uKI2Et1%2FDDYSXJg7YAVwe3sNp7o%3D
    转换为
    'https://appen-data.oss-cn-shanghai.aliyuncs.com/Sand/Sand_MovingVehicle/20240628_135703770731/1054/2024051814433939
    95530/velodyne_points/velodyne64.pcd'

    :param url:
    :return:
    """
    url = urllib.parse.unquote(url)
    parsed_url = urllib.parse.urlparse(url)
    clean_url = urllib.parse.urlunparse(parsed_url._replace(query=""))
    return clean_url