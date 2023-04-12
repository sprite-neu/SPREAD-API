"""
Print various information about the dataset and its recordings
"""
import argparse
import os

from core import *

import logging

formatter = logging.Formatter('%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s')
log = logging.getLogger('spread')
log.setLevel(logging.INFO)


def process_info(dataset, recordings_list, filters, table_of_contents=False, no_show=False, recount_pictures=False):
    """
    Process the dataset and print information
    @param dataset: Root directory of the dataset
    @param recordings_list: List of recordings to print (eg: [rec_23 rec_52 syn_104 noi_2])
    @param filters: List of space separated filters for recordings (eg: [class=wifi channel=13])
    @param table_of_contents: Boolean, print out the table of contents and save it to files
    @param no_show: Boolean, only save the contents; don't print them
    @param recount_pictures: Recount pictures for all recordings
    @return: None
    """

    # Initialize dataset
    ds = Dataset(dataset, recount_pictures=recount_pictures)

    if table_of_contents:
        if not no_show:
            log.info("\n\nTable of Contents\n\n%s", ds.cont_table.get_table_str())
        ds.cont_table.save_to_csv()
        ds.cont_table.save_to_json()
        ds.cont_table.save_reclist_to_json()
        log.info("Dataset information are stored in global metadata: %s", ds.metadata_dir)

    # Print info about a list of recordings
    if recordings_list:
        for rec in recordings_list:
            rec = Dataset.get_rec_name(rec)

            try:
                ds.recordings_dict[rec].print_info()
            except KeyError:
                log.error("Recording %s not found", rec)

    # Print info about filtered recordings based on given properties
    if filters:
        filtered = ds.filter_recordings(filters)
        for rec in filtered:
            rec.print_info()
        log.info("List of filtered recordings: %s", ' '.join([x.name for x in filtered]))


def main():
    """
    Parse arguments
    """
    parser = argparse.ArgumentParser(description="Print information about the dataset or specific recordings")
    parser.add_argument("--dataset", required=True,
                        help="Root directory of the dataset.")
    parser.add_argument("--recordings", nargs="*",
                        help="List of recordings to print info for.")
    parser.add_argument("--show", nargs="*",
                        help="Print recordings that satisfy some criteria (eg --show classes=wifi channel=3)")
    parser.add_argument("--contents", action='store_true',
                        help="Print out a table of contents for the dataset")
    parser.add_argument("--no-show", action='store_true',
                        help="Don't print contents, only save in in the dataset_root_dir/metadata")
    parser.add_argument("--recount-pictures", action='store_true',
                        help="Count the pictures for every recording during loading to refresh the recording and "
                             "dataset metadata. Results in slower initialization of the dataset.")
    args = parser.parse_args()

    process_info(args.dataset, args.recordings, args.show, args.contents, args.no_show, args.recount_pictures)


if __name__ == '__main__':
    main()
