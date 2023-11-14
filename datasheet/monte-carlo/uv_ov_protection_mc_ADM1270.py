#!/usr/bin/env python
# pylint: disable=duplicate-code,invalid-name
# pylint: enable=invalid-name
"""
This Python scrip calculates the overvoltage, undervoltage and overcurrent parameters for the DIN 41612 backplane
datasheet. These numbers are derived using monto-carlo simulation and take into account the component parameters to
calculate the typical and minimum and maximum values used in the datasheet. This script is used for the positive rail
employing the Analog Devices ADM1270: https://www.analog.com/media/en/technical-documentation/data-sheets/ADM1270.pdf.
"""
import argparse
import os
from math import erf

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from numpy import ndarray

colors = sns.color_palette("colorblind")
__version__ = "0.9.0"

# Use these settings for the PhD thesis
tex_fonts = {
    "text.usetex": True,  # Use LaTeX to write all text
    "font.family": "serif",
    # Use 10pt font in plots, to match 10pt font in document
    "axes.labelsize": 10,
    "font.size": 10,
    # Make the legend/label fonts a little smaller
    "legend.fontsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "pgf.rcfonts": False,  # don't setup fonts from rc parameters
    "text.latex.preamble": "\n".join(
        [  # plots will use this preamble
            r"\usepackage{siunitx}",
        ]
    ),
    # "pgf.texsystem": "lualatex",
    "pgf.preamble": "\n".join(
        [  # plots will use this preamble
            r"\usepackage{siunitx}",
        ]
    ),
    "savefig.directory": os.path.dirname(os.path.realpath(__file__)),
}
plt.rcParams.update(tex_fonts)
plt.style.use("tableau-colorblind10")
# end of settings


def init_argparse() -> argparse.ArgumentParser:
    """
    Create a basic argument parser to disable showing plots via a user supplied switch.

    Returns
    -------
    argparse.ArgumentParser
        The configured argument parser
    """

    parser = argparse.ArgumentParser(
        description="Datasheet parameter calculator for the ADM1270 input protection ic using Monte Carlo methods."
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{parser.prog} version {__version__}",
    )
    parser.add_argument("--silent", action="store_true", help="Do not show the plot when set.")

    return parser


def res_divider(vout: ndarray[float], res1: ndarray[float], res2: ndarray[float]) -> ndarray[float]:
    """Note: this is an inverted resistive divider that returns in the input voltage"""
    return vout * (res1 + res2) / res2


def plot_result(
    res: ndarray[float],
    is_silent: bool,
    confidence_interval: float,
    fname: str | None = None,
) -> None:
    """
    Plot a result array as a histogram both on screen and to a file.

    Parameters
    ----------
    res: ndarray of float
        The Numpy array to plot
    is_silent: bool
        Do not show the plot on screen when true
    confidence_interval:
        The confidence interval in multiples of sigma. See
        https://en.wikipedia.org/wiki/Standard_deviation#Rules_for_normally_distributed_data for details.
    fname: str, optional
        If not None, write the plot to the given filename
    """
    ax1 = plt.subplot(111)
    # First, bin the results. Make sure to use an odd number of bins is used to have a central bin to cover the maximum
    # of the gaussian.
    n, bins, _ = ax1.hist(res, bins=11, color=colors[0])
    # Find the bin with the highest count, aka the maximum.
    max_res = bins[np.argmax(n)]
    # Find all values that are greater (or equal) than the maximum, and sort them
    results_high_side = np.sort(res[res >= max_res])
    # Find all values that are less than the maximum, and sort them. The bias introduced will be addressed below
    results_low_side = np.sort(res[res < max_res])
    sigma_probability = erf(confidence_interval / np.sqrt(2))  # Convert sigma into a probability
    # Pick the value at the sigma_probability * len(results_high_side) index
    upper_bound = results_high_side[int(sigma_probability * np.size(results_high_side))]
    # Pick the (1-sigma_probability) * len(results_low_side) value. Taking (1-sigma_probability) fixes the bias
    # introduced earlier.
    lower_bound = results_low_side[int((1.0 - sigma_probability) * np.size(results_low_side))]
    print(
        f"Most likely result (± {confidence_interval}-sigma):"
        f" {max_res:.3f} −{max_res - lower_bound:.2f} +{upper_bound - max_res:.3f}"
    )
    print(f"Min:{lower_bound:.3f}, Typical: {max_res:.3f} Max: {upper_bound:.3f}")

    ax1.grid(True, which="minor", ls="-", color="0.85")
    ax1.grid(True, which="major", ls="-", color="0.45")
    ax1.set_ylabel(r"Counts")
    ax1.set_xlabel(r"Voltage \unit{\V}")

    fig = plt.gcf()
    #  fig.set_size_inches(11.69,8.27)   # A4 in inch
    #  fig.set_size_inches(128/25.4 * 2.7 * 0.8, 96/25.4 * 1.5 * 0.8)  # Latex Beamer size 128 mm by 96 mm
    phi = (5**0.5 - 1) / 2  # golden ratio
    fig.set_size_inches(441.01773 / 72.27 * 0.89, 441.01773 / 72.27 * 0.89 * phi)  # TU thesis
    plt.tight_layout()

    if fname is not None:
        print(f"Saving image to '{fname}'")
        plt.savefig(fname)

    if not is_silent:
        plt.show()


