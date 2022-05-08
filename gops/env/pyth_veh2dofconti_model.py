#  Copyright (c). All Rights Reserved.
#  General Optimal control Problem Solver (GOPS)
#  Intelligent Driving Lab(iDLab), Tsinghua University
#
#  Creator: iDLab
#  Description: Vehicle 3DOF Model
#  Update Date: 2021-05-55, Congsheng Zhang: create environment
#  Update Date: 2022-04-20, Jiaxin Gao: modify veh3dof model


import math
import warnings
import numpy as np
import torch
import copy
from gym.wrappers.time_limit import TimeLimit
import gym
import matplotlib.pyplot as plt

class Veh2dofcontiModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        """
        you need to define parameters here
        """
        self.vehicle_dynamics = VehicleDynamics()
        self.obs_scale = [1., 2., 1., 2.4]
        self.base_frequency = 10.
        self.obses = None
        self.actions = None
        self.veh_states = None

    def reset(self, obses):
        self.obses = obses
        self.actions = None
        self.veh_states = self._get_state(self.obses)

    def _get_obs(self, veh_states):
        v_ys, rs, delta_ys, delta_phis = veh_states[:, 0], veh_states[:, 1], veh_states[:, 2], veh_states[:, 3]
        lists_to_stack = [v_ys, rs, delta_ys, delta_phis]
        return torch.stack(lists_to_stack, 1)

    def _get_state(self, obses):
        v_ys, rs, delta_ys, delta_phis = obses[:, 0], obses[:, 1], obses[:, 2], obses[:, 3]
        lists_to_stack = [v_ys, rs, delta_ys, delta_phis]
        return torch.stack(lists_to_stack, 1)

    def forward(self, actions: torch.Tensor):
        steer_norm = actions
        actions = steer_norm * 1.2 * np.pi / 9
        self.actions = actions
        rewards = self.vehicle_dynamics.compute_rewards(self.veh_states, actions)
        self.veh_states = self.vehicle_dynamics.prediction(self.veh_states, actions, self.base_frequency)
        v_ys, rs, delta_ys, delta_phis = self.veh_states[:, 0], self.veh_states[:, 1], self.veh_states[:, 2], self.veh_states[:, 3]
        delta_phis = torch.where(delta_phis > np.pi, delta_phis - 2 * np.pi, delta_phis)
        delta_phis = torch.where(delta_phis <= -np.pi, delta_phis + 2 * np.pi, delta_phis)
        self.veh_states = torch.stack([v_ys, rs, delta_ys, delta_phis], 1)
        self.obses = self._get_obs(self.veh_states)
        mask = True
        return self.obses, rewards, mask, {"constraint": None}

    def scale_obs(self, obs: torch.Tensor):
        v_ys, rs, delta_ys, delta_phis = obs[:, 0], obs[:, 1], obs[:, 2], \
                                                   obs[:, 3]
        lists_to_stack = [v_ys * self.obs_scale[0], rs * self.obs_scale[1],
                          delta_ys * self.obs_scale[2], delta_phis * self.obs_scale[3]]
        return torch.stack(lists_to_stack, 1)


    def forward_n_step(self, obs: torch.Tensor, func, n):
        done_list = []
        next_obs_list = []
        v_pi = torch.zeros((obs.shape[0],))
        self.reset(obs)

        for step in range(n):
            scale_obs = self.scale_obs(obs)
            action = func(scale_obs)
            obs, reward, done, constraint = self.forward(action)
            v_pi = v_pi + reward
            next_obs_list.append(obs)
            done_list.append(done)

        return next_obs_list, v_pi, done_list


