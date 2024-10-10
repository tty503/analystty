# -*- coding: UTF-8 -*-

'''
Author: Henry Wang
Date: 2022-06-29 13:08
Short Description:

Change History:

'''
import cv2
import math
import numpy as np
from sympy import Line3D, Point3D, Plane
from scipy.spatial.transform import Rotation
from peutils.transform.v1.base import DotDict

isDict = lambda d, keys="xyz": [d[k] for k in keys] if isinstance(d, dict) else d
# ADJACENT_POINTS_MAP = {
#     "pe": {0: {1, 2, 5}, 1: {0, 3, 4}, 2: {0, 3, 7}, 3: {1, 2, 6}, 4: {1, 5, 6}, 5: {0, 4, 7}, 6: {3, 4, 7}, 7: {2, 5, 6}},
#     "a9": {0: {1, 2, 5}, 1: {0, 3, 4}, 2: {0, 3, 7}, 3: {1, 2, 6}, 4: {1, 5, 6}, 5: {0, 4, 7}, 6: {3, 4, 7}, 7: {2, 5, 6}},
# }
PLANE_MAPPING = {
    "pe": {
        "4567": {4: 1, 5: 0, 6: 3, 7: 2}, "0123": {0: 5, 1: 4, 2: 7, 3: 6},  # 前 后
        "0257": {0: 1, 2: 3, 5: 4, 7: 6}, "1346": {1: 0, 3: 2, 4: 5, 6: 7},  # 左 右
        "0145": {0: 2, 1: 3, 4: 6, 5: 7}, "2367": {2: 0, 3: 1, 6: 4, 7: 5}   # 上 下
    },
    "a9": {
        "0123": {0: 5, 1: 4, 2: 7, 3: 6}, "4567": {4: 1, 5: 0, 6: 3, 7: 2},  # 前 后
        "0145": {0: 2, 1: 3, 4: 6, 5: 7}, "2367": {2: 0, 3: 1, 6: 4, 7: 5},  # 左 右
        "0257": {0: 1, 2: 3, 5: 4, 7: 6}, "1346": {1: 0, 3: 2, 4: 5, 6: 7}   # 上 下
    }
}

def get_abs_cube_points_list(*args, quaternion, position, dimension, axis="pe"):
    '''axis==pe初次框顶点顺序
    平台上看物体的方向，默认视角下，红色y 超做

    平台默认坐标系下， x(蓝色) 朝前， y(红色) 朝左， z(绿色) 朝上。对于空间中的点顺序信息应该下面这样的表示
    ## 矩形框的8个点是这样的，注意坐标系! 这个坐标系y朝左的
               z
               -     y
               -    -
               0 # # # # # # # #5
              #-  -            ##
             # - -            # #
            1 # # # # # # # #4  #
            #  2 - - - - - -#- -7 - - ->x
            #  -            #   #
            # -             #  #
            #-              # #
            3 # # # # # # # #6
    注意仅用于平台的坐标检查和平台的映射，使用在其他场景下，注意坐标系可能是不一样的
    '''
    l, w, h = isDict(dimension)
    ### 物体相对于中心点的坐标
    if axis == "pe":
        vertexX = [-l / 2, -l / 2, -l / 2, -l / 2, l / 2, l / 2, l / 2, l / 2]
        vertexY = [w / 2, -w / 2, w / 2, -w / 2, -w / 2, w / 2, -w / 2, w / 2]
        vertexZ = [h / 2, h / 2, -h / 2, -h / 2, h / 2, h / 2, -h / 2, -h / 2]
        # plane_mapping = {"4567": "前", "0123": "后", "0257": "左", "1346": "右", "0145": "上", "2367": "下"}

    elif axis == "a9":
        """A9平台计算顶点顺序
            point index as below
                  y
                  |
                  4____1
                5/___0/|
                | 6__|_3____ x
                7/___2/
               /
            z/
        """
        vertexX = [l / 2, -l / 2, l / 2, -l / 2, -l / 2, l / 2, -l / 2, l / 2]
        vertexY = [w / 2, w / 2, w / 2, w / 2, -w / 2, -w / 2, -w / 2, -w / 2]
        vertexZ = [h / 2, h / 2, -h / 2, -h / 2, h / 2, h / 2, -h / 2, -h / 2]
        # plane_mapping = {"0123": "前", "4567": "后", "0145": "左", "2367": "右", "0257": "上", "1346": "下"}

    ### 计算旋转矩阵
    m1 = Rotation.from_quat(isDict(quaternion, keys="xyzw")).as_matrix()

    ###根据中心点进行矩线性变换，并且加上原来中心点位置得到空间坐标点位置
    point_arr = np.dot(m1, [vertexX, vertexY, vertexZ]).T + np.array(isDict(position))
    #### 保留6为小数
    # print(point_arr.tolist())
    # print( np.around(point_arr,6))
    return point_arr


