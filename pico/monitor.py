import gc 
import os 

def bytes_to_kb(n_bytes): 
    return n_bytes >> 10

def current_state():
    stats = os.statvfs('/')
    total_space = stats[0] * stats[2]
    free_space = stats[0] * stats[3]
    used_space = total_space - free_space
    return {
        'free_memory': bytes_to_kb(gc.mem_free()),
        'used_memory': bytes_to_kb(gc.mem_alloc()),
        'free_space': bytes_to_kb(free_space),
        'used_space': bytes_to_kb(used_space),
    }