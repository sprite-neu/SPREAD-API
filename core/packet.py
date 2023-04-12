from copy import deepcopy
import numpy as np

class Packet(object):
    def __init__(self, data, category, var_length=True):
        self.data = deepcopy(data)                  # should be numpy array
        self.length = data.shape[0]
        self.width = data.shape[1]
        self.category = category
        self.var_length = var_length    # Indicate if packet length is variable

    def adjust_snr(self, attennuation, limit_thres=0):
        self.data[self.data>limit_thres] -= attennuation        # Decrease the snr globally
        return


    def adjust_length(self, target_length, cushion=20):
        if target_length <= self.length:
            tail = target_length/2
            self.data = np.vstack((self.data[:tail,...], self.data[-(target_length-tail):, ...]))
            self.length = target_length
            assert self.length == self.data.shape[0]    # Check the length consistency
        else:           # If we wish to extend, stacking the last part of a packet to the existing data...
            if self.length < cushion:
                print("Packet is too short. No need to adjust.")
                return

            stacked_data = deepcopy(self.data[:-cushion,...])

            while stacked_data.shape[0] < target_length:    # Stacking until we fill up the gap between target_length and data length.
                gap = target_length-stacked_data.shape[0]
                if gap < self.length-cushion:               # Partial stacking
                    stacked_data = np.vstack((stacked_data, self.data[-gap:,...]))
                else:                                       # Full stacking
                    stacked_data = np.vstack((stacked_data, self.data[cushion:-cushion,...]))

            # Check the data and update the attributes
            assert stacked_data.shape[0] == target_length

            self.data = stacked_data
            self.length = target_length

        return