def lidar_pos_to_camera_pos(*args, lidar_pos, external_arr):
    '''3D框单个顶点
    ### 用于3D坐标系下的点云位置，转到相机坐标系的三维位置
    '''
    camera_pos = np.dot(external_arr, np.array([
        [lidar_pos[0]], [lidar_pos[1]], [lidar_pos[2]], [1]
    ]))
    return [camera_pos[0][0], camera_pos[1][0], camera_pos[2][0]]


# camera_pos = lidar_pos_to_camera_pos(lidar_pos =[12.620720042768912, 3.6885788192013638,1],external_arr=reflect_t)
# print("camera_pos",camera_pos)  # [-3.368023051808521, -1.0938639012445723, 12.48499963630992]


def camera_pos_to_image_loc(*args, camera_pos, internal_arr, adapter=None, model="pinhole"):
    '''
        ####用于将相机坐标系转到2D
        # 先通过上面的方法拿到相机坐标系
        # 再计算图像中的平面位置
        "p": [
            [
                cam_fx, 0 , cam_cx, 0
            ],
            [
                0 , cam_fy, cam_cy, 0
            ],
            [
                0, 0, 1, 0
            ]
        ]
        ix = fx * x / z + cx
        iy = fy * y / z + cy

        ### 鱼眼 内参
        {
            "fx": 506.084470,
            "fy": 508.358641,
            "cx": 996.711571,
            "cy": 653.682533,
            "k1": 0.146539,
            "k2": -0.054121,
            "k3": 0.009412,
            "k4": -0.001171,
        }
    '''
    if model == "pinhole":
        fx = internal_arr[0][0]
        fy = internal_arr[1][1]
        cx = internal_arr[0][2]
        cy = internal_arr[1][2]

        # print(fx, fy, cx, cy)

        ix = fx * camera_pos[0] / camera_pos[2] + cx
        iy = fy * camera_pos[1] / camera_pos[2] + cy
        if adapter is None:
            return (ix, iy)
        else:
            return (adapter(ix), adapter(iy))
    elif model == "fisheye":
        k1, k2, k3, k4 = internal_arr["k1"], internal_arr["k2"], internal_arr["k3"], internal_arr["k4"]
        fx, fy, cx, cy = internal_arr["fx"], internal_arr["fy"], internal_arr["cx"], internal_arr["cy"]
        a = camera_pos[0] / camera_pos[2]
        b = camera_pos[1] / camera_pos[2]
        r = math.sqrt(a ** 2 + b ** 2)
        theta = math.atan(r)
        thetaD = theta * (1 + k1 * (theta ** 2) + k2 * (theta ** 4) + k3 * (theta ** 6) + k4 * (theta ** 8))
        x1 = (thetaD / r) * a
        y1 = (thetaD / r) * b
        ix = fx * x1 + cx
        iy = fy * y1 + cy
        if adapter is None:
            return (ix, iy)
        else:
            return (adapter(ix), adapter(iy))


# image_locate = camera_pos_to_image_loc(camera_pos=[-3.368023051808521, -1.0938639012445723, 12.48499963630992],internal_arr=reflect_p)
# print("image_locate",image_locate)  # [678.9020866475078, 406.47439076926906]


def lidar_pos_to_camera_loc(*args, lidar_pos, internal_arr, external_arr, adapter=None, model="pinhole"):
    camera_pos = lidar_pos_to_camera_pos(lidar_pos=lidar_pos, external_arr=external_arr)
    image_locate = camera_pos_to_image_loc(camera_pos=camera_pos, internal_arr=internal_arr, adapter=adapter, model=model)
    return image_locate


# image_locate2 = lidar_pos_to_camera_loc(lidar_pos=[12.620720042768912, 3.6885788192013638,1],internal_arr=reflect_p,external_arr=reflect_t)
# print("image_locate from lidar pos",image_locate2)

