import gc 
import os 

def bytes_to_kb(n_bytes): 
    return n_bytes >> 10

def current_state():
    return {
        'free_memory': bytes_to_kb(gc.mem_free()),
        'used_memory': bytes_to_kb(gc.mem_alloc()),
    }