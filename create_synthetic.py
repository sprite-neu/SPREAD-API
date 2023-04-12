"""
Create synthetic transmissions to augment the dataset for initial training.

Based on pre-made molds for all classes, the user can create a small dataset of artificial data with the
classes of their choice.

Workflow:
==============================================================
             DATA AUGMENTATION ON PER-PACKET BASIS
   PROCESSING FLOW:

   MANUAL EXTRACT SAMPLES/MOLDS ==>  ADJUST SNR ==> ADJUST LENGTH
                                                          |
                                                          V
                      VERTICAL PADDING <== HORIZONTAL PADDING
==============================================================
"""

from __future__ import division
from PIL import Image
import numpy as np
from random import randint, choice

import argparse
import os
import datetime

from core import data_clip
from core import img_flip
from core import stack_image_channels
from core import check_collision
from core import img_scale
from core import constants
from core import Frame
from core import Packet


def gen_synthetic_single_emission(category, savepath, snr_range=None, nfft=512, nlines=512,
                                  length_range=(62, 512), length_step=15, full_length_ratio=10):
    """ Generate data for single class """
    if snr_range is None:
        snr_range = [-10, 0, 10]

    # Sanitizing save path
    if not os.path.isdir(savepath):
        os.makedirs(savepath)

    # Report file
    reportfile = os.path.dirname(savepath) + '/report_' + str(datetime.datetime.now().date()) + '.txt'
    f_report = open(reportfile, 'a+')
    f_report.write('Report for category ' + constants.CATEGORIES[category]["main"] + '\n\n')

    # Load background mold
    background_mold = dict()
    for background in constants.CATEGORIES[-1]['element']:
        background_mold[background] = np.load(constants.MOLD_PATHS[background])

    print("===> Generating data for " +str(constants.CATEGORIES[category]["main"]))
    count = 0

    for obj_key in constants.CATEGORIES[category]["element"]:
        print("==>[ Processing object "+str(obj_key)+" ]")

        # Load main object mold
        object_mold = np.load(constants.MOLD_PATHS[obj_key])

        # Change the background
        for background in background_mold:
            print(">! Change frame background to "+str(background)+" for "+str(obj_key))

            # Change the SNR variation
            for snr in snr_range:
                if obj_key == 'bt_1' and snr == snr_range[0]:
                    continue

                if obj_key == 'bt_2' and snr != snr_range[1]:
                    continue

                print(">! Apply SNR variation of "+str(snr))

                # Writing counts to the report...
                f_report.write('Start count for category ' + constants.CATEGORIES[category][
                    'main'] + ' object ' + obj_key + ' with snr change ' + str(snr) + ':' + str(count) + '\n')

                # Start adjusting
                if constants.VAR[obj_key]:  # Length can be adjusted
                    for length in range(length_range[0], length_range[1] + 1, length_step):
                        # Only do replication for full-length packets
                        replicate = full_length_ratio
                        if length != length_range[1]:
                            replicate = 1

                        while replicate > 0:
                            print("! Change object length to "+str(length))

                            # Get the lower and upper bounds of objects in the frame 
                            x_start_point = constants.AUGMENT_CHANNELS[category]['start']
                            y_start_point = 0

                            x_end_point = constants.LIMIT_INDEX
                            y_end_point = 512

                            for i in range(x_start_point, x_end_point - object_mold.shape[1],
                                           constants.AUGMENT_CHANNELS[category]['space'] *
                                           constants.AUGMENT_CHANNELS[category][
                                               'skip']):  # Avoid similar samples by frequency skipping

                                # Vertical padding
                                j = y_start_point
                                while j + length <= y_end_point:  # Avoid similar samples by random time skipping
                                    left_offset = i
                                    top_offset = j

                                    # Adjust main object
                                    c_object = Packet(object_mold, category, constants.VAR[obj_key])
                                    c_object.adjust_length(length)
                                    c_object.adjust_snr(snr)

                                    # Create and adjust frame
                                    pathname = savepath + "/" + constants.CATEGORIES[category]['main'] + "_" + str(
                                        count) + ".jpg"
                                    frame = Frame(pathname, background_mold[background], nfft, nlines)
                                    current_box = frame.add_packet(c_object, left_offset, top_offset)

                                    # Save image
                                    data_clip(frame.frame_data, constants.VMIN, constants.VMAX)
                                    image_data = img_scale(frame.frame_data, constants.VMIN, constants.VMAX)
                                    image_data = img_flip(stack_image_channels(image_data), ax=0)
                                    image = Image.fromarray(image_data)
                                    image.save(pathname)
                                    count += 1

                                    # Time skipping
                                    j += np.random.randint(10, 30, 1)[0]

                            # Make sure to decrement the replication
                            replicate -= 1

                else:  # Length is fixed
                    print("! Length is fixed...")

                    # Get the lower and upper bounds of objects in the frame 
                    x_start_point = constants.AUGMENT_CHANNELS[category]['start']
                    y_start_point = 0

                    x_end_point = constants.LIMIT_INDEX
                    y_end_point = 512

                    for i in range(x_start_point, x_end_point - object_mold.shape[1],
                                   constants.AUGMENT_CHANNELS[category]['space'] * constants.AUGMENT_CHANNELS[category][
                                       'skip']):  # Avoid similar samples by frequency skipping

                        # Vertical padding
                        j = y_start_point
                        while j + object_mold.shape[0] < y_end_point:  # Avoid similar samples by random time skipping
                            left_offset = i
                            top_offset = j

                            # Adjust main object
                            c_object = Packet(object_mold, category, constants.VAR[obj_key])
                            c_object.adjust_snr(snr)

                            # Create and adjust frame
                            pathname = savepath + "/" + constants.CATEGORIES[category]['main'] + "_" + str(
                                count) + ".jpg"
                            frame = Frame(pathname, background_mold[background], nfft, nlines)
                            current_box = frame.add_packet(c_object, left_offset, top_offset)

                            # Save image
                            data_clip(frame.frame_data, constants.VMIN, constants.VMAX)
                            image_data = img_scale(frame.frame_data, constants.VMIN, constants.VMAX)
                            image_data = img_flip(stack_image_channels(image_data), ax=0)
                            image = Image.fromarray(image_data, 'RGB')
                            image.save(pathname)
                            count += 1

                            # Time skipping
                            j += np.random.randint(10, 30, 1)[0]

                # Writing counts for the report...
                f_report.write('Finish count for category ' + constants.CATEGORIES[category][
                    'main'] + ' object ' + obj_key + ' with snr change ' + str(snr) + ':' + str(count) + '\n')
                f_report.write('==================================================\n')

    f_report.close()
    print("> Done processing "+str(constants.CATEGORIES[category]['main'])+". "+str(count)+" elements generated")
    print("Images saved in: "+savepath)
    print("Processing report: "+reportfile)
    return savepath


