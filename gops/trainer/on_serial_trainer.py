#  Copyright (c). All Rights Reserved.
#  General Optimal control Problem Solver (GOPS)
#  Intelligent Driving Lab(iDLab), Tsinghua University
#
#  Creator: iDLab
#  Description: Serial trainer for RL algorithms
#  Update Date: 2021-03-10, Wenhan CAO: Revise Codes
#  Update Date: 2021-05-21, Shengbo LI: Format Revise


__all__ = ["OnSerialTrainer"]

import logging

import torch
from torch.utils.tensorboard import SummaryWriter

from gops.utils.tensorboard_tools import add_scalars

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
from gops.utils.tensorboard_tools import tb_tags
import time


class OnSerialTrainer:
    def __init__(self, alg, sampler, evaluator, **kwargs):
        self.alg = alg
        self.sampler = sampler
        self.evaluator = evaluator

        if kwargs["use_gpu"]:
            self.alg.networks.cuda()
        else:
            self.sampler.networks = self.alg.networks
            self.evaluator.networks = self.alg.networks

        # Import algorithm, appr func, sampler & buffer
        self.iteration = 0
        self.max_iteration = kwargs.get("max_iteration")
        self.ini_network_dir = kwargs["ini_network_dir"]

        # initialize the networks
        if self.ini_network_dir is not None:
            self.alg.networks.load_state_dict(torch.load(self.ini_network_dir))

        self.save_folder = kwargs["save_folder"]
        self.log_save_interval = kwargs["log_save_interval"]
        self.apprfunc_save_interval = kwargs["apprfunc_save_interval"]
        self.eval_interval = kwargs["eval_interval"]
        self.writer = SummaryWriter(log_dir=self.save_folder, flush_secs=20)
        self.writer.add_scalar(tb_tags["alg_time"], 0, 0)
        self.writer.add_scalar(tb_tags["sampler_time"], 0, 0)

        self.writer.flush()
        self.start_time = time.time()
        # setattr(self.alg, "writer", self.evaluator.writer)

    def step(self):
        # sampling
        (samples_with_replay_format, sampler_tb_dict,) = self.sampler.sample_with_replay_format()
        print('samples_with_replay_format = ', samples_with_replay_format)
        # learning
        loss, alg_tb_dict = self.alg.local_update(samples_with_replay_format, self.iteration)
        if self.iteration % 50 == 0:
            print('ite = ', self.iteration)
            print('loss = ', loss)
        # # log
        # if self.iteration % self.log_save_interval == 0:
        #     print("Iter = ", self.iteration)
        #     add_scalars(alg_tb_dict, self.writer, step=self.iteration)
        #     add_scalars(sampler_tb_dict, self.writer, step=self.iteration)
        # # evaluate
        # if self.iteration % self.eval_interval == 0:
        #     self.evaluator.networks.load_state_dict(self.alg.networks.state_dict())
        #     self.sampler.env.close()
        #     total_avg_return = self.evaluator.run_evaluation(self.iteration)
        #     self.evaluator.env.close()
        #     self.writer.add_scalar(
        #         tb_tags["TAR of RL iteration"], total_avg_return, self.iteration
        #     )
        #     self.writer.add_scalar(
        #         tb_tags["TAR of total time"],
        #         total_avg_return,
        #         int(time.time() - self.start_time),
        #     )
        #     self.writer.add_scalar(
        #         tb_tags["TAR of collected samples"],
        #         total_avg_return,
        #         self.sampler.get_total_sample_number(),
        #     )
        #
        # save
        if self.iteration % self.apprfunc_save_interval == 0:
            torch.save(
                self.alg.networks.state_dict(),
                self.save_folder + "/apprfunc/apprfunc_{}.pkl".format(self.iteration),
            )
        if self.iteration == self.max_iteration - 1:
            torch.save(
                self.alg.networks.state_dict(),
                self.save_folder + "/apprfunc/apprfunc_{}.pkl".format(self.iteration),
            )

    def train(self):
        while self.iteration < self.max_iteration:
            self.step()
            self.iteration += 1

        self.writer.flush()