def camera_pos8_truncated_to_z1(camera_pos8, axis="pe", **kwargs):
    '''
    相机8个顶点(可能存在被截断的顶点) ==> 相机8个顶点(被截断的顶点转到Z=1平面上)
    '''
    truncationPoints = {}  # 相机后被截断的顶点位置
    if isinstance(camera_pos8, np.ndarray) or isinstance(camera_pos8, list):
        camera_pos8_dict = {}
        for idx, cameraP in enumerate(camera_pos8):
            camera_pos8_dict[idx] = cameraP
            if cameraP[2] < 0.1:  # 平台默认0.1 (const filterDistance = 0.1;)
                truncationPoints[idx] = cameraP  # z<0.1的被认为截断的顶点
    elif isinstance(camera_pos8, dict):
        camera_pos8_dict = camera_pos8
        for idx, cameraP in camera_pos8.items():
            if cameraP[2] < 0.1:  # 平台默认0.1 (const filterDistance = 0.1;)
                truncationPoints[idx] = cameraP  # z<0.1的被认为截断的顶点
    else:
        raise TypeError("camera_pos8 类型支持 [np.ndarray, list, dict]")

    if 0 < len(truncationPoints):
        # 确定截断面
        minZ_to_maxZ = sorted(camera_pos8_dict.items(), key=lambda i: i[1][2], reverse=False)
        minZ_4 = minZ_to_maxZ[:4]
        minZ_4.sort(key=lambda i: i[0])
        truncationPlane = "".join([str(i[0]) for i in minZ_4])
        adjacentPointMap = PLANE_MAPPING[axis][truncationPlane]  # 截断面的顶点 及 对面相邻顶点

        camera_z1_plane = Plane(Point3D(0, 0, 1), normal_vector=(0, 0, 1))  # 创建一个三维平面z=1
        for pointIdx, truncationPoint in truncationPoints.items():
            if adjacentPointMap.get(pointIdx) is None:
                # ⚠️截断顶点>4时continue，平台投影不出这种框
                continue
            # 确认线段：截断点 与 相邻未截断点的线段
            line = Line3D(Point3D(truncationPoint), Point3D(camera_pos8_dict[adjacentPointMap[pointIdx]]))
            # 计算 线段 与 z=1平面 交点
            intersection = camera_z1_plane.intersection(line)
            if intersection:
                p = intersection[0]  # 获取第一个交点
                camera_pos8_dict[pointIdx] = [p[0].evalf(), p[1].evalf(), p[2].evalf()]
    return list(camera_pos8_dict.values())


def lidar_item_to_image_pos8(quaternion, position, dimension, external_arr, internal_arr, **kwargs):
    '''
    lidar8个顶点 ==> image8个顶点
    用于3D坐标系下的点云位置，转到图像坐标系的像素位置
    '''
    model = kwargs.get("model", "pinhole")
    axis = kwargs.get("axis", "pe")
    adapter = kwargs.get("adapter", None)

    lidar_pos8 = get_abs_cube_points_list(position=position, dimension=dimension, quaternion=quaternion, axis=axis)
    camera_pos8 = {}  # 相机坐标系的顶点位置
    truncationPoints = {}  # 相机后被截断的顶点位置
    for idx, lidarP in enumerate(lidar_pos8):
        # 单个顶点 lidar到相机
        cameraP = np.dot(external_arr, np.array([lidarP[0], lidarP[1], lidarP[2], 1])).tolist()[:3]  # 相机顶点
        camera_pos8[idx] = cameraP
        if cameraP[2] < 0.1:  # 平台默认0.1 (const filterDistance = 0.1;)
            truncationPoints[idx] = cameraP  # z<0.1的被认为截断的顶点

    if 0 < len(truncationPoints):
        # 确定截断面
        minZ_to_maxZ = sorted(camera_pos8.items(), key=lambda i: i[1][2], reverse=False)
        minZ_4 = minZ_to_maxZ[:4]
        minZ_4.sort(key=lambda i: i[0])
        truncationPlane = "".join([str(i[0]) for i in minZ_4])
        adjacentPointMap = PLANE_MAPPING[axis][truncationPlane]  # 截断面的顶点 及 对面相邻顶点

        camera_z1_plane = Plane(Point3D(0, 0, 1), normal_vector=(0, 0, 1))  # 创建一个三维平面z=1
        for pointIdx, truncationPoint in truncationPoints.items():
            if adjacentPointMap.get(pointIdx) is None:
                # ⚠️截断顶点>4时continue，平台投影不出这种框
                continue
            # 确认线段：截断点 与 相邻未截断点的线段
            line = Line3D(Point3D(truncationPoint), Point3D(camera_pos8[adjacentPointMap[pointIdx]]))
            # 计算 线段 与 z=1平面 交点
            intersection = camera_z1_plane.intersection(line)
            if intersection:
                p = intersection[0]  # 获取第一个交点
                camera_pos8[pointIdx] = [p[0].evalf(), p[1].evalf(), p[2].evalf()]

    image_pos = [
        camera_pos_to_image_loc(camera_pos=camera_pos, internal_arr=internal_arr, model=model, adapter=adapter)
        for pIdx, camera_pos in camera_pos8.items()
    ]
    return image_pos


