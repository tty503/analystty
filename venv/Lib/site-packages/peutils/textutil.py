# -*- coding: UTF-8 -*-

'''
Author: Henry Wang
Date: 2021-03-05 15:55
Short Description:

Change History:

'''
import base64
import json
import subprocess
import platform


def gen_uuid():
    import uuid
    uid = str(uuid.uuid4())
    suid = ''.join(uid.split('-'))
    return suid

def parse_info_from_token(token):
    byte_string = base64.b64decode(token)
    normal_string = byte_string.decode()
    data_dict = json.loads(normal_string)
    return data_dict


def md5_file(filename):
  '''
  GEN MD5
  WINDOWS CMD LINE :certutil -hashfile Filename MD5
  MAC/LINUX :md5sum Filename
  '''
  import hashlib
  md5_l = hashlib.md5()
  with open(filename,mode="rb") as f:
    data = f.read()
  md5_l.update(data)
  ret = md5_l.hexdigest()
  print(ret)


def gen_date_str(sep='std'):
    from datetime import datetime
    '''
    if sep is std return %Y-%m-%d %H:%M:%S  '2020-06-28 21:26:47'
    if sep is None return %Y%m%d%H%M%S '20200628212651'
    '''
    if sep == 'std':
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    elif sep == None:
        return datetime.now().strftime("%Y%m%d%H%M%S")
    else:
        raise Exception('sep not definded.')


# 去掉前后空格，多个空格变成一个空格
def strip_and_replace_blank(text):
    import re
    newtext = re.sub(' +',' ',text).strip()
    return newtext

def get_device_sn():
    sys_kind = platform.system()
    if sys_kind == "Darwin":
        cmd = 'ioreg -l | grep IOPlatformSerialNumber'
        result = subprocess.check_output(cmd, shell=True).decode('utf-8')
        serial_number = result.split(' ')[-1].strip('\n').strip('"')
    elif sys_kind == 'Windows':
        cmd = 'wmic bios get serialnumber'
        result = subprocess.check_output(cmd, shell=True).decode('utf-8')
        serial_number = result.split('\n')[1].strip()
    else:
        raise Exception(f"unknow system kind:{sys_kind}")
    return serial_number



