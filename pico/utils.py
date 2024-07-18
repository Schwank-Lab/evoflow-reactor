import os 
import time 
import sys

def timestamp_to_date(timestamp):
    localtime_tuple = time.localtime(timestamp)
    # Format the local time as a string
    return "{:04d}-{:02d}-{:02d}".format(*localtime_tuple[0:3])


def date_to_timestamp(date): 
    year, month, day = map(int, date.split('-'))
    return time.mktime((year, month, day, 0, 0, 0, 0, 0, 0))


def create_dir(path, exist_ok=True): 
    try:
        os.mkdir(path)
    except OSError as e:
        if not exist_ok:
            raise ValueError(f'Directory {path} already exists')
        

def file_exists(path):
    try:
        with open(path) as f:
            pass
        return True
    except OSError:
        return False
    
def is_dir(path): 
    try:
        os.listdir(path)
        return True
    except OSError:
        return False
    

def rm_tree(path):
    filenames = os.listdir(path)
    for filename in filenames:
        file_path = path + "/" + filename
        if is_dir(file_path):
            rm_tree(file_path)
        else: 
            os.remove(file_path)
    os.rmdir(path)
    
