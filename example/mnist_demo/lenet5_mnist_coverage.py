# Copyright 2019 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sys
import numpy as np

from mindspore import Model
from mindspore import context
from mindspore.train.serialization import load_checkpoint, load_param_into_net
from mindspore.nn import SoftmaxCrossEntropyWithLogits

from mindarmour.attacks.gradient_method import FastGradientSignMethod
from mindarmour.utils.logger import LogUtil
from mindarmour.fuzzing.model_coverage_metrics import ModelCoverageMetrics

from lenet5_net import LeNet5

sys.path.append("..")
from data_processing import generate_mnist_dataset

LOGGER = LogUtil.get_instance()
TAG = 'Neuron coverage test'
LOGGER.set_level('INFO')


def test_lenet_mnist_coverage():
    context.set_context(mode=context.GRAPH_MODE, device_target="CPU")
    # upload trained network
    ckpt_name = './trained_ckpt_file/checkpoint_lenet-10_1875.ckpt'
    net = LeNet5()
    load_dict = load_checkpoint(ckpt_name)
    load_param_into_net(net, load_dict)
    model = Model(net)

    # get training data
    data_list = "./MNIST_unzip/train"
    batch_size = 32
    ds = generate_mnist_dataset(data_list, batch_size, sparse=True)
    train_images = []
    for data in ds.create_tuple_iterator():
        images = data[0].astype(np.float32)
        train_images.append(images)
    train_images = np.concatenate(train_images, axis=0)

    # initialize fuzz test with training dataset
    model_fuzz_test = ModelCoverageMetrics(model, 10000, 10, train_images)

    # fuzz test with original test data
    # get test data
    data_list = "./MNIST_unzip/test"
    batch_size = 32
    ds = generate_mnist_dataset(data_list, batch_size, sparse=True)
    test_images = []
    test_labels = []
    for data in ds.create_tuple_iterator():
        images = data[0].astype(np.float32)
        labels = data[1]
        test_images.append(images)
        test_labels.append(labels)
    test_images = np.concatenate(test_images, axis=0)
    test_labels = np.concatenate(test_labels, axis=0)
    model_fuzz_test.test_adequacy_coverage_calculate(test_images)
    LOGGER.info(TAG, 'KMNC of this test is : %s', model_fuzz_test.get_kmnc())
    LOGGER.info(TAG, 'NBC of this test is : %s', model_fuzz_test.get_nbc())
    LOGGER.info(TAG, 'SNAC of this test is : %s', model_fuzz_test.get_snac())

    # generate adv_data
    loss = SoftmaxCrossEntropyWithLogits(is_grad=False, sparse=True)
    attack = FastGradientSignMethod(net, eps=0.3, loss_fn=loss)
    adv_data = attack.batch_generate(test_images, test_labels, batch_size=32)
    model_fuzz_test.test_adequacy_coverage_calculate(adv_data,
                                                     bias_coefficient=0.5)
    LOGGER.info(TAG, 'KMNC of this test is : %s', model_fuzz_test.get_kmnc())
    LOGGER.info(TAG, 'NBC of this test is : %s', model_fuzz_test.get_nbc())
    LOGGER.info(TAG, 'SNAC of this test is : %s', model_fuzz_test.get_snac())


if __name__ == '__main__':
    test_lenet_mnist_coverage()
