# -*- coding: UTF-8 -*-

'''
Author: Henry Wang
Date: 2022-07-05 14:36
Short Description:

Change History:

'''
from peutils.transform.v1.tools.lidar import get_abs_cube_points_list

import numpy as np
import open3d as o3d
from peutils.transform.v1.base import deco_execution_time


def array_to_pointcloud(np_array):
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(np_array)
    return pcd

def conv_hull(points: np.ndarray):
    """
    生成凸包 参考文档：https://blog.csdn.net/io569417668/article/details/106274172
    :param points: 待生成凸包的点集
    :return: 索引 list
    """
    pcl = array_to_pointcloud(points)
    hull, lst = pcl.compute_convex_hull()
    return lst
    # '''
	# 这里的load_data_txt是我自己写的函数，主要是读入三维点坐标，返回list
	# array_to_point_cloud是用来把NdArray类型的点坐标转换成o3d.geometry.PointCloud类型的函数
    # '''

@deco_execution_time
def in_convex_polyhedron(points_set: np.ndarray, test_points: np.ndarray,x_range,y_range,z_range):
    """
    检测点是否在凸包内
    :param points_set: 凸包，需要对分区的点进行凸包生成 具体见conv_hull函数
    :param test_points: 需要检测的点 可以是多个点
    :return: bool类型
    """
    assert type(points_set) == np.ndarray
    assert type(test_points) == np.ndarray
    # bol = np.zeros((test_points.shape[0], 1), dtype=np.bool)
    bol = []
    ori_set = points_set
    ori_edge_index = conv_hull(ori_set)
    ori_edge_index = np.sort(np.unique(ori_edge_index))

    for i in range(test_points.shape[0]):
        # print(test_points[i])
        p = test_points[i]
        if (p[0]< x_range[0] or p[0]>x_range[1]) \
               or  (p[1]< y_range[0] or p[1]>y_range[1])  \
               or  (p[2]< z_range[0] or p[2]>z_range[1]) :
            bol.append(False)
            continue

        new_set = np.concatenate((points_set, test_points[i, np.newaxis]), axis=0)
        new_edge_index = conv_hull(new_set)
        new_edge_index = np.sort(np.unique(new_edge_index))
        # print(new_edge_index,ori_edge_index)
        # bol[i] = (new_edge_index.tolist() == ori_edge_index.tolist())
        bol.append(new_edge_index.tolist() == ori_edge_index.tolist())
    return bol


'''
输入
2. 完整的点的信息
3. 物体长宽高 中心点和旋转
输出
所有在这个框内的数据的index
'''
def get_idx_in_convex_polyhedron(test_points: np.ndarray, position, dimension, quaternion):
    """
    检测点是否在凸包内
    :param points_set: 凸包，需要对分区的点进行凸包生成 具体见conv_hull函数
    :param test_points: 需要检测的点 可以是多个点
    :return: bool类型
    """

    max_l = max(dimension.values()) / 2
    x_range = tuple([position["x"] - max_l, position["x"] + max_l])
    y_range = tuple([position["y"] - max_l, position["y"] + max_l])
    z_range = tuple([position["z"] - max_l, position["z"] + max_l])

    points8 = get_abs_cube_points_list(
        quaternion=quaternion,
        position=position,
        dimension=dimension
    )
    # assert type(points8) == np.ndarray
    # assert type(test_points) == np.ndarray
    # bol = np.zeros((test_points.shape[0], 1), dtype=np.bool)
    in_p_set = set()
    ori_set = points8
    ori_edge_index = conv_hull(ori_set)
    ori_edge_index = np.sort(np.unique(ori_edge_index))

    for i in range(test_points.shape[0]):
        # print(test_points[i])
        p = test_points[i]
        if (p[0]< x_range[0] or p[0]>x_range[1]) \
               or  (p[1]< y_range[0] or p[1]>y_range[1])  \
               or  (p[2]< z_range[0] or p[2]>z_range[1]) :
            continue

        new_set = np.concatenate((points8, test_points[i, np.newaxis]), axis=0)
        new_edge_index = conv_hull(new_set)
        new_edge_index = np.sort(np.unique(new_edge_index))
        # print(new_edge_index,ori_edge_index)
        # bol[i] = (new_edge_index.tolist() == ori_edge_index.tolist())
        if new_edge_index.tolist() == ori_edge_index.tolist():
            in_p_set.add(i)
        #
        # bol.append(new_edge_index.tolist() == ori_edge_index.tolist())
    return in_p_set

if __name__ == '__main__':
    # test1
    # A = np.array([[0, 0, 0], [0, 0, 1], [0, 1, 0], [0, 1, 1],
    #               [1, 0, 0], [1, 0, 1], [1, 1, 0], [1, 1, 1]])

    # p = np.array([[.5, .5, .5], [.2, .3, .6], [1, 1, 1.1]])
    # print(in_convex_polyhedron(A, p))  # True True False

    from peutils import pcd_py3
    import numpy as np

    position = {
            "x": 18.71206541732196,
            "y": 7.67060693678588,
            "z": 0.8000000000000006
          }
    dimension = {
        "x": 4.2,
        "y": 1.8,
        "z": 1.6
    }
    quaternion = {
        "x": 0,
        "y": 0,
        "z": -0.8908214220397678,
        "w": 0.45435360022238835
    }


    dt = pcd_py3.PointCloud.from_path("/Users/hwang2/Downloads/release_bundle_center_128_lidar-8_camera_pcd_txt_2022_04_14_icu30_HP-30-V71-AC-021_center_128_lidar_scan_data_1649928997301941.pcd")
    points_iter = ((p["x"], p["y"], p["z"]) for p in dt.pc_data)
    point_list = np.array(list(points_iter), dtype="float32")

    out_idx = get_idx_in_convex_polyhedron(point_list,position=position,dimension=dimension,quaternion=quaternion)
    # print(len(out_idx))
    # print(out_idx)

    ## 中心点，分别加上，长宽高的最长的一边，
    ## 中心点x y z 分别+- 长宽高最长一边的一半， 先判断，如果 x,y ,z 都不在这个区间内，那么点不在框内
    ## 不满足上面判断的时候，再用剩余的点再用上面的方法进行一轮计算，得出再框内的点有哪些


