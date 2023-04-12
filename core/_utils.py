"""
Utils file that defines miscellaneous functions
"""

import math
import struct
from . import constants
import numpy as np
from random import choice
from PIL import Image


def pwr_to_db(pwr):
    """
    Returns the power in dB
    """
    return 10*math.log10(pwr)


def db_to_pwr(db_lvl):
    """
    Returns the absolute power
    """
    return 10**(db_lvl/10.0)


def add_noise_levels(db_noise_levels):
    """
    Gets a list of noise levels and returns the additive noise in dB
    """
    absolute_noise_levels = [db_to_pwr(x) for x in db_noise_levels]
    sum_noise = sum(absolute_noise_levels)
    return pwr_to_db(sum_noise)


def load_bytes_from_fd(fd, start=None, end=None):
    """
    Reads `batch` number of samples from a file descriptor into a tuple and returns the tuple
    """
    if start:
        fd.seek(start)
    binary = fd.read(end-start)
    syntax = str(len(binary) / 4) + "f"
    try:
        data = struct.unpack(syntax, binary)
        return data
    except struct.error:        # not enough bytes to unpack, end of binary
        return None


def load_array_from_fd(fd):
    """Loads a numpy array from given file descriptor"""
    try:
        return np.load(fd)
    except (IOError, ValueError):
        return None


def data_reshape(data, step, nfft):
    """
    Reshape the array of data to form I,Q pairs
    """
    return np.reshape(data, (step, nfft))


def append_samples_to_file(filename, samples):
    """
    Appends the samples to file
    """
    syntax = str(len(samples))+'f'
    binary = struct.pack(syntax, *samples)
    with open(filename, 'ab') as of:
        of.write(binary)


def data_clip(data, min_snr, max_snr):
    """
    Clip the lower and upper values in a matrix
    """
    if min_snr is not None:
        data[data < min_snr] = min_snr
    if max_snr is not None:
        data[data > max_snr] = max_snr
    return data


def img_scale(data, min_snr, max_snr):
    """
    Assuming data is already clipped
    """
    return ((data-min_snr).astype(float)/(max_snr-min_snr)*255).astype(np.uint8)


def img_flip(data, ax=0):
    """
    Flip array along an axis
    """
    return np.flip(data, axis=ax)


def stack_image_channels(img_data):
    """
    Stack image channels assuming array is 2D
    """
    return np.stack((img_data, img_data, img_data), axis=-1)


def check_collision(left_offset1, width1, range2, width2, error=5):
    """
    Checking if collision between two packets is possible
    """
    lo2_choices = []
    for lo2 in range2:
        if left_offset1 > lo2 + width2 - error:
            continue

        if lo2 > left_offset1 + width1 - error:
            break

        lo2_choices.append(lo2)

    if len(lo2_choices) < 1:    # Collision is not possible
        return False, None
    else:
        return True, choice(lo2_choices)


def spectro_plot(data_img, img_name=None, display=True, save=False):
    """
    Show or save an image from a given array
    """
    im = Image.fromarray(data_img)
    if save:
        im.save(img_name)
    elif display:
        im.show()
    return


def convert_size(size_bytes, back=False):
    """
    Converts a size value to string and back using the hurry module. If hurry is not found, standard conversion is used.
    @param size_bytes:
    @param back:
    @return:
    """
    try:
        # Try to import hurry filesize for more readable output
        from hurry.filesize import size as h_size, si           # (system si assumes 1K == 1000 instead of 1024)
        # For back conversion, return absolute bytes size given a string as input
        if back:
            # If si is used the mapping is
            back_map = {x[1]: x[0] for x in si}
            # # Else
            # back_map = {'B': 1, 'G': 1073741824, 'K': 1024, 'M': 1048576, 'P': 1125899906842624, 'T': 1099511627776}
            try:
                return int(size_bytes[:-1])*back_map[size_bytes[-1]] if size_bytes != '0' else 0
            except ValueError as e:
                print (e)
                return None
        else:
            return h_size(size_bytes, system=si)
    # If package is not installed, print out in bytes
    except ImportError:
        if back:
            return int(size_bytes[:-1]) * constants.UNITS[size_bytes[-1]] if size_bytes != '0' else 0
        else:
            return "%sB" % size_bytes


def total_size(size_strs):
    """
    Given a list of strings [1G, 500M, 2.5T] it calculates and returns a string with the total size
    """
    size_sum = sum([convert_size(x, back=True) for x in size_strs if x])
    try:
        # Try to import hurry filesize for more readable output
        # noinspection PyUnresolvedReferences
        from hurry.filesize import size as h_size, si           # (system si assumes 1K == 1000 instead of 1024)
        total_size_str = h_size(size_sum, system=si)
    except ImportError:
        # Package not installed
        total_size_str = "%sB\t(Please install hurry.filesize package (pip install hurry.filesize)\
 for more readable output)" % size_sum
    return total_size_str


def convert_freq(freq, back=False):
    """Convert freq values from string to absolute value and back"""
    if back:
        return "%s Hz" % freq
    else:
        if not freq:
            return 0.0
        return float(freq[:-1]) * constants.UNITS[freq[-1]]  # if freq != '0.0' else 0.0


def get_pairs(item_list):
    """
    Given a list of items, returns all possible pair combinations.
    """
    pairs = []
    for i in item_list[:-1]:
        pairs.extend([(i, j) for j in item_list[item_list.index(i)+1:len(item_list)]])
    return pairs


def get_id_from_pic_name(picname):
    """
    Returns the ID of a (compressed) picture/annotation.

    Naming format is: <recording prefix>_<rec_ID>_pic_<pic_ID>.<jpg,txt>
    """
    pic_id = picname.split(".")[0].split("_")[-1]
    try:
        if isinstance(pic_id, str) and "grsc" in pic_id:
            pic_id = pic_id.replace("grsc", "")
        pic_id = int(pic_id)
    except ValueError:
        pic_id = -1
    return pic_id


def do_collide(transmissions):
    """
    Returns true if any pair of transmission settings (class and channel) in the given list causes a collision.
    """
    for i in transmissions[:-1]:
        if i[0] == 1 or i[0] == 4:
            continue
        for j in transmissions[transmissions.index(i)+1:]:
            if j[0] == 1 or j[0] == 4:
                continue
            i_cf = constants.CHANNELS[i[0]][0][i[1]]
            i_bw = constants.CHANNELS[i[0]][1]
            i_range = (i_cf - i_bw / 2.0, i_cf + i_bw / 2.0)
            j_cf = constants.CHANNELS[j[0]][0][j[1]]
            j_bw = constants.CHANNELS[j[0]][1]
            j_range = (j_cf - j_bw / 2.0, j_cf + j_bw / 2.0)
            # print("%s %s" % ((i_range[0]-j_range[0]), (i_range[1]-i_range[1])))
            if (i_range[0]-j_range[0]) * (i_range[1]-j_range[1]) < 0:
                return True
    return False