def cal_diff_num(num, max_num):
    # 根据当前值，分大和小的情况，最终返回差异范围
    if num < 0:
        return -num
    elif 0 <= num <= max_num:
        return 0
    elif num > max_num:
        return num - max_num


def get_expand(points_list, width, height):
    left_right_expand = 0
    up_down_expand = 0
    for item in points_list:
        left_right_over = cal_diff_num(int(item[0]), width)
        up_down_over = cal_diff_num(int(item[1]), height)

        left_right_expand = max(left_right_over, left_right_expand)
        up_down_expand = max(up_down_over, up_down_expand)

    if max(left_right_expand, up_down_expand) == 0:
        out_expand = 0
    else:
        # 多留60px余地
        out_expand = max(left_right_expand, up_down_expand) + 60
    return out_expand


def draw_line(img, pts_int, color=(255, 255, 0), thickness=1):
    # 顶点标序号
    [cv2.putText(img, str(i), vp, cv2.FONT_HERSHEY_TRIPLEX, 0.8, (255, 0, 255), 1) for i, vp in enumerate(pts_int)]
    cv2.line(img, pts_int[0], pts_int[1], color, thickness)
    cv2.line(img, pts_int[0], pts_int[2], color, thickness)
    cv2.line(img, pts_int[3], pts_int[1], color, thickness)
    cv2.line(img, pts_int[3], pts_int[2], color, thickness)

    cv2.line(img, pts_int[4], pts_int[5], color, thickness)
    cv2.line(img, pts_int[4], pts_int[6], color, thickness)
    cv2.line(img, pts_int[7], pts_int[5], color, thickness)
    cv2.line(img, pts_int[7], pts_int[6], color, thickness)

    cv2.line(img, pts_int[0], pts_int[5], color, thickness)
    cv2.line(img, pts_int[1], pts_int[4], color, thickness)
    cv2.line(img, pts_int[2], pts_int[7], color, thickness)
    cv2.line(img, pts_int[3], pts_int[6], color, thickness)


def point_to_img2(img_path, lidar_items, external_arr, internal_arr, **kwargs):
    from pathlib import Path

    model = kwargs.get("model", "pinhole")
    axis = kwargs.get("axis", "pe")
    adapter = kwargs.get("adapter", lambda p: int(p))  # cv2绘图必须int
    point_size = kwargs.get("point_size", 10)
    point_color = kwargs.get("point_color", (0, 255, 0))  # BGR
    thickness = kwargs.get("thickness", 1)

    save_path = kwargs.get("save_path", Path(img_path).name)  # img写入保存路径，默认不报错，imshow预览效果
    assert Path(save_path).suffix[0] == ".", "save_path保存路径必须指定文件"

    background = kwargs.get("background", False)
    img_w = kwargs.get("img_w", None)
    img_h = kwargs.get("img_h", None)
    if background is True:  # ⚠️当background===True时，运行可能缓慢
        assert img_w and img_h, "制作黑布绘图必须指定图片宽(img_w)高(img_h)参数"

    img = cv2.imread(img_path)
    if background:
        image_pos8_list = []
        for item in lidar_items:
            image_pos8 = lidar_item_to_image_pos8(
                position=item["position"], dimension=item["dimension"], quaternion=item["quaternion"],
                external_arr=external_arr, internal_arr=internal_arr, model=model, axis=axis, adapter=adapter
            )
            image_pos8_list.append(image_pos8)
        # 左右上下都加同样的expand
        expand = 0
        for img_p8 in image_pos8_list:
            out_expand = get_expand(image_pos8, width=img_w, height=img_h)
            expand = max(out_expand, expand)  # ⚠️expand有上限，暂不确定最大为多少，不能过万，否则不生成图片
        # 绘制最大的黑布
        img_max = np.zeros((img_w + (expand * 2), img_h + (expand * 2), 3), np.uint8)
        if expand > 0:
            # 原图放在黑布中央
            img_max[expand: -expand, expand: -expand] = img
        else:
            img_max = img
        for img_p8 in image_pos8_list:
            # 点也要加expand
            draw_line(img=img_max, pts_int=[(p[0] + expand, p[1] + expand) for p in img_p8], color=point_color, thickness=thickness)

        cv2.imwrite(save_path, img_max)  # 最后输出时，保留边缘的黑布。不保留和cv2直接绘制效果一样，可以background=True即可
        # cv2.imshow('Lidar2Image', img_max)
        # cv2.waitKey()
    else:
        for item in lidar_items:
            image_pos8 = lidar_item_to_image_pos8(
                position=item["position"], dimension=item["dimension"], quaternion=item["quaternion"],
                external_arr=external_arr, internal_arr=internal_arr, model=model, axis=axis, adapter=adapter
            )
            draw_line(img=img, pts_int=image_pos8, color=point_color, thickness=thickness)
        cv2.imwrite(save_path, img)  # 不保留，和cv2直接绘制效果一样
        # cv2.imshow('Lidar2Image', img)
        # cv2.waitKey()


