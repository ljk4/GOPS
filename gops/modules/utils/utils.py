"""


"""
import time

import torch
import torch.nn as nn
import numpy as np

from modules.utils.tensorboard_tools import tb_tags
import random


def get_activation_func(key: str):
    assert isinstance(key, str)

    activation_func = None
    if key == 'relu':
        activation_func = nn.ReLU

    elif key == 'tanh':
        activation_func = nn.Tanh

    elif key == 'linear':
        activation_func = nn.Identity

    if activation_func is None:
        print('input activation name:' + key)
        raise RuntimeError

    return activation_func


def get_apprfunc_dict(key: str,type:str, **kwargs):
    if type == 'MLP':
        var = {'apprfunc': kwargs[key + '_func_type'],
               'name': kwargs[key + '_func_name'],
               'hidden_sizes': kwargs[key + '_hidden_sizes'],
               'hidden_activation': kwargs[key + '_hidden_activation'],
               'output_activation': kwargs[key + '_output_activation'],
               'obs_dim': kwargs['obsv_dim'],
               'act_dim': kwargs['action_dim'],
               'action_high_limit': kwargs['action_high_limit'],
               'action_low_limit': kwargs['action_low_limit']
               }
    elif type == 'GAUSS':
        var = {'apprfunc': kwargs[key + '_func_type'],
               'name': kwargs[key + '_func_name'],
               'num_kernel':kwargs[key + '_num_kernel'],
               'obs_dim': kwargs['obsv_dim'],
               'act_dim': kwargs['action_dim'],
               'action_high_limit': kwargs['action_high_limit'],
               'action_low_limit': kwargs['action_low_limit']
               }
    else:
        raise NotImplementedError

    return var


def change_type(obj):
    if isinstance(obj, (np.int_, np.intc, np.intp, np.int8,
                        np.int16, np.int32, np.int64, np.uint8,
                        np.uint16, np.uint32, np.uint64)):
        return int(obj)
    elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, (np.ndarray,)):  # add this line
        return obj.tolist()  # add this line
    elif isinstance(obj, dict):
        for k, v in obj.items():
            obj[k] = change_type(v)
        return obj
    elif isinstance(obj, list):
        for i, o in enumerate(obj):
            obj[i] = change_type(o)
        return obj
    else:
        return obj

def random_choice_with_index(obj_list):
    obj_len = len(obj_list)
    random_index = random.choice(list(range(obj_len)))
    random_value = obj_list[random_index]
    return random_value, random_index
class Timer(object):
    def __init__(self, writer, tag=tb_tags['time'], step=None):
        self.writer = writer
        self.tag = tag
        self.step = step

    def __enter__(self):
        self.start = time.time()

    def __exit__(self, exc_type, exc_val, exc_tb):
        # print(time.time() - self.start)
        self.writer.add_scalar(self.tag, time.time() - self.start, self.step)

