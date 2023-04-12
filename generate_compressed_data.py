"""This tool generates compressed pictures and compresses existing annotations of recordings"""
import argparse
import logging

from core import *

formatter = logging.Formatter('%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s')
log = logging.getLogger('spread')
log.setLevel(logging.INFO)


def gen_compressed_data(dataset, recordings, pictures_only, annotations_only, compr_avg, compr_proc):
    """Compress recording pictures"""

    # Initialize dataset
    ds = Dataset(dataset)

    # Print info about a list of recordings

    if recordings:
        recordings = [ds.recordings_dict.get(rec, None) for rec in recordings]
    else:
        recordings = [x for x in ds.recordings if not x.compressed_pic_list or len(x.compressed_pic_list) < 152]

    mode = "compressed"
    for rec in recordings:
        if not annotations_only:
            log.info("Compressing pictures for recording %s", rec.name)
            rec.generate_pictures(mode=mode, navg=compr_avg, nproc=compr_proc)
        if not pictures_only:
            log.info("Compressing annotations for recording %s", rec.name)
            rec.compress_annotations(compr_avg * compr_proc)


def main():
    """Parse args"""
    parser = argparse.ArgumentParser(description="Generate compressed pictures and annotations")
    parser.add_argument("--dataset", required=True,
                        help="Root directory of the dataset.")
    parser.add_argument("--recordings", nargs="*",
                        help="List of recordings to print info for.")
    parser.add_argument("--compr-avg", type=int, default=3,
                        help="Total compression factor is: `compr-avg * compr-proc`.")
    parser.add_argument("--compr-proc", type=int, default=4,
                        help="Total compression factor is: `compr-avg * compr-proc`.")
    parser.add_argument("--pictures-only", action='store_true',
                        help='Only generate compressed pictures.')
    parser.add_argument("--annotations-only", action='store_true',
                        help='Only generate compressed annotations.')
    args = parser.parse_args()

    gen_compressed_data(args.dataset, args.recordings, args.pictures_only, args.annotations_only, args.compr_avg,
                        args.compr_proc)


if __name__ == '__main__':
    main()
