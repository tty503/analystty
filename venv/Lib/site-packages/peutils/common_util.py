# -*- coding: UTF-8 -*-

'''
Author:rxu 
Date: 2024-04-26
Short Description:

Change History:

'''
from typing import List,Tuple,Union,Any,Set

def average_sampling(datas: Union[List[Any], Tuple[Any]], target_quantity: int) -> List[Tuple[Any,int]]:
    """
    平均采样
    从样本集中平均抽出n个样本"

    返回[(data,offset),(data,offset).....]

    :param datas:原始数据
    :param target_quantity:目标数量
    :return:
    """
    length = len(datas)

    # 如果 target_quantity 大于等于 length，则返回整个列表
    if target_quantity >= length:
        return datas

    interval = length / target_quantity

    sampled_lst = []

    for i in range(1, target_quantity + 1):
        index = int(i * interval) - 1
        sampled_lst.append((datas[index], index))

    return sampled_lst

def merge_overlapping_datasets(datasets:List[Set[Any]]) -> List[Set[Any]]:
    """
    合并重叠数据集，输出最终的整合结果

    e.g:
        input_list = [{1, 2, 3}, {4, 5}, {1, 4},{10,13},{6, 7, 8}, {8, 9, 10}, {11, 12}]
        out_list=[{1, 2, 3, 4, 5}, {6, 7, 8, 9, 10, 13}, {11, 12}]

    目前用双循环暴力解，可以优化
    :param datasets:
    :return:
    """
    merged_list = []
    while datasets:
        current_set = datasets.pop(0)
        merged = True

        while merged:
            merged = False
            for other_set in datasets:
                if current_set & other_set:
                    current_set |= other_set
                    datasets.remove(other_set)
                    merged = True

        merged_list.append(list(current_set))
    return merged_list
