#!/usr/bin/env python
# coding: utf-8
'''Subject-specific classification with KU Data,
using Deep ConvNet model from [1].

References
----------
.. [1] Schirrmeister, R. T., Springenberg, J. T., Fiederer, L. D. J.,
   Glasstetter, M., Eggensperger, K., Tangermann, M., Hutter, F. & Ball, T. (2017).
   Deep learning with convolutional neural networks for EEG decoding and
   visualization.
   Human Brain Mapping , Aug. 2017. Online: http://dx.doi.org/10.1002/hbm.23730
'''

import argparse
import json
#from lib2to3.pytree import _Results
import logging
import sys
from os.path import join as pjoin
from typing_extensions import runtime

import h5py
import torch
import torch.nn.functional as F

#from braindecode.models.deep4 import Deep4Net
from deep4 import Deep4Net

from braindecode.torch_ext.optimizers import AdamW
from braindecode.torch_ext.util import set_random_seeds

logging.basicConfig(format='%(asctime)s %(levelname)s : %(message)s',
                    level=logging.INFO, stream=sys.stdout)
parser = argparse.ArgumentParser(
    description='Subject-specific classification with KU Data')
parser.add_argument('datapath', type=str, help='Path to the h5 data file')

parser.add_argument('-gpu', type=int,
                    help='The gpu device index to use', default=0)
parser.add_argument('-start', type=int,
                    help='Start of the subject index', default=1)
parser.add_argument(
    '-end', type=int, help='End of the subject index (not inclusive)', default=55)
parser.add_argument('-subj', type=int, nargs='+',
                    help='Explicitly set the subject number. This will override the start and end argument')
args = parser.parse_args()

datapath = args.datapath


subjs = 6
dfile = h5py.File(datapath, 'r')
torch.cuda.set_device(args.gpu)
set_random_seeds(seed=20200205, cuda=True)

import pynvml
import numpy as np
import os
import time

# pynvml.nvmlInit()

# gpu = pynvml.nvmlDeviceGetHandleByIndex(args.gpu)

# name = pynvml.nvmlDeviceGetName(gpu)
# device = name.decode("utf-8")

def get_data(subj):
    dpath = '/s' + str(subj)
    X = dfile[pjoin(dpath, 'X')]
    Y = dfile[pjoin(dpath, 'Y')]
    #chan = [7,8,9,10,12,13,14,17,18,19,20,32,33,34,35,36,37,38,39,40]; X=X[:,chan]
    return X[:], Y[:]

# Get data for within-subject classification
X, Y = get_data(6)
X_train, Y_train = X[50:250], Y[50:250]
X_val, Y_val = X[250:300], Y[250:300]
X_test, Y_test = X[300:], Y[300:]

suffix = 's' + str(6)
n_classes = 2
in_chans = X.shape[1]
print("X Shape", X.shape)

# final_conv_length = auto ensures we only get a single output in the time dimension
model = Deep4Net(in_chans=in_chans, n_classes=n_classes,
                    input_time_length=X.shape[2],
                    final_conv_length=1, split_first_layer=False).cuda()

# these are good values for the deep model
optimizer = AdamW(model.parameters(), lr=1 * 0.01, weight_decay=0.5*0.001)
model.compile(loss=F.nll_loss, optimizer=optimizer, iterator_seed=1, )

model.fit(X, Y, epochs=1, batch_size=400, scheduler='cosine')
            #validation_data=(X_val, Y_val))#, remember_best_column='valid_loss')


test_loss = model.evaluate(X, Y)

# measurements = []

# for _ in range(100):
#     start = time.time()
#     test_loss = model.evaluate(X_test, Y_test)
#     end = time.time()
#     runtime = end - start
#     throughput = len(Y) / runtime
#     measurements.append(throughput)
    

# # pynvml.nvmlShutdown()
# results = np.array(measurements)
# res = {}
# #res['Throughput (images/second)'] = throughput
# res['Mean Throughput (images/sec)'] = results.mean()
# res['Std'] = results.std()
# res['N']   = len(results)

# try:
#     os.remove("throughput_metrics.txt")
# except FileNotFoundError:
#     pass

# # file = open("throughput_metrics.txt", "w")
# # file.write(str(res))
# # file.close()
# print("Results written to power_metrics.txt")
