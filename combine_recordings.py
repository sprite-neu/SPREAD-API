"""
Script to create synthetic recordings in the Dataset from current recordings.
"""
import argparse
import os
import logging
from random import choice as pick_one
from time import time
from multiprocessing import Process, Queue
from core import *

formatter = logging.Formatter('%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s')
log = logging.getLogger('spread')
log.setLevel(logging.DEBUG)


def get_obj_from_files(ds, from_files):
    """
    Returns a list of objects based on their filenames
    """
    from_files = [os.path.basename(x).split('.32fc')[0] for x in from_files]  # get rid of file path and extension
    rec_obj_list = sorted([ds.recordings_dict[x] for x in from_files], key=lambda rec: rec.id)
    return rec_obj_list


def get_obj_from_properties(ds, from_properties):
    """
    Returns a list of objects based on their properties
    """
    rec_obj_list = []
    for rec_prop in from_properties:
        # Split the filters in the required list format [key=value ...]
        rec_prop = rec_prop.split(',')
        # and pick a random one from the filtered recordings
        filtered = ds.filter_recordings(rec_prop)
        if not filtered:
            log.error("No recording found that satisfies the properties: %s", ','.join(rec_prop))
            skipped_combos = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skipped_combs.txt")
            with open(skipped_combos, 'a') as sc:
                sc.write("%s\n" % ' '.join(from_properties))
            return
        which_one = pick_one(filtered)
        rec_obj_list.append(which_one)
    rec_obj_list.sort(key=lambda rec: rec.id)
    return rec_obj_list


def combine_recordings(dataset, from_files, from_properties, to_files, ds=None,
                       q=None, md_only=False):
    """
    Creates synthetic data from the given recordings. This includes initializing
    the recording and the metadata, and storing them in the dataset, depending on
    the options given.
    """

    if q:
        ds = q.get()
    if not ds:
        ds = Dataset(dataset)

    # Either get recordings explicitly from filenames
    if from_files:
        rec_obj_list = get_obj_from_files(ds, from_files)
    # choose random recordings based on input filters
    elif from_properties:
        rec_obj_list = get_obj_from_properties(ds, from_properties)
    else:
        rec_obj_list = None
    if not rec_obj_list:
        log.info("No recordings to combine, skipping.")
        return

    t = time()
    to_file = to_files[0] if to_files else None
    # Create the synthetic recording object and optionally the complex samples file
    synthetic = Recording.merge_recordings(rec_obj_list, to_file, mockup=md_only)
    # Create the synthetic metadata
    if not synthetic:
        log.error("Synthetic %s could not be found.", to_file)
        return
    synthetic.metadata = RecordingMetadata.combine_metadata(synthetic, [x.metadata for x in rec_obj_list])
    # Create the metafile for the recording and store the metadata
    synthetic.metadata.store_metadata()
    synthetic.print_info()
    log.info("Time elapsed: %s minutes", (time() - t) / 60)


