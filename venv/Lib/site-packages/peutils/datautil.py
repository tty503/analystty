# -*- coding: UTF-8 -*-

'''
Author: Henry Wang
Date: 2021-03-05 15:53
Short Description:

Change History:

'''

def unique(iterable, key=None):
    seen = set()
    for item in iterable:
        val = item if key is None else key(item) #要看后面key的函数传的什么，也是转成元组比较
        if val not in seen:
            yield item
            seen.add(val)

## list unique
'''
a = [1, 5, 2, 1, 9, 1, 5, 10]
print(list(unique(a)))
'''

'''
a = [{'x':1, 'y':2}, {'x':1, 'y':3}, {'x':1, 'y':2}, {'x':2, 'y':4}]
list(unique(a, key=lambda d: (d['x'],d['y'])))
'''

## file unique
'''
with open("/Users/hwang2/Documents/a.txt") as f:
    for i in unique(f):
        print(repr(i))
'''

## csv unique
'''
import csv
from operator import itemgetter
with open("/Users/hwang2/Documents/b.csv") as f:
    for row in unique(csv.reader(f),key=itemgetter(0,1)):
        print(row)
'''



def gen_uuid_seq(start=0):
    '''
    start 等于-1 第一个值出现值是0
    start 等于 0 第一个出现值是1
    '''
    # 0的话就代表 从1 开始
    count = start
    uuid_dict=dict()
    def new_uuid(uuid):
        nonlocal count
        nonlocal uuid_dict
        if uuid not in uuid_dict:
            count += 1
            uuid_dict[uuid]=count
        # print(uuid_dict,count)
        return uuid_dict[uuid]
    return new_uuid

'''
def my_uuid():
    from random import choice
    for i in range(10):
        rd = choice(['a','b','c','d'])
        print(rd,get_uuid_seq(str(rd)))

for i in range(3):
    print(f'round {i}')
    get_uuid_seq = gen_uuid_seq()
    my_uuid()

'''

class GenCategorySeq():
    def __init__(self,start=0,default_dict=None):
        self.start = start
        self.uuid_dict = dict() if default_dict is None else default_dict

    def up_seq(self,uuid):
        if uuid not in self.uuid_dict:
            self.uuid_dict[uuid] = self.start +1
        else:
            self.uuid_dict[uuid] = self.uuid_dict[uuid]+1

        return self.uuid_dict[uuid]

    def get_seq(self,uuid):
        return self.uuid_dict.get(uuid,self.start)
'''
不带初始数据
category_seq = GenCategorySeq(start=0)
print(category_seq.up_seq("a"))
print(category_seq.up_seq("b"))
print(category_seq.up_seq("a"))
1
1
2

'''

'''
带初始数据
category_seq = GenCategorySeq(default_dict={"a":10})
print(category_seq.up_seq("a"))
print(category_seq.up_seq("b"))
print(category_seq.up_seq("a"))

11
1
12
'''