def gen_synthetic_colliding_emission(categories, savepath, snr_range=None, nfft=512, nlines=512, num_coll_iter=500,
                                     length_range=(62, 512), length_step=15, full_length_ratio=10):
    """ Generate collisions for 2 classes """

    if snr_range is None:
        snr_range = [-10, 0, 10]

    # Parsing the classes
    cat1, cat2 = categories

    # Sanitizing save path
    if not os.path.isdir(savepath):
        os.makedirs(savepath)

    # Report file
    reportfile = os.path.dirname(savepath) + '/report_' + str(datetime.datetime.now().date()) + '.txt'
    f_report = open(reportfile, 'a+')
    f_report.write('Report for collision of ' + constants.CATEGORIES[cat1]["main"] + ' ' + constants.CATEGORIES[cat2][
        "main"] + '\n\n')

    # Load background mold
    background_mold = dict()
    for background in constants.CATEGORIES[-1]['element']:
        background_mold[background] = np.load(constants.MOLD_PATHS[background])

    print("===> Generating data for collision "+str(constants.CATEGORIES[cat1]["main"])+" "+str(constants.CATEGORIES[cat2]["main"]))
    count = 0

    # Change the background
    for background in background_mold:
        print(">! Change frame background to "+str(background))

        # Change the object for each category
        for obj1 in constants.CATEGORIES[cat1]['element']:
            object_mold1 = np.load(constants.MOLD_PATHS[obj1])
            for snr_obj1 in snr_range:
                if obj1 == 'bt_1' and snr_obj1 == snr_range[0]:
                    continue

                if obj1 == 'bt_2' and snr_obj1 != snr_range[1]:
                    continue

                print(">! Apply SNR variation of "+str(snr_obj1)+" to "+str(obj1))
                for obj2 in constants.CATEGORIES[cat2]['element']:
                    object_mold2 = np.load(constants.MOLD_PATHS[obj2])
                    for snr_obj2 in snr_range:
                        if obj2 == 'bt_1' and snr_obj2 == snr_range[0]:
                            continue

                        if obj2 == 'bt_2' and snr_obj2 != snr_range[1]:
                            continue

                        # Collision is not visible
                        if (snr_obj1 == snr_range[0] and snr_obj2 == snr_range[2]) or (
                                snr_obj1 == snr_range[2] and snr_obj2 == snr_range[0]):
                            continue

                        print(">! Apply SNR variation of "+str(snr_obj2)+" to "+str(obj2))
                        f_report.write(
                            'Start count for collision of ' + obj1 + ' and ' + obj2 + ' with snr change ' + str(
                                snr_obj1) + ' and ' + str(snr_obj2) + ':' + str(count) + '\n')

                        """
                        One problem is that, it's not trivial to come up with all collision
                        patterns, considering all settings of length, and snrs. So, the most
                        efficient way would be generating a number of samples for each combination
                        of SNRs and objects.
                        """

                        iter_counts = 0
                        while iter_counts < num_coll_iter:

                            packet_obj1 = Packet(object_mold1, cat1, constants.VAR[obj1])
                            packet_obj1.adjust_snr(snr_obj1)

                            packet_obj2 = Packet(object_mold2, cat2, constants.VAR[obj2])
                            packet_obj2.adjust_snr(snr_obj2)

                            # Varying lengths if needed
                            if constants.VAR[obj1]:
                                packet_obj1.adjust_length(randint(100, 512))
                            if constants.VAR[obj2]:
                                packet_obj2.adjust_length(randint(100, 512))

                            # Generate collision: Need to check if collision is possible
                            collidable = False
                            left_offset1 = None
                            left_offset2 = None
                            top_offset1 = None
                            top_offset2 = None

                            while collidable == False:
                                # First, choose the location of the first packet
                                left_offset1 = choice(range(constants.AUGMENT_CHANNELS[cat1]['start'],
                                                            constants.LIMIT_INDEX - packet_obj1.width,
                                                            constants.AUGMENT_CHANNELS[cat1]['space']))
                                top_offset1 = choice(range(0, 512 - packet_obj1.length + 1, 1))

                                range2 = range(constants.AUGMENT_CHANNELS[cat2]['start'],
                                               constants.LIMIT_INDEX - packet_obj2.width,
                                               constants.AUGMENT_CHANNELS[cat2]['space'])
                                collidable, left_offset2 = check_collision(left_offset1, packet_obj1.width, range2,
                                                                           packet_obj2.width)

                            top_offset2 = choice(
                                range(min(max(0, top_offset1 - int(packet_obj2.length / 2)), 512 - packet_obj2.length),
                                      min(512 - packet_obj2.length, top_offset1 + int(packet_obj1.length / 2)) + 1, 1))
                            # Collision not visible
                            if (
                                    left_offset1 <= left_offset2 and left_offset1 + packet_obj1.width >= left_offset2 + packet_obj2.width and
                                    top_offset1 <= top_offset2 and top_offset1 + packet_obj1.length >= top_offset2 + packet_obj2.length and
                                    snr_obj1 < snr_obj2 and obj2 != 'bt_2') or \
                                    (
                                            left_offset2 <= left_offset1 and left_offset2 + packet_obj2.width >= left_offset1 + packet_obj1.width and
                                            top_offset2 <= top_offset1 and top_offset2 + packet_obj2.length >= top_offset1 + packet_obj1.length and
                                            snr_obj2 < snr_obj1 and obj1 != 'bt_2'):
                                continue

                            # Create and adjust frame
                            pathname = savepath + "/" + "collision_" + constants.CATEGORIES[cat1]["main"] + "_" + \
                                       constants.CATEGORIES[cat2]["main"] + "_" + str(count) + ".jpg"
                            frame = Frame(pathname, background_mold[background], nfft, nlines)
                            frame.add_packet(packet_obj1, left_offset1, top_offset1)
                            frame.add_packet(packet_obj2, left_offset2, top_offset2)

                            # Save image
                            data_clip(frame.frame_data, constants.VMIN, constants.VMAX)
                            image_data = img_scale(frame.frame_data, constants.VMIN, constants.VMAX)
                            image_data = img_flip(stack_image_channels(image_data), ax=0)
                            image = Image.fromarray(image_data)
                            image.save(pathname)
                            count += 1
                            iter_counts += 1

                        # Writing counts for the report...
                        f_report.write(
                            'Finish count for collision of ' + obj1 + ' and ' + obj2 + ' with snr change ' + str(
                                snr_obj1) + ' and ' + str(snr_obj2) + ':' + str(count) + '\n')
                        f_report.write('==================================================\n')

    f_report.close()
    print("> Done processing collisions of "+str(constants.CATEGORIES[cat1]['main'])+" "+str(constants.CATEGORIES[cat2]['main'])+". "+str(count)+" elements generated")
    print("Images saved in: "+savepath)
    print("Processing report: "+reportfile)
    return savepath


