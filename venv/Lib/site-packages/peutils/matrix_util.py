# -*- coding: UTF-8 -*-

'''
Author: vincent yao
Date: 2023/7/4
Short Description:
    matrix
Change History:

'''
import numpy as np


# 3*3 matrix + 1*3 t => 4*4 matrix
def pad_rot_matrix(mat, t):
    padded = np.eye(4)
    padded[:3, :3] = mat
    padded[0, 3] = t[0]
    padded[1, 3] = t[1]
    padded[2, 3] = t[2]
    return padded
