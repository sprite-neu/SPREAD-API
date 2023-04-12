"""
Tool to generate pictures for recordings of SPREAD.
"""
import argparse

from core import *

import logging

formatter = logging.Formatter('%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s')
log = logging.getLogger('spread')
log.setLevel(logging.INFO)


def process_gen_pics(dataset_dir, recordings=None, mode='grayscale', overwrite=False, log_noise=None, fft_size=512,
                     img_limit=0, filters=None):
    """
    Generates pictures of a recording and saves them in the picture directory of the dataset
    """

    # Load the dataset
    ds = Dataset(dataset_dir)

    # Get the recording objects
    if recordings:
        to_pic = [ds.recordings_dict.get(Dataset.get_rec_name(x), None) for x in recordings]
    elif filters:
        to_pic = ds.filter_recordings(filters)
    else:
        to_pic = ds.recordings

    for rec in to_pic:
        if not rec:
            log.error("No recording found")
            continue
        else:
            if not rec.metadata.no_of_pictures or rec.metadata.no_of_pictures == 0 or overwrite:
                rec.generate_pictures(log_noise=log_noise, npics=img_limit, mode=mode,
                                      nfft=fft_size)
            else:
                log.info("Skipping recording %s because pictures already exist. Specify \"--overwrite\" if desired.",
                         rec.name)


def main():
    """
    Parse arguments
    """
    parser = argparse.ArgumentParser(description='Generate pictures for all or selected recordings',
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--dataset", required=True,
                        help="Root directory of the dataset.")
    parser.add_argument("--recordings", nargs="*",
                        help="List of recordings to generate pictures for. If no recordings are specified, all \
                             recordings with no pictures will be processed")
    parser.add_argument("--filter", nargs="*",
                        help="Pass recordings with filters (eg: classes=3)")
    parser.add_argument("--mode", type=str, default='grayscale', choices=['grayscale', 'compressed'],
                        help='Choose mode: grayscale or compressed')
    # parser.add_argument("--compr-factor", type=int, default=12,
    #                     help="Compression factor.")
    parser.add_argument("--overwrite", action='store_true',
                        help="Overwrites previously generated pictures")
    parser.add_argument("--log-noise",
                        help="Noise level in dB. If omitted, noise is read from the recording metadata.")
    parser.add_argument("--img-limit", type=int, default=0,
                        help='Number of pictures to generate (default: 0 (all pictures)')
    parser.add_argument("--fft-size", type=int, default=512,
                        help="FFT size")
    args = parser.parse_args()

    process_gen_pics(args.dataset, args.recordings, args.mode, args.overwrite, args.log_noise, args.fft_size,
                     args.img_limit, args.filter)


if __name__ == '__main__':
    main()