def gen_synthetic_data(category, save_path, snr_range=None, nfft=512, nlines=512, num_coll_iter=500, length_range=(62, 512),
                       length_step=15, full_length_ratio=10):
    """
    Generate synthetic dataset based on category and the corresponding mold. Return the directory of the dataset.
    """
    if isinstance(category, int):
        return gen_synthetic_single_emission(category, save_path, snr_range, nfft, nlines,
                                             length_range, length_step, full_length_ratio)
    elif isinstance(category, list) or isinstance(category, tuple) :
        if len(category) == 1:
            return gen_synthetic_single_emission(category[0], save_path, snr_range, nfft, nlines,
                                                 length_range, length_step, full_length_ratio)
        elif len(category) == 2:
            return gen_synthetic_colliding_emission(category, save_path, snr_range, nfft, nlines, num_coll_iter, length_range,
                                                    length_step, full_length_ratio)
        else:
            raise NotImplementedError("Collision with more than two emission categories is not supported.")
    else:
        raise TypeError("Wrong format for emission category.")


def main():
    """ Parse args """
    parser = argparse.ArgumentParser(description="Create synthetic emission data.",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--save-path", type=str, required=True,
                        help="Directory path to save data.")
    parser.add_argument("--categories", "-c", type=int,
                        choices=[x for x in constants.CATEGORIES.keys() if x > -1], required=True, nargs="*",
                        help="Category(-ies) of synthetic emissions. Specifying two categories generates a collision.")
    parser.add_argument("--snr-range", nargs="+", type=int, default=[-10, 0, 10],
                        help="SNR Values for the synthetic emissions.")
    parser.add_argument("--n-fft", type=int, default=512,
                        help="Nfft for image generation. SPREAD dataset uses 512.")
    parser.add_argument("--n-lines", type=int, default=512,
                        help="Nlines for image generation. SPREAD dataset uses 512.")
    parser.add_argument("--num-coll-iter", "-i", type=int, default=500,
                        help="Number of random iterations for each choice of collision setting regarding the location.")
    parser.add_argument("--length-range", "-l", type=int, nargs=2, default=(62, 512),
                        help="Range for adjustment of emissions length.")
    parser.add_argument("--length-step", "-s", type=int, default=15,
                        help="Length adjustment step. I.e.: For 100MHz recordings, a step of 10 corresponds to ~50us.")
    parser.add_argument("--full-length-ratio", "-r", type=int, default=10,
                        help="Ratio of full length packets to synthetic ones. Generating more full length packets "
                             "improves training performance.")
    args = parser.parse_args()

    assert len(args.categories) <= 2, "A number of one or two categories may be selected."

    gen_synthetic_data(args.categories, args.save_path, snr_range=args.snr_range, nfft=args.n_fft, nlines=args.n_lines,
                       num_coll_iter=args.num_coll_iter, length_range=args.length_range, length_step=args.length_step,
                       full_length_ratio=args.full_length_ratio)


if __name__ == "__main__":
    main()