if __name__ == '__main__':
    pass
    # #### 平台的内参是p, 外参是t, 以下以wz为例
    # reflect_t = [
    #     [0.013008662021065768, -0.9998308106509982, 0.013004798552426648, -0.08963269786502702],
    #     [-0.16855299625924877, -0.015012435684566009, -0.9855782638770227, -0.23169931343217604],
    #     [0.9856067482340263, 0.010629056768325538, -0.16871977058947302, -0.5035080012889495],
    #     [0, 0, 0, 1]
    # ]  # 外参
    # reflect_p = [[990.3901353092, 0, 920.7098863878875, 0], [0, 990.3616928331, 518.2222635023165, 0], [0, 0, 1, 0]]  # 内参
    #
    # cameraCubes = [
    #     {  # 正常框
    #         "position": {"x": 3.5267498892287588, "y": 4.913005481472807, "z": -1.924160699171428},
    #         "dimension": {"x": 3.5, "y": 1.5, "z": 1.5},
    #         "quaternion": {"x": 0, "y": 0, "z": -0.9893870638906137, "w": 0.14530394972577523}
    #     },
    #     {  # 存在截断的框
    #         "position": {"x": -0.1701175599364254, "y": 0.09766359990450012, "z": -1.6868215081515596},
    #         "dimension": {"x": 3.5, "y": 1.5, "z": 1.5},
    #         "quaternion": {"x": 0, "y": 0, "z": 0.06819077841201075, "w": 0.9976722997756147}
    #     }
    # ]
    # # test 截断框
    # lidarVeters = get_abs_cube_points_list(position=cameraCubes[1]["position"], dimension=cameraCubes[1]["dimension"], quaternion=cameraCubes[1]["quaternion"], axis="pe")
    # print(f"get_abs_cube_points_list: {lidarVeters}\n")
    #
    # cameraPos = lidar_pos_to_camera_pos(lidar_pos=lidarVeters[0], external_arr=reflect_t)
    # print(f"lidar_pos_to_camera_pos: {cameraPos}\n")
    #
    # imagePos = camera_pos_to_image_loc(camera_pos=cameraPos, internal_arr=reflect_p, adapter=None, model="pinhole")
    # print(f"camera_pos_to_image_loc: {imagePos}\n")
    #
    # cameraPos1 = lidar_pos_to_camera_loc(lidar_pos=lidarVeters[0], internal_arr=reflect_p, external_arr=reflect_t, adapter=None, model="pinhole")
    # print(f"lidar_pos_to_camera_loc: {cameraPos1}\n")
    #
    # cameraPos_z1 = camera_pos8_truncated_to_z1(camera_pos8=[lidar_pos_to_camera_pos(lidar_pos=p, external_arr=reflect_t) for p in lidarVeters], axis="pe")
    # print(f"camera_pos8_truncated_to_z1: {cameraPos_z1}\n")
    #
    # imagePos8 = lidar_item_to_image_pos8(position=cameraCubes[1]["position"], dimension=cameraCubes[1]["dimension"], quaternion=cameraCubes[1]["quaternion"], internal_arr=reflect_p, external_arr=reflect_t)
    # print(f"lidar_item_to_image_pos8: {imagePos8}\n")
    #
    # point_to_img2(
    #     img_path=f"/Users/echai/Downloads/1677983341595289344.jpg",
    #     lidar_items=cameraCubes, external_arr=reflect_t, internal_arr=reflect_p,
    #     axis="a9", background=False, img_w=1080, img_h=1920
    # )