def combine_annotations(dataset, synthetics=None, ds=None):
    """Creates synthetic annotations for synthetic recordings, by combining the annotations of the source recordings."""

    if not ds:
        ds = Dataset(dataset)

    if synthetics:
        synthetics = [ds.recordings_dict.get(x, None) for x in synthetics]
    else:
        synthetics = [x for x in ds.recordings if x.metadata.synthetic]

    for syn in synthetics:
        if not syn:
            log.error("Synthetic not found.")
            continue
        log.info("Creating synthetic annotations for recording %s", syn.name)
        if not os.path.isdir(syn.rec_pics_dir):
            try:
                os.mkdir(syn.rec_pics_dir)
            except OSError:
                pass
        if not os.path.isdir(syn.synthetic_annotations_dir):
            os.mkdir(syn.synthetic_annotations_dir)
        if not os.path.isdir(syn.compressed_pics_dir):
            try:
                os.mkdir(syn.compressed_pics_dir)
            except OSError:
                pass

        sources = [ds.recordings_dict.get(x, None) for x in syn.metadata.sources]

        # If a source is missing (i.e. removed from dataset)
        if None in sources:
            log.info("Synthetic %s is depending on a missing source: %s. Skipping.", syn.name,
                     ' '.join([x for x in syn.metadata.sources if not ds.recordings_dict.get(x, None)]))
            continue

        # Check if all source recordings have compressed annotations and use these first
        if all([x.compressed_annotation_list for x in sources]):
            log.info("Using compressed annotations.")
            for compr_ann in sources[0].compressed_annotation_list:
                syn_pic_id = get_id_from_pic_name(os.path.basename(compr_ann))
                pic_annotations = []

                # Find the corresponding annotation of every source file
                for src_rec in sources:
                    src_ann_file = os.path.join(src_rec.compressed_pics_dir, src_rec.pic_prefix + "_" + str(syn_pic_id)
                                                + ".txt")
                    try:
                        with open(src_ann_file, 'r') as f:
                            src_annot = f.read().strip().split('\n')
                    except IOError:
                        log.error("File missing for source rec: %s", src_ann_file)
                        continue
                    pic_annotations.extend(src_annot)

                # Merge all the lines together
                pic_annotations = '\n'.join(pic_annotations)
                # and save them in the synthetic annotation
                outfile = os.path.join(syn.compressed_pics_dir,
                                       syn.pic_prefix + "_" + str(syn_pic_id) + ".txt")
                with open(outfile, 'w') as f:
                    f.write(pic_annotations)

        # Else if not, for every picture in the synthetic file
        else:
            for syn_pic in syn.pic_list:
                syn_pic_id = get_id_from_pic_name(os.path.basename(syn_pic))
                pic_annotations = []
                # Find the corresponding annotation of every source file
                for src_rec in sources:
                    if src_rec.fixed_label_list:
                        src_dir = src_rec.fixed_labels_dir
                    else:
                        log.info("Fixed labels were not found for recording %s in %s. Skipping recording: %s.",
                                 src_rec.name,
                                 src_rec.fixed_labels_dir,
                                 syn.name)
                        break
                    src_ann_file = os.path.join(src_dir, src_rec.pic_prefix + "_" + str(syn_pic_id) + ".txt")
                    with open(src_ann_file, 'r') as f:
                        src_annot = f.read().strip().split('\n')
                    pic_annotations.extend(src_annot)
                else:
                    # Merge all the lines together
                    pic_annotations = '\n'.join(pic_annotations)
                    # and save them in the synthetic annotation
                    outfile = os.path.join(syn.synthetic_annotations_dir,
                                           syn.pic_prefix + "_" + str(syn_pic_id) + ".txt")
                    with open(outfile, 'w') as f:
                        f.write(pic_annotations)
                    continue
                break


def main():
    """
    Parse arguments
    """
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description="""This tool creates synthetic data based on other real or synthetic \
        data of SPREAD.
        The data can be produced by merging other sample files.

        Example usage:
        python combine_recordings.py --from source1.32fc source2.32fc --to combined.32fc

        In order to provide property filters as input instead of recording names one can use:

        --from-properties class=wifi,channel=3,duration=10 class=wmic class=bluetooth,transmission=continuous

        In that case there will be chosen and merged a random:
        
        wifi, channel 3, 10 second recording, with a
        wireless microphone recording, and a
        continuous bluetooth recording.

        Pay attention to the comma and space separations to avoid merging wrong files.
""")
    parser.add_argument("--dataset", required=True,
                        help="Dataset root directory")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--from-files", nargs="+",
                        help='File(s) to create synthetic data from.')
    source.add_argument("--from-properties", nargs="+",
                        help='Specify source recordings depending on their properties giving a \
        comma-separated list of property=value for each recording. \
        A random dataset recording satisfying the properties (if any) will be used.')
    parser.add_argument("--to-files", nargs='+',
                        help='File(s) to write synthetic data to.')
    source.add_argument("--combine-annotations", action='store_true',
                        help="Create annotations for the specified synthetic recordings by combining the annotations\
                             of the source recordings.")
    parser.add_argument("--synthetics", nargs="*",
                        help="Synthetic recordings to create annotations for. If not specified, all of them are\
                             generated.")
    parser.add_argument("--mock", action="store_true", help="Only print metadata of the resulting synthetic.")
    args = parser.parse_args()

    if args.combine_annotations:
        combine_annotations(args.dataset, args.synthetics)
        return

    combine_recordings(args.dataset, args.from_files, args.from_properties, args.to_files, md_only=args.mock)


if __name__ == '__main__':
    main()
