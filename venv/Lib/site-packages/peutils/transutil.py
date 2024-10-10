# -*- coding: UTF-8 -*-

'''
Author: Henry Wang
Date: 2022-04-21 16:11
Short Description:

Change History:

'''



def rectToBbox(shape:dict,adapter=None):
    '''
    平台的rectangle 类型转成 [x_min, y_min, w, h]
    如果是先取证，再转的话是 lambda i: int(round(i,0))
    :param shape:
    :param adapter:
    :return:
    '''
    points = shape['points']
    width = shape['width']
    height = shape["height"]
    assert width is not None and height is not None and points is not None,"rectangle长宽高和点不能为None"

    left_top = min(points,key=lambda i: (i["x"],i["y"]))
    x = left_top["x"]
    y = left_top["y"]

    if adapter is None:
        return x,y ,width,height
    else:
        return adapter(x),adapter(y),adapter(width),adapter(height)


def pointsToList(points:list,adpter=None):
    assert points is not None,"points不能为None"

    if adpter is None:
        return [[ p["x"], p["y"]] for p in points]
    else:
        return  [[ adpter(p["x"]), adpter(p["y"])] for p in points]


