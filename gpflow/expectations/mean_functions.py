# noqa: F811

import tensorflow as tf

from .dispatch import expectation_dispatcher
from .. import mean_functions as mfn
from ..probability_distributions import Gaussian
from ..util import NoneType
from .expectations import expectation


@expectation_dispatcher.register(Gaussian, mfn.Linear, NoneType, NoneType, NoneType)
@expectation_dispatcher.register(Gaussian, mfn.Constant, NoneType, NoneType, NoneType)
def _E(p, mean, _, __, ___, nghp=None):
    """
    Compute the expectation:
    <m(X)>_p(X)
        - m(x) :: Linear, Identity or Constant mean function

    :return: NxQ
    """
    return mean(p.mu)


@expectation_dispatcher.register(Gaussian, mfn.Constant, NoneType, mfn.Constant, NoneType)
def _E(p, mean1, _, mean2, __, nghp=None):
    """
    Compute the expectation:
    expectation[n] = <m1(x_n)^T m2(x_n)>_p(x_n)
        - m1(.), m2(.) :: Constant mean functions

    :return: NxQ1xQ2
    """
    return mean1(p.mu)[:, :, None] * mean2(p.mu)[:, None, :]


@expectation_dispatcher.register(Gaussian, mfn.Constant, NoneType, mfn.MeanFunction, NoneType)
def _E(p, mean1, _, mean2, __, nghp=None):
    """
    Compute the expectation:
    expectation[n] = <m1(x_n)^T m2(x_n)>_p(x_n)
        - m1(.) :: Constant mean function
        - m2(.) :: General mean function

    :return: NxQ1xQ2
    """
    e_mean2 = expectation(p, mean2)
    return mean1(p.mu)[:, :, None] * e_mean2[:, None, :]


@expectation_dispatcher.register(Gaussian, mfn.MeanFunction, NoneType, mfn.Constant, NoneType)
def _E(p, mean1, _, mean2, __, nghp=None):
    """
    Compute the expectation:
    expectation[n] = <m1(x_n)^T m2(x_n)>_p(x_n)
        - m1(.) :: General mean function
        - m2(.) :: Constant mean function

    :return: NxQ1xQ2
    """
    e_mean1 = expectation(p, mean1)
    return e_mean1[:, :, None] * mean2(p.mu)[:, None, :]


@expectation_dispatcher.register(Gaussian, mfn.Identity, NoneType, mfn.Identity, NoneType)
def _E(p, mean1, _, mean2, __, nghp=None):
    """
    Compute the expectation:
    expectation[n] = <m1(x_n)^T m2(x_n)>_p(x_n)
        - m1(.), m2(.) :: Identity mean functions

    :return: NxDxD
    """
    return p.cov + (p.mu[:, :, None] * p.mu[:, None, :])


@expectation_dispatcher.register(Gaussian, mfn.Identity, NoneType, mfn.Linear, NoneType)
def _E(p, mean1, _, mean2, __, nghp=None):
    """
    Compute the expectation:
    expectation[n] = <m1(x_n)^T m2(x_n)>_p(x_n)
        - m1(.) :: Identity mean function
        - m2(.) :: Linear mean function

    :return: NxDxQ
    """
    N = tf.shape(p.mu)[0]
    e_xxt = p.cov + (p.mu[:, :, None] * p.mu[:, None, :])  # NxDxD
    e_xxt_A = tf.linalg.matmul(e_xxt, tf.tile(mean2.A[None, ...], (N, 1, 1)))  # NxDxQ
    e_x_bt = p.mu[:, :, None] * mean2.b[None, None, :]  # NxDxQ

    return e_xxt_A + e_x_bt


@expectation_dispatcher.register(Gaussian, mfn.Linear, NoneType, mfn.Identity, NoneType)
def _E(p, mean1, _, mean2, __, nghp=None):
    """
    Compute the expectation:
    expectation[n] = <m1(x_n)^T m2(x_n)>_p(x_n)
        - m1(.) :: Linear mean function
        - m2(.) :: Identity mean function

    :return: NxQxD
    """
    N = tf.shape(p.mu)[0]
    e_xxt = p.cov + (p.mu[:, :, None] * p.mu[:, None, :])  # NxDxD
    e_A_xxt = tf.linalg.matmul(tf.tile(mean1.A[None, ...], (N, 1, 1)), e_xxt, transpose_a=True)  # NxQxD
    e_b_xt = mean1.b[None, :, None] * p.mu[:, None, :]  # NxQxD

    return e_A_xxt + e_b_xt


@expectation_dispatcher.register(Gaussian, mfn.Linear, NoneType, mfn.Linear, NoneType)
def _E(p, mean1, _, mean2, __, nghp=None):
    """
    Compute the expectation:
    expectation[n] = <m1(x_n)^T m2(x_n)>_p(x_n)
        - m1(.), m2(.) :: Linear mean functions

    :return: NxQ1xQ2
    """
    e_xxt = p.cov + (p.mu[:, :, None] * p.mu[:, None, :])  # NxDxD
    e_A1t_xxt_A2 = tf.einsum("iq,nij,jz->nqz", mean1.A, e_xxt, mean2.A)  # NxQ1xQ2
    e_A1t_x_b2t = tf.einsum("iq,ni,z->nqz", mean1.A, p.mu, mean2.b)  # NxQ1xQ2
    e_b1_xt_A2 = tf.einsum("q,ni,iz->nqz", mean1.b, p.mu, mean2.A)  # NxQ1xQ2
    e_b1_b2t = mean1.b[:, None] * mean2.b[None, :]  # Q1xQ2

    return e_A1t_xxt_A2 + e_A1t_x_b2t + e_b1_xt_A2 + e_b1_b2t
