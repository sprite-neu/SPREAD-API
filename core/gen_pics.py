"""
Helper script to generate images for recordings. Used by class `Recording`.
"""
import argparse
import struct
import sys
from PIL import Image

import numpy as np
import os
from . import _utils as utils
# from core import img_scale, data_clip

SNR_MIN = -10
SNR_MAX = 50

np.set_printoptions(threshold=sys.maxsize)


def data_IO_snr(fopen, npoints, nfft, navg):
    """
    IO from a SNR file.
    """
    binary = fopen.read(npoints*4)
    syntax = str(npoints) + "f"

    data = struct.unpack(syntax, binary)
    data = np.reshape(data, (-1, nfft))

    if navg > 1 and type(navg) is int:
        avg_data = np.empty((data.shape[0]/navg, data.shape[1]))
        for i in range(0, data.shape[0], navg):
            avg_data[i/navg] = np.mean(data[i:i+navg], axis=0, keepdims=True)

        utils.data_clip(avg_data, SNR_MIN, SNR_MAX)
        avg_data = np.flip(utils.img_scale(avg_data, SNR_MIN, SNR_MAX),axis=0)
        return avg_data
    else:
        utils.data_clip(data, SNR_MIN, SNR_MAX)
        data = np.flip(utils.img_scale(data, SNR_MIN, SNR_MAX),axis=0)
        return data


def data_IO_raw_compressed(fopen, npoints, nfft, navg, nproc, log_noise):
    """
    IO from an FFT-ed complex recording file.
    """
    binary = fopen.read(npoints*4*2)
    syntax = str(npoints*2) + "f"

    data = struct.unpack(syntax, binary)
    data = np.reshape(data, (-1, nfft*2))

    real = np.take(data, np.arange(0, data.shape[1], 2), axis=1)
    imge = np.take(data, np.arange(1, data.shape[1], 2), axis=1)

    pwr = real**2+imge**2

    # Window Averaging
    avg_pwr = np.empty((pwr.shape[0]/navg, pwr.shape[1]))
    for i in range(0, pwr.shape[0], navg):
        avg_pwr[i/navg] = np.mean(pwr[i:i+navg,:], axis=0, keepdims=True)

    # Window Max-Min-
    max_pwr = np.empty((avg_pwr.shape[0]/nproc, avg_pwr.shape[1]))
    min_pwr = np.empty((avg_pwr.shape[0]/nproc, avg_pwr.shape[1]))
    avg_pwr_2 = np.empty((avg_pwr.shape[0]/nproc, avg_pwr.shape[1]))
    for i in range(0, avg_pwr.shape[0], nproc):
        max_pwr[i/nproc] = np.max(avg_pwr[i:i+nproc,:], axis=0, keepdims=True)
        min_pwr[i/nproc] = np.min(avg_pwr[i:i+nproc,:], axis=0, keepdims=True)
        avg_pwr_2[i/nproc] = np.mean(avg_pwr[i:i+nproc,:], axis=0, keepdims=True)

    max_pwr = (10*np.log10(max_pwr)-log_noise).astype(int)
    min_pwr = (10*np.log10(min_pwr)-log_noise).astype(int)
    avg_pwr_2 = (10*np.log10(avg_pwr_2)-log_noise).astype(int)

    # utils.data_clip, scaling
    utils.data_clip(max_pwr, SNR_MIN, SNR_MAX)
    utils.data_clip(min_pwr, SNR_MIN, SNR_MAX)
    utils.data_clip(avg_pwr_2, SNR_MIN, SNR_MAX)

    max_pwr = np.flip(utils.img_scale(max_pwr, SNR_MIN, SNR_MAX), axis=0)
    min_pwr = np.flip(utils.img_scale(min_pwr, SNR_MIN, SNR_MAX), axis=0)
    avg_pwr_2 = np.flip(utils.img_scale(avg_pwr_2, SNR_MIN, SNR_MAX), axis=0)

    return max_pwr, min_pwr, avg_pwr_2


def spectro_plot(data_img, disp, img_name):
    im = Image.fromarray(data_img)
    if disp == 'save':
        im.save(img_name)
    elif disp == 'show':
        im.show()
    return


def plot_recording(file, figdir, prefix, nfft, nline, navg, nproc, log_noise, img_mode='grayscale', disp='save', img_limit=None):
    """
        Plot the recorded data.
        img_mode: 'grayscale' - Replicate SNR data in 3 channels
                  'compressed' - Compress data for each channel
    """
    NPOINTS = nfft*nline*navg*nproc
    fopen = open(file, "rb")

    if not os.path.isdir(figdir):
        os.makedirs(figdir)

    img_index = 0
    while True:
        try:
            if img_mode == 'grayscale':
                data = data_IO_snr(fopen, NPOINTS, nfft, navg)
                data_img = np.stack((data, data, data), axis=-1)

            elif img_mode == 'compressed':
                data_ch1, data_ch2, data_ch3 = data_IO_raw_compressed(fopen, NPOINTS, nfft, navg, nproc, log_noise)
                data_img = np.stack((data_ch1, data_ch2, data_ch3), axis=-1)
            else:
                print("Unrecognized mode: ", img_mode)
                return

            fname = figdir + "/" + prefix + "_" + str(img_index) + ".jpg"
            spectro_plot(data_img, disp, fname)

            img_index += 1

            # Check if img limit is reached and exit
            if img_limit and img_limit>0:
                if img_index == img_limit:
                    print("Image limit reached: %s. Stopping...", img_limit)
                    break

        except struct.error:
            print("Done.")
            break

    # Always close the file after done
    fopen.close()
    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=str, required=True,
        help='Path to data: If mode is "grayscale" or "discretized" (experimental), the file should include SNR values (.dat file). If mode is "compressed", the file should include I&Q values after FFT.')
    parser.add_argument("--figdir", type=str, required=True,
        help='Path to figure storage')
    parser.add_argument("--prefix", type=str, default='rec',
        help='Prefix of the images')
    parser.add_argument("--nfft", type=int, default=512,
        help='Num. of FFT points')
    parser.add_argument("--nline", type=int, default=512,
        help='Num. of data lines to plot (after avg)')
    parser.add_argument("--navg", type=int, default=10,
        help='Average window size')
    parser.add_argument("--nproc", type=int, default=10,
        help='Max/min window size')
    parser.add_argument("--log-noise", type=int, default=-47,
        help='Measured log-noise level.')
    parser.add_argument("--img-mode", type=str, default='grayscale',
        help='Image mode: grayscale, compressed, discretized')
    parser.add_argument("--disp", type=str, default='save',
        help='Display mode')
    parser.add_argument("--img-limit", type=int,
        help='Limit the images to be generated.')
    args = parser.parse_args()

    plot_recording(args.file, args.figdir, args.prefix, args.nfft, args.nline, args.navg, args.nproc,
                   args.log_noise, img_mode=args.img_mode, disp=args.disp, img_limit=args.img_limit)