class VehicleDynamics(object):
    def __init__(self):
        self.vehicle_params = dict(C_f=-128915.5,  # front wheel cornering stiffness [N/rad]
                                   C_r=-85943.6,  # rear wheel cornering stiffness [N/rad]
                                   a=1.06,  # distance from CG to front axle [m]
                                   b=1.85,  # distance from CG to rear axle [m]
                                   mass=1412.,  # mass [kg]
                                   I_z=1536.7,  # Polar moment of inertia at CG [kg*m^2]
                                   miu=1.0,  # tire-road friction coefficient
                                   g=9.81,  # acceleration of gravity [m/s^2]
                                   )
        a, b, mass, g = self.vehicle_params['a'], self.vehicle_params['b'], \
                        self.vehicle_params['mass'], self.vehicle_params['g']
        F_zf, F_zr = b * mass * g / (a + b), a * mass * g / (a + b)
        self.vehicle_params.update(dict(F_zf=F_zf,
                                        F_zr=F_zr))
        self.path = ReferencePath()

    def f_xu(self, states, actions, tau):
        A = np.array([[0.4411, -0.6398, 0, 0],
                      [0.0242, 0.2188, 0, 0],
                      [0.0703, 0.0171, 1, 2],
                      [0.0018, 0.0523, 0, 1]])
        B = np.array([[2.0350], [4.8124], [0.4046], [0.2952]])
        A = torch.from_numpy(A.astype("float32"))
        B = torch.from_numpy(B.astype("float32"))
        v_y, r, delta_y, delta_phi = states[:, 0], states[:, 1], states[:, 2], states[:, 3]
        next_state = [v_y * A[0, 0] + r * A[0, 1] + delta_y * A[0, 2] + delta_phi * A[0, 3] + B[0, 0] * actions[:, 0],
                      v_y * A[1, 0] + r * A[1, 1] + delta_y * A[1, 2] + delta_phi * A[1, 3] + B[1, 0] * actions[:, 0],
                      v_y * A[2, 0] + r * A[2, 1] + delta_y * A[2, 2] + delta_phi * A[2, 3] + B[2, 0] * actions[:, 0],
                      v_y * A[3, 0] + r * A[3, 1] + delta_y * A[3, 2] + delta_phi * A[3, 3] + B[3, 0] * actions[:, 0]]
        return torch.stack(next_state, 1)

    def _get_obs(self, veh_states):
        v_ys, rs, delta_ys, delta_phis = veh_states[:, 0], veh_states[:, 1], veh_states[:, 2], veh_states[:, 3]
        lists_to_stack = [v_ys, rs, delta_ys, delta_phis]
        return torch.stack(lists_to_stack, 1)

    def _get_state(self, obses):
        v_ys, rs, delta_ys, delta_phis = obses[:, 0], obses[:, 1], obses[:, 2], obses[:, 3]
        lists_to_stack = [v_ys, rs, delta_ys, delta_phis]
        return torch.stack(lists_to_stack, 1)

    def prediction(self, x_1, u_1, frequency):
        x_next = self.f_xu(x_1, u_1, 1 / frequency)
        return x_next

    def simulation(self, states, actions, base_freq):
        steer_norm = actions
        actions = steer_norm * 1.2 * np.pi / 9
        # self.actions = actions
        next_states = self.prediction(states, actions, base_freq)
        v_ys, rs, delta_ys, delta_phis = next_states[:, 0], next_states[:, 1], next_states[:, 2], next_states[:, 3]
        delta_phis = torch.where(delta_phis > np.pi, delta_phis - 2 * np.pi, delta_phis)
        delta_phis = torch.where(delta_phis <= -np.pi, delta_phis + 2 * np.pi, delta_phis)
        next_states = torch.stack([v_ys, rs, delta_ys, delta_phis], 1)
        # self.obses = self._get_obs(next_states)
        return next_states

    def compute_rewards(self, states, actions):  # obses and actions are tensors
        # veh_state = obs: v_xs, v_ys, rs, delta_ys, delta_phis, xs
        # veh_full_state: v_xs, v_ys, rs, ys, phis, xs
        v_ys, rs, delta_ys, delta_phis = states[:, 0], states[:, 1], states[:, 2], \
                                                   states[:, 3]
        steers = actions[:, 0]
        devi_y = -torch.square(delta_ys)
        devi_phi = -torch.square(delta_phis)
        punish_yaw_rate = -torch.square(rs)
        punish_steer = -torch.square(steers)
        rewards = 0.4 * devi_y + 0.1 * devi_phi + 0.2 * punish_yaw_rate + 0.5 * punish_steer
        return rewards


class ReferencePath(object):
    def __init__(self):
        self.curve_list = [(7.5, 200., 0.), (2.5, 300., 0.), (-5., 400., 0.)]
        self.period = 1200.

    def compute_path_y(self, x):
        y = np.zeros_like(x, dtype=np.float32)
        for curve in self.curve_list:
            # 正弦的振幅，周期，平移
            # 这里是对3种正弦曲线进行了叠加。
            magnitude, T, shift = curve
            y += magnitude * np.sin((x - shift) * 2 * np.pi / T)
        return y

    def compute_path_phi(self, x):
        deriv = np.zeros_like(x, dtype=np.float32)
        for curve in self.curve_list:
            magnitude, T, shift = curve
            deriv += magnitude * 2 * np.pi / T * np.cos(
                (x - shift) * 2 * np.pi / T)
        return np.arctan(deriv)

    def compute_y(self, x, delta_y):
        y_ref = self.compute_path_y(x)
        return delta_y + y_ref

    def compute_delta_y(self, x, y):
        y_ref = self.compute_path_y(x)
        return y - y_ref

    def compute_phi(self, x, delta_phi):
        phi_ref = self.compute_path_phi(x)
        phi = delta_phi + phi_ref
        phi[phi > np.pi] -= 2 * np.pi
        phi[phi <= -np.pi] += 2 * np.pi
        return phi

    def compute_delta_phi(self, x, phi):
        phi_ref = self.compute_path_phi(x)
        delta_phi = phi - phi_ref
        delta_phi[delta_phi > np.pi] -= 2 * np.pi
        delta_phi[delta_phi <= -np.pi] += 2 * np.pi
        return delta_phi


def env_model_creator(**kwargs):
    return Veh2dofcontiModel()


def clip_by_tensor(t, t_min, t_max):
    """
    clip_by_tensor
    :param t: tensor
    :param t_min: min
    :param t_max: max
    :return: cliped tensor
    """
    result = (t >= t_min) * t + (t < t_min) * t_min
    result = (result <= t_max) * result + (result > t_max) * t_max
    return result
