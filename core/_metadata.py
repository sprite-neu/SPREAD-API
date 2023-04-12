"""
Definition of the metadata structures of the dataset

RecordingMetadata
DatasetMetadata
"""
import os
import json
import datetime
import logging

from ._utils import *
from . import constants

from textwrap import dedent

__all__ = ['RecordingMetadata', 'DatasetMetadata']

log = logging.getLogger('spread')


class RecordingMetadata(object):
    """
    Represents an instance of recording metadata.

    This includes information about the actual recording such as date created, duration, or transmission infromation.

    If the recording is synthetic, it also includes information about the way the recording was created, the source
    files, etc.
    """

    @staticmethod
    def get_rec_metafile(recfile):
        """
        Returns the metadata file of the recording.
        Looks for a JSON file in the same directory as the recording with the same prefix
        :param recfile: path to recording file
        :return: recording metadata file (.json)
        """
        recfile = os.path.abspath(recfile)
        return os.path.splitext(recfile)[0]+'.json'
        # if os.path.isfile(os.path.splitext(recfile)[0]+'.json'):
        #     return os.path.splitext(recfile)[0]+'.json'
        # else:
        #     return None

    @classmethod
    def combine_metadata(cls, recording, from_md):
        """
        Combines multiple metadata objects into a new metadata object. Used for the creation of synthetic data.
        @param recording: synthetic recording object to create metadata for
        @param from_md: Source metadata objects
        @return: Combined metadata object
        """
        # Initial values for the synthetic metadata
        combined = {
            'date_recorded': datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S'),
            'classes': ','.join([x for y in from_md for x in y.d_class]),
            'noise_db': add_noise_levels([x.noise_pwr_db for x in from_md]),
            'synthetic': True,
            'sources': ','.join([x.rec_name for x in from_md]),
            'rec_name': recording.name,
            'duration': min([x.duration for x in from_md]),
        }

        initial_combined_keys = list(combined.keys())

        for md in from_md:
            for key in md.metadata:
                if key in initial_combined_keys + ['freq_sweep', 'no_of_pictures', 'file_size']:
                    continue

                if key == "tx":
                    new_value = md.metadata[key]
                else:
                    new_value = md.metadata['classes']+'_'+str(md.metadata[key])
                # If the key already exists include the new metadata separated by commas
                if key in combined:
                    combined[key] += ',' + new_value
                # Else create it
                else:
                    combined[key] = new_value
        return cls(recording, md_from_dict=combined)

    def __init__(self, recording, md_from_dict=None):

        # Initial metadata
        if md_from_dict:
            self._metadata = md_from_dict              # Initialize metadata dict
        else:
            self._metadata = {}

        self.recording = recording

        # Metadata file
        self.metafile = RecordingMetadata.get_rec_metafile(recording.recfile)

        # Parse the recording metadata to retrieve properties
        if not self._metadata:
            if self.metafile:
                if os.path.isfile(self.metafile):
                    self.load_metadata()

        self.rec_name = self._gets('rec_name')
        self._synthetic = self._getb('synthetic')
        self.sources = self._gets('sources').split(',')
        self.date_recorded = self._gets('date_recorded')
        self.d_class = (self._gets('class') or self._gets('classes')).split(',')
        self.duration = self._geti('duration')

        self.channel = (self._gets('channel') or self._gets('channels')).split(',')
        self.cfreq = (self._gets('cfreq') or self._gets('fc')).split(',')
        self.samp_rate = self._gets('samp_rate').split(',')
        self.noise_pwr_db = self._getf('noise_pwr_db') or self._getf('noise_db')
        self.noise_variance = self._getf('noise_variance')
        self.snr = self._gets('snr').split(',')
        self._snr_range = self._gets('snr_range').split(',')

        if not self._snr_range or self._snr_range == [''] or self._snr_range == ['n/a'] or \
                ''.join(self._snr_range) == 'n/a':
            self._set_md_value('snr_range', ','.join(self._get_snr_range()))
            self._snr_range = self._gets('snr_range').split(',')

        # If the transmission was a frequency sweep, the information is stored in this dictionary in order to be parsed
        self.freq_sweep = self._get_md_value('freq_sweep')

        self.transmission = self._gets('transmission')      # Transmission (continuous or interval)
        self.type = self._gets('type')                      # Type of transmission(data, control, ping, n/a)

        self.no_of_pictures = self._geti('no_of_pictures')
        self.file_size = self._gets('file_size')

    def load_metadata(self):
        """
        Parses the metafile and stores metadata in a dictionary
        """
        try:
            with open(self.metafile, "r") as mf:
                self._metadata = json.load(mf)
        # Some metadata files have an extra closing bracket when multiprocessing is used
        except ValueError:
            # Try fixing a recognized pattern
            with open(self.metafile, "r") as mf:
                meta_contents = mf.read().strip()
            if meta_contents[-2:] == "}}":
                meta_contents = meta_contents[:-1]
            try:
                self._metadata = json.loads(meta_contents)
            except ValueError:
                recname = self.recording.name if self.recording else None
                log.error("Error loading metadata for recording: %s", recname)
                self._metadata = {}

        # Rename potentially old fields
        renamed_keys = {
            "class": "classes",
            "channel": "channels",
            "cfreq": "fc",
            "noise_pwr_db": "noise_db",
        }
        for renamed_key in renamed_keys.keys():
            if renamed_key in self._metadata.keys():
                self._metadata[renamed_keys.get(renamed_key)] = self._metadata.pop(renamed_key)

    def store_metadata(self):
        """
        Stores the current metadata dictionary in the metafile, overwriting the previous contents.
        """
        if self._metadata:
            with open(self.metafile, "w") as mf:
                json.dump(self._metadata, mf)

    @property
    def metadata(self):
        """
        Returns the dictionary containing the recording metadata
        """
        return self._metadata

    @property
    def synthetic(self):
        """
        Returns True if the recording is synthetic
        """
        return self._synthetic

    @property
    def snr_range(self):
        """
        Returns the snr range of the recording out of 'low', 'mid', 'high'.
        """
        return self._snr_range

    def _get_snr_range(self):
        """
        Categorizes the SNR of the recording in a range of LOW, MID, HIGH, depending on the class and SNR value
        Different transmissions have different depiction in the pictures based on their type and snr value. This
        classification as high, mid, or low is just meant to help with the analysis and prediction workflow.
        """

        # SNR ranges are defined in the constants.py
        snr_ranges = constants.SNR_RANGES
        ret = []
        for i in range(len(self.d_class)):
            rec_class = self.d_class[i]
            try:
                snr = self.snr[i].lstrip("%s_" % self.d_class[i])
                snr = round(float(snr), 2)
            except ValueError:
                return 'n/a'

            # For the class in question, identify the range the SNR falls into
            for thres in snr_ranges[rec_class]:
                if snr > thres:
                    ret.append(snr_ranges['label'][snr_ranges[rec_class].index(thres)])
                    break
                continue
        return ret

    def _geti(self, value, default=0):
        """
        Return the metadata value as an int
        """
        try:
            ret_value = int(self._get_md_value(value, default))
        except ValueError:
            ret_value = default
            log.error("Error trying to load the proper value for %s. Loading default value: %s.", value, default)
        return ret_value

    def _geti_list(self, value, default=None):
        """
        Return the metadata value as a list of ints parsed from a comma separated string
        """
        if default is None:
            default = [0]
        ret_value = self._get_md_value(value, default)
        ret_value = ret_value.split(',')
        return [int(x) if x else 0 for x in ret_value]

    def _getf(self, value, default=0.0):
        """
        Return the metadata value as a float
        """
        try:
            ret_value = float(self._get_md_value(value, default))
        except ValueError:
            ret_value = default
            log.error("Error trying to load the proper value for %s. Loading default value: %s.", value, default)
        return ret_value

    def _getf_list(self, value, default=None):
        """
        Return the metadata value as a list of floats parsed from a comma separated string
        """
        if default is None:
            default = [0.0]
        ret_value = self._get_md_value(value, default)
        ret_value = ret_value.split(',')
        return [float(x) if x else 0.0 for x in ret_value]

    def _gets(self, value, default=''):
        """
        Return the metadata value as a string
        """
        try:
            ret_value = str(self._get_md_value(value, default))
        except ValueError:
            ret_value = default
            log.error("Error trying to load the proper value for %s. Loading default value: %s.", value, default)
        return ret_value

    def _getb(self, value, default=None):
        """
        Return the metadata value as boolean
        """
        return True if self._get_md_value(value, default).lower() == 'true' else False

    def _get_md_value(self, value, default=None):
        return str(self._metadata.get(value, default))

    def _set_md_value(self, key, value):
        """
        Modifies or adds a metadata key value. Used only for development purposes
        """
        self._metadata.update({key: value})

    def get_md_string(self):
        """
        Returns a string containing the metadata info for screen printing purposes
        """
        md_str = """\
                Name of recording: %s
                Synthetic: %s
                Sources: %s
                Center frequency: %s
                Sample rate: %s
                Duration: %s
                Class(es): %s
                Type: %s
                Channel(s): %s
                Transmission(s): %s
                Noise level in dB: %s
                SNR: %s
                SNR Range(s): %s
                Number of pictures: %s
                """ % (
                        self.rec_name,
                        self.synthetic,
                        ','.join(self.sources),
                        ','.join(self.cfreq),
                        ','.join(self.samp_rate),
                        self.duration,
                        ','.join(self.d_class),
                        self.type,
                        ','.join(self.channel),
                        self.transmission,
                        self.noise_pwr_db,
                        ','.join(self.snr),
                        ','.join(self.snr_range),
                        self.no_of_pictures
                        )
        return dedent(md_str)


class DatasetMetadata(object):
    """
    Represents an instance of dataset metadata.

    This can be information like size, number of recordings or pictures, types of classes, and so on.
    """
    def __init__(self, ds):
        self.dataset = ds
        self.ds_md_folder = os.path.join(self.dataset.root_dir, 'metadata')

        if not os.path.isdir(self.ds_md_folder):
            os.mkdir(self.ds_md_folder)

        self.class_names_file = os.path.join(self.ds_md_folder, "classes.json")

        self.classes = self.load_class_names()

    def load_class_names(self):
        """Load the dictionary containing class names and indices from the dataset metadata."""
        if os.path.isfile(self.class_names_file):
            with open(self.class_names_file, 'r') as cf:
                class_dict = json.load(cf)
        else:
            class_dict = dict()
        return class_dict
