from peutils.pcd_py3 import PointCloud
import numpy as np


def get_pointlist_from_path(path,fltype=None,dtype=None):
    # path可以是当时标注的点云对应文件，也可以是客户标注的对应文件，如果是客户的文件，我们要注意是否有去过Nan点，这种需要补点.
    # path可以是url 也可以是路径

    if fltype not in ("pcd","bin"):
        raise Exception("fltype必须是pcd或者bin类型")
    if fltype =="bin":
        if dtype is None:
            raise Exception("bin文件必须指定数据类型")

    if fltype =="bin":
        bin_data = np.fromfile(path,dtype=dtype)
        return bin_data
    elif fltype =="pcd":
        dt = PointCloud.from_path(path)
        return dt.pc_data

def get_pointlist_from_url(session,url,fltype=None,dtype=None):

    if fltype not in ("pcd","bin"):
        raise Exception("fltype必须是pcd或者bin类型")
    if fltype =="bin":
        if dtype is None:
            raise Exception("bin文件必须指定数据类型")

    bin_r = session.get(url, stream=True)
    if fltype == "bin":
        bin_data = np.frombuffer(bin_r.content, dtype=dtype)
        bin_r.close()
        return bin_data  # np的一维数组
    elif fltype == "pcd":
        dt = PointCloud.from_buffer(bin_r.content)
        bin_r.close()
        return dt.pc_data  # 通过 x y z 等取数据

'''
ss = get_session()
p_list = get_pointlist_from_url(ss,"https://appen-storage.oss-cn-shanghai.aliyuncs.com/humor_3d/bucket-dataengine/release/preparation/card_data/icu30/data_label_preprocess/619c8ea93842dacdbf91b66e/center_128_lidar/1636006959490492.pcd",
                                    fltype="pcd")
for p in p_list:
    print(p["x"],p["y"],p["z"],p["intensity"])

p_list = get_pointlist_from_path("/Users/hwang2/Downloads/1636006959490492.pcd",fltype="pcd")
for p in p_list:
    print(p["x"],p["y"],p["z"],p["intensity"])

p_array = get_pointlist_from_url(ss,"https://projecteng.oss-cn-shanghai.aliyuncs.com/haomo_3d/segmentation/20210602/HDR006_60b0599b50eb3fa074e490d9_3034_QA/point_cloud/bin_v1/1620539160100000.bin",
            fltype="bin",dtype="float32")
p_array = get_pointlist_from_path("/Users/hwang2/Downloads/1620539160100000.bin", fltype="bin",dtype="float32")
print(p_array[:10])

'''