arg_parser = init_argparse()
args = arg_parser.parse_args()

RESISTOR_TOLERANCE = 0.01  # assume 3-sigma, but this may not be true if the manufacturer bins the resistors
N_SIGMA = 3
N_SAMPLES = int(1e8)
print(f"Rolling the dice {N_SAMPLES:.0e} times.")

tol_1 = np.random.normal(loc=1, scale=0.01 / 3, size=N_SAMPLES)  # 1% tolerance
tol_2 = np.random.normal(loc=1, scale=0.01 / 3, size=N_SAMPLES)
tol_3 = np.random.normal(loc=1, scale=0.01 / 3, size=N_SAMPLES)
v_sense = np.random.normal(loc=1, scale=0.015 / 3, size=N_SAMPLES)  # 1 V +- 0.015 V
# vout_hysteresis = np.random.normal(loc=60/1000, scale=5/1000/3, size=n_samples)  # 60 mV +- 5 mV, uv hysteresis
# vout_hysteresis = np.random.normal(loc=-30/1000, scale=5/1000/3, size=n_samples)  # -30 mV +- 5 mV, ov hysteresis
# vout_hysteresis = 0
# result = res_divider(vout=vout+vout_hysteresis, r1=221e3*tol_1, r2=30.1e3*tol_2 + 10e3*tol_3)  # Undervoltage
# result = res_divider(vout=vout+vout_hysteresis, r1=221e3*tol_1+30.1e3*tol_2, r2=10e3*tol_3)  # Overvoltage

print("Calculating undervoltage thresholds")
r1, r2 = 221e3 * tol_1, 30.1e3 * tol_2 + 10e3 * tol_3  # Undervoltage
result = res_divider(vout=v_sense + 0, res1=r1, res2=r2)
plot_result(result, confidence_interval=N_SIGMA, is_silent=args.silent)
plt.clf()

print("Calculating undervoltage hysteresis")
vout_hysteresis = np.random.normal(loc=60 / 1000, scale=5 / 1000 / 3, size=N_SAMPLES)  # 60 mV +- 5 mV, uv hysteresis
result = res_divider(vout=v_sense + vout_hysteresis, res1=r1, res2=r2)
plot_result(result, confidence_interval=N_SIGMA, is_silent=args.silent)
plt.clf()

print("Calculating overvoltage thresholds")
r1, r2 = 221e3 * tol_1 + 30.1e3 * tol_2, 10e3 * tol_3  # Overvoltage
result = res_divider(vout=v_sense + 0, res1=r1, res2=r2)
plot_result(result, confidence_interval=N_SIGMA, is_silent=args.silent)
plt.clf()

print("Calculating overcurrent thresholds")
vout_hysteresis = np.random.normal(loc=-30 / 1000, scale=5 / 1000 / 3, size=N_SAMPLES)  # -30 mV +- 5 mV, ov hysteresis
result = res_divider(vout=v_sense + vout_hysteresis, res1=r1, res2=r2)
plot_result(result, confidence_interval=N_SIGMA, is_silent=args.silent)
plt.clf()

print("Calculating overcurrent thresholds")
v_sense = np.random.normal(loc=50 / 1000, scale=3 / 1000 / 3, size=N_SAMPLES)  # 50 mV +- 3 mV
r1 = 3e-3 * tol_1
result = v_sense / (r1)
plot_result(result, confidence_interval=N_SIGMA, is_silent=args.silent)
