# -*- coding: UTF-8 -*-

"""
Author: vincent yao
Date: 2023/5/23
Short Description:

Change History:

"""
from io import BytesIO
from typing import List
import numpy as np
import plyfile
from peutils.transform.v1.base import get_session
import open3d as o3d
from peutils.pcd_py3 import point_cloud_from_path
from pypcd import pypcd
import numpy.typing as npt


# common ply convert pcd tool
def ply2pcd(ply_file_path, compression="binary", mode="local"):
    if mode == "local":
        with open(ply_file_path, "rb") as ff:
            plydata = plyfile.PlyData.read(ff)
    elif mode == "http":
        session = get_session()
        r = session.get(ply_file_path)
        ply_data_bytes = BytesIO(r.content)
        plydata = plyfile.PlyData.read(ply_data_bytes)
    else:
        raise Exception("mode error")

    prop_names = [prop.name for prop in plydata["vertex"].properties]
    prop_val_dtypes = [prop.val_dtype for prop in plydata["vertex"].properties]

    metadata = dict()
    metadata["version"] = "0.7"
    metadata["fields"] = prop_names
    metadata["size"] = [int(val_dtype[1]) for val_dtype in prop_val_dtypes]
    metadata["type"] = [val_dtype[0].upper() for val_dtype in prop_val_dtypes]
    metadata["count"] = [1] * len(plydata["vertex"].properties)
    metadata["width"] = len(plydata["vertex"])
    metadata["height"] = 1
    metadata["points"] = metadata["width"] * metadata["height"]
    metadata["viewpoint"] = [0, 0, 0, 1, 0, 0, 0]
    metadata["data"] = compression

    points_data = np.array(
        [plydata["vertex"][prop.name] for prop in plydata["vertex"].properties]
    ).T
    result_pc = pypcd.PointCloud(metadata, points_data)
    return result_pc


# common merge pcds tool
def merge_pcds(pcd_paths):
    metadata = new_pc_data = None
    for pcd_path in pcd_paths:
        pc = pypcd.PointCloud.from_path(pcd_path)
        if not metadata:
            metadata = pc.get_metadata()
        else:
            metadata["points"] += pc.get_metadata()["points"]
            metadata["width"] += pc.get_metadata()["width"]

        if new_pc_data is None:
            new_pc_data = pc.pc_data
        else:
            new_pc_data = np.concatenate((new_pc_data, pc.pc_data), axis=0)

    result_pc = pypcd.PointCloud(metadata, new_pc_data)
    return result_pc


def convert_pcd(pcd_path: str, calibration: list):
    # calibration = [-0.031411579470372014, -0.9993558406098698, -0.017447904095204192, -0.0699976997537005,
    #                -0.004685153654105046, 0.017607980740519055, -0.9998338768362586, -0.33002570442139434,
    #                0.9994982387382582, -0.03131460776519021, -0.005233599397279213, -0.2500102660427299,
    #                0.0, 0.0, 0.0, 1.0]
    calibration_matrix = np.array(calibration).reshape(4, 4)
    pc = point_cloud_from_path(pcd_path)
    for p in pc.pc_data:
        multi = np.dot(calibration_matrix, np.array([p["x"], p["y"], p["z"], 1]))
        p["x"] = multi[0]
        p["y"] = multi[1]
        p["z"] = multi[2]
    return pc


def get_point_indices_within_box(
    center_position,
    dimension,
    rotation_matrix,
    point_cloud: o3d.geometry.PointCloud = None,
    points:npt.NDArray=None,
) -> List[int]:
    """
    计算3D框在点云中包含的点
    入参point_cloud，points二选一,point_cloud优先级大于points
    推荐使用point_cloud,减少计算量

    :param center_position: 中心点[x,y,z]
    :param dimension:  长宽高[l,w,h]
    :param rotation_matrix: rotation 3x3 matrix
    :param point_cloud: open3d PointCloud
    :param points:numpy.array,[[x,y,z],...]
    :return:
    """
    if not any([point_cloud, points.any()]):
        raise Exception("缺少点云数据")

    if point_cloud:
        if not isinstance(point_cloud, o3d.geometry.PointCloud):
            raise Exception("参数point_cloud类型需要为open3d.geometry.PointCloud")

    if not point_cloud and points.any():
        point_cloud = o3d.geometry.PointCloud()
        point_cloud.points = o3d.utility.Vector3dVector(points)

    obb = o3d.geometry.OrientedBoundingBox(
        center=center_position, R=rotation_matrix, extent=dimension
    )
    indices = obb.get_point_indices_within_bounding_box(point_cloud.points)
    return indices
