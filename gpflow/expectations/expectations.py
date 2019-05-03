# Copyright 2018 the GPflow authors.
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

from .dispatch import expectation_dispatcher, quadrature_expectation_dispatcher
from ..probability_distributions import (DiagonalGaussian, Gaussian,
                                         MarkovGaussian)
from ..util import create_logger

logger = create_logger()


def expectation(p, obj1, obj2=None, nghp=None):
    """
    Compute the expectation <obj1(x) obj2(x)>_p(x)
    Uses multiple-dispatch to select an analytical implementation,
    if one is available. If not, it falls back to quadrature.

    :type p: (mu, cov) tuple or a `ProbabilityDistribution` object
    :type obj1: kernel, mean function, (kernel, features), or None
    :type obj2: kernel, mean function, (kernel, features), or None
    :param int nghp: passed to `_quadrature_expectation` to set the number
                     of Gauss-Hermite points used: `num_gauss_hermite_points`
    :return: a 1-D, 2-D, or 3-D tensor containing the expectation

    Allowed combinations

    - Psi statistics:
        >>> eKdiag = expectation(p, kernel)  (N)  # Psi0
        >>> eKxz = expectation(p, (kernel, feature))  (NxM)  # Psi1
        >>> exKxz = expectation(p, identity_mean, (kernel, feature))  (NxDxM)
        >>> eKzxKxz = expectation(p, (kernel, feature), (kernel, feature))  (NxMxM)  # Psi2

    - kernels and mean functions:
        >>> eKzxMx = expectation(p, (kernel, feature), mean)  (NxMxQ)
        >>> eMxKxz = expectation(p, mean, (kernel, feature))  (NxQxM)

    - only mean functions:
        >>> eMx = expectation(p, mean)  (NxQ)
        >>> eM1x_M2x = expectation(p, mean1, mean2)  (NxQ1xQ2)
        .. note:: mean(x) is 1xQ (row vector)

    - different kernels. This occurs, for instance, when we are calculating Psi2 for Sum kernels:
        >>> eK1zxK2xz = expectation(p, (kern1, feature), (kern2, feature))  (NxMxM)
    """
    p, obj1, feat1, obj2, feat2 = _init_expectation(p, obj1, obj2)
    try:
        expectation_fn = expectation_dispatcher.registered_fn(type(p), type(obj1), type(feat1),
                                                              type(obj2), type(feat2))
        return expectation_fn(p, obj1, feat1, obj2, feat2, nghp=nghp)
    except NotImplementedError as error:
        logger.debug(error)
        quadrature_expectation_fn = quadrature_expectation_dispatcher.registered_fn(
            type(p), type(obj1), type(feat1),type(obj2), type(feat2))
        return quadrature_expectation_fn(p, obj1, feat1, obj2, feat2, nghp=nghp)


def quadrature_expectation(p, obj1, obj2=None, nghp=None):
    """
    Compute the expectation <obj1(x) obj2(x)>_p(x)
    Uses Gauss-Hermite quadrature for approximate integration.

    :type p: (mu, cov) tuple or a `ProbabilityDistribution` object
    :type obj1: kernel, mean function, (kernel, features), or None
    :type obj2: kernel, mean function, (kernel, features), or None
    :param int num_gauss_hermite_points: passed to `_quadrature_expectation` to set
                                         the number of Gauss-Hermite points used
    :return: a 1-D, 2-D, or 3-D tensor containing the expectation
    """
    print(f"2. p={p}, obj1={obj1}, obj2={obj2}")
    p, obj1, feat1, obj2, feat2 = _init_expectation(p, obj1, obj2)
    quadrature_expectation_fn = quadrature_expectation_dispatcher.registered_fn(
            type(p), type(obj1), type(feat1),type(obj2), type(feat2))
    return quadrature_expectation_fn(p, obj1, feat1, obj2, feat2, nghp=nghp)


def _init_expectation(p, obj1, obj2):
    if isinstance(p, tuple):
        mu, cov = p
        classes = [DiagonalGaussian, Gaussian, MarkovGaussian]
        p = classes[cov.ndim - 2](*p)

    obj1, feat1 = obj1 if isinstance(obj1, tuple) else (obj1, None)
    obj2, feat2 = obj2 if isinstance(obj2, tuple) else (obj2, None)
    return p, obj1, feat1, obj2, feat2
