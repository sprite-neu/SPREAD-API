from __future__ import division
import numpy as np
import matplotlib.pyplot as plt
import math
from copy import deepcopy

COMMON_NOISE = -45


class Frame(object):
    def __init__(self, pathname, background_data, width, height):
        self.width = width
        self.height = height
        self.background = background_data
        self.background_length = self.background.shape[0]

        self.frame_data = deepcopy(background_data)  # Background needs to be full-frame

        self.packets = []  # Packets in the frame

        self.pathname = pathname
        self.annotation_pathname = pathname[:-4] + ".txt"

    def add_packet(self, packet, left_offset=None, top_offset=None, noise=None):
        """
        Add packet to current frame. the background need to be of full-frame.
        """
        if not noise:
            noise = COMMON_NOISE
        packet_data = packet.data

        assert isinstance(left_offset, int) and isinstance(top_offset, int), \
            "The offsets are not properly set!"

        # Adding packet to the current frame
        for i in range(top_offset, top_offset + packet.length):
            for j in range(left_offset, left_offset + packet.width):
                log_to_pow_bg = pow(10.0, (self.frame_data[i][j] + noise) / 10.0)
                log_to_pow_trans = pow(10.0, (packet_data[i - top_offset][j - left_offset] + noise) / 10.0)
                self.frame_data[i][j] = 10 * math.log10(log_to_pow_bg + log_to_pow_trans) - noise

        bottom_offset = self.height - packet.length - top_offset

        # Extracting object frame info
        box_x_c = left_offset + packet.width / 2
        # Y-axis will be flipped to make the waterfall plot.
        box_y_c = self.height - (self.height - bottom_offset + top_offset) / 2
        box_w = packet.width
        box_h = packet.length
        category = packet.category

        # Append the bounding box to annotation file
        fopen = open(self.annotation_pathname, 'a+')
        fopen.write(str(category) + " " + str(round(box_x_c / self.width, 6)) + " " + str(
            round(box_y_c / self.height, 6)) + " " + str(round(box_w / self.width, 6)) + " " + str(
            round(box_h / self.height, 6)) + "\n")
        fopen.close()

        self.packets.append(packet)

        return

    def convert_image(self, cmap, vmin, vmax):
        """
        Directly convert 2D data into RGB image data of a spectrogram
        """
        norm = plt.Normalize(vmin, vmax)
        return np.flip(np.array(np.floor(cmap(norm(self.frame_data)) * 256)[:, :, :-1]).astype(np.uint8), axis=0)
