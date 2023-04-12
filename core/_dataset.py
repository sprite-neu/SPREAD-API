"""
Definition of the dataset top level structure: Dataset
"""
import os
import glob
import logging
from ._recording import Recording
from ._tables import DatasetTable
from ._metadata import DatasetMetadata
from ._utils import *

log = logging.getLogger('spread')


__all__ = ['Dataset']


class Dataset(object):
    """
    Represents an instance of SPREAD
    """

    @staticmethod
    def get_rec_name(recname):
        """
        Returns the name of a recording, omitting the 32fc/dat extension
        """
        if recname.endswith('.32fc'):
            return recname.split('.32fc')[0]
        elif recname.endswith('.dat'):
            return recname.split('.dat')[0]
        else:
            return recname

    def __init__(self, root_dir, recount_pictures=False):
        """
                Dataset structure

                    dataset_root
        recordings                      pictures                        metadata
rec_<id>.32fc  rec_<id>.json    rec<id>/rec_<id>_pic_<pic_id>       global_metadata_files
        """

        # Root directory of the dataset
        self.root_dir = os.path.abspath(root_dir)
        if not os.path.isdir(self.root_dir):
            log.error("Dataset root directory not found.")

        # Dataset directories
        self.recordings_dir = os.path.join(self.root_dir, "recordings")
        # Pictures
        self.pictures_dir = os.path.join(self.root_dir, "pictures")
        # Noise Calculation
        self.noise_calc_dir = os.path.join(self.root_dir, "noise_calculations")
        # Metadata dir, containing global metadata
        self.metadata_dir = os.path.join(self.root_dir, "metadata")

        # Dataset metadata instance
        self.metadata = DatasetMetadata(self)

        if not os.path.isdir(self.metadata_dir):
            os.mkdir(self.metadata_dir)

        # File naming
        self.default_rec_name_prefix = "rec_"
        self.default_syn_name_prefix = "syn_"

        # Image naming <rec_ID>_<pic_ID>.jpg

        # Dataset toolset
        self.tools = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.core_dir = os.path.join(self.tools, 'core')
        self.flowgraphs = os.path.join(self.core_dir, 'flowgraphs')
        self.gen_dat_snr = os.path.join(self.flowgraphs, 'samples_fft.py')
        self.gen_fft_samples = os.path.join(self.flowgraphs, 'samples_to_dat.py')

        self.gen_pics_script = os.path.join(self.core_dir, 'gen_pics.py')

        # Dictionary containing all the recording objects
        self._recordings_dict = {}

        # Table of contents
        self.cont_table = None

        self.load_recordings(recount_pictures=recount_pictures)

        try:
            self.load_content_table()
        except Exception as e:
            log.error("There was an error loading the table of contents: %s", e)

        self.print_info()

    def load_recordings(self, recount_pictures=False):
        """
        Loads and initializes the recordings of this dataset
        """
        files = glob.glob(os.path.join(self.recordings_dir, '*.32fc'))
        for rec in files:
            rec_obj = Recording(rec, self, recount_pictures=recount_pictures)
            self._recordings_dict[rec_obj.name] = rec_obj

    def add_recording(self, rec_object=None, recname=None):
        """
        Adds a recording to the dataset either by recording object or by recording name (ie: rec_145)
        """
        if recname:
            recfile = [os.path.join(self.recordings_dir, '%s.32fc' % recname)]
            rec_obj = Recording(recfile, self)
            self._recordings_dict[rec_obj.name] = rec_obj
        elif rec_object:
            self._recordings_dict[rec_object.name] = rec_object

    def get_last_synthetic_index(self):
        """
        Loads and initializes the recordings of this dataset
        """
        files = glob.glob(os.path.join(self.recordings_dir, 'syn_*.32fc'))
        if not files:
            return 0
        indexes = [x.split('syn_')[1].split('.')[0] for x in files]
        try:
            indexes = [int(x) for x in indexes]
            return max(indexes)
        except ValueError:
            return None

    @property
    def recordings(self):
        """
        Returns a list of all recording objects in the dataset
        """
        return sorted(self._recordings_dict.values(), key=lambda x: (x.name[0], x.id))

    @property
    def recordings_dict(self):
        """
        Returns the dictionary of recordings
        """
        return self._recordings_dict

    @property
    def sorted_recordings(self):
        """
        Returns a sorted list of recordings based on their name and ID
        """
        return sorted(self._recordings_dict.values(), key=lambda x: (x.name[0], x.id))

    @property
    def sorted_recording_names(self):
        """
        Returns a sorted list of recording names
        """
        return sorted(self._recordings_dict.keys())

    def get_synthetic_outfile(self):
        """
        Returns the next available name for synthetic recordings using the default prefix
        """
        last_index = self.get_last_synthetic_index()
        if last_index is None:
            return None
        else:
            return self.default_syn_name_prefix + str(last_index+1) + '.32fc'

    def filter_recordings(self, filters):
        """
        Return a list of recordings that satisfy the given filters.
        :param filters: list of filters in the form of [key1=value1, key2=value2, ...]
        :return: list of recordings objects that satisfy all the filters
        """
        filtered = []
        for rec in self.recordings:
            for fltr in filters:
                try:
                    fltr_k, fltr_v = fltr.split('=')
                except ValueError:
                    log.error("Please make sure you are properly providing the filters in the format of key=value")
                    continue
                # Additional properties search
                if fltr_k == 'classes':
                    try:
                        fltr_v = int(fltr_v)
                    except ValueError:
                        log.error("Please provide an integer to filter the number of classes.")
                        continue
                    if len(rec.metadata.sources) != fltr_v:
                        break
                elif fltr_k == 'sources':
                    if fltr_v not in rec.metadata.sources:
                        break
                # If a filter is not satisfied, discard it
                elif str(rec.metadata.metadata.get(fltr_k, '')) != fltr_v:
                    break
            else:
                filtered.append(rec)
                continue
            continue
        return sorted(filtered, key=lambda x: (x.name[0], x.id))

    def load_content_table(self):
        """
        Loads the table of contents
        """
        self.cont_table = DatasetTable(self)

    def get_total_size(self):
        """
        Returns the total size of the dataset
        """
        return total_size([x.file_size for x in self.recordings])

    def get_total_duration(self):
        """
        Returns total duration of recordings in seconds
        """
        try:
            return sum([int(x.metadata.duration) for x in self.recordings])
        except TypeError:
            return None

    def get_total_no_pictures(self):
        """
        Returns total amount of pictures in the dataset
        """
        try:
            return sum([x.metadata.no_of_pictures for x in self.recordings])
        except TypeError:
            return None

    def print_info(self):
        """
        Prints info about the dataset
        """
        log.info("Loading SPREAD from %s", self.root_dir)
        # log.info("Dataset root directory: %s", self.root_dir)
        log.info("Total number of recordings: %s", len(self.recordings))
        log.info("Total duration of recordings in seconds: %s", self.get_total_duration())
        log.info("Total number of pictures: %s", self.get_total_no_pictures())
        log.info("Total size: %s", self.get_total_size())
