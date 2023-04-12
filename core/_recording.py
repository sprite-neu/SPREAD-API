"""
Recording class and related functionalities to support the recording object of the Dataset
"""
import os
import sys
import glob
import subprocess
import json
import time
import logging
import numpy as np

from argparse import Namespace
from matplotlib import pyplot as plt

try:
    from . import flowgraphs
except SyntaxError:
    raise Exception("Flowgraphs cannot be imported. Please try with Python2.7.")

from . import _metadata as metadata
from . import _utils as utils
from . import _annotation as annotation
from ._plotter import Plotter
from ._annotation import Annotation
from gen_pics import plot_recording

__all__ = ['Recording']

log = logging.getLogger('spread')


class Recording(object):
    """
    Represents a recording of the dataset with data parsed from the recording and its metadata
    """

    heuristic_noise_calculation = 5.568650501352949 ** 2

    @staticmethod
    def get_rec_id(name):
        """
        Returns the id of the recording when the name format is rec_*
        """
        try:
            return int(name.split('_')[-1])
        except ValueError:
            return -1

    @staticmethod
    def get_recname(recfile):
        """
        Returns recording name based on the given path. The recording name is the basename of
        the path without any extension.
        :param recfile: path to recording file
        :return: recording name
        """
        recfile = os.path.abspath(recfile)
        return os.path.splitext(os.path.basename(recfile))[0]

    @staticmethod
    def get_rectype(recfile):
        """
        Returns recording type based on the given path.
        :param recfile: path to recording file
        :return: recording type
        """
        recfile = os.path.abspath(recfile)
        return os.path.splitext(os.path.basename(recfile))[1]

    @classmethod
    def merge_recordings(cls, rec_objects, outfile=None, mockup=False):
        """
        Takes multiple recording objects as input and returns one recording object as output
        :param rec_objects: list of recording objects to merge
        :param outfile: filepath to save the result
        :param mockup: If true, don't create the recording, just display the resulting metadata
        :return Recording: Combined recording object
        """
        if len(rec_objects) < 2:
            log.info("At least 2 recordings are needed in order to merge...")
            return None
        elif len(rec_objects) > 5:
            log.info("Merging of more than 5 recordings is not implemented")
            return None
        else:
            ds = rec_objects[0].dataset
            if not outfile:
                outfile = ds.get_synthetic_outfile()
                if not outfile:
                    log.error("Error determining synthetic filename")
                    sys.exit(-1)
                outfile = os.path.join(ds.recordings_dir, outfile)
            log.info("Merging recordings %s to create %s", ' '.join([x.name for x in rec_objects]),
                     os.path.basename(outfile))
            if mockup:
                with open(outfile, 'w') as ow:
                    ow.write("")
            else:
                # Use the appropriate GNUradio script to combine the recordings
                flowgraph_dict = {
                    2: flowgraphs.merge2recordings.main,
                    3: flowgraphs.merge3recordings.main,
                    4: flowgraphs.merge4recordings.main,
                    5: flowgraphs.merge5recordings.main,
                }

                # Create the appropriate filenames to pass as arguments
                filenames = {'outfile': outfile}
                # One for each input file
                for i in range(len(rec_objects)):
                    filenames['file%s' % (i + 1)] = rec_objects[i].recfile

                args = Namespace(**filenames)

                # Call the proper flowgraph with the arguments mapping
                t = time.time()
                try:
                    flowgraph_dict[len(rec_objects)](options=args)
                    log.info("GNUradio merging time: %s", time.time()-t)
                except RuntimeError as e:
                    log.error("GNUradio failed to merge recordings. Error: ", str(e))
                    return

            # Initialize  the recording
            return cls(outfile, rec_objects[0].dataset, no_md=True)

    def __init__(self, recfile, dataset, no_md=False, recount_pictures=False):

        # Dataset istance that the recording is member of
        self.dataset = dataset

        self.plotter = None

        # Recording files and names
        # Absolute recording file path
        self.recfile = os.path.abspath(recfile)

        # File descriptor of recording file, used to read chunks of data when processing
        # Should be closed after operation.
        self.file_descriptor = None

        # Name of the recording with no extension (eg: rec_43)
        self.name = Recording.get_recname(recfile)
        # Id of recording (eg: 43)
        self.id = Recording.get_rec_id(self.name)

        # Directory for files needed for noise calculation (fft samples, SNR values, pics, etc)
        self.noise_calc_dir = os.path.join(self.dataset.noise_calc_dir, self.name)
        # SNR values file and fft samples file
        self.dat_file = os.path.join(self.noise_calc_dir, self.name + '.dat')
        self.fft_file = os.path.join(self.noise_calc_dir, self.name + '_fft.32fc')

        # Pictures directory and picture files prefix (eg: rec_43_pic_546)
        self.rec_pics_dir = os.path.join(self.dataset.pictures_dir, self.name)  # Pictures directory for the recording
        self.compressed_pics_dir = os.path.join(self.rec_pics_dir, 'compressed_pictures')
        self.pic_prefix = "%s_pic" % self.name
        self.corrected_annotations_dir = os.path.join(self.rec_pics_dir, "corrected_annotations")
        self.synthetic_annotations_dir = os.path.join(self.rec_pics_dir, "synthetic_annotations")
        self.fixed_labels_dir = os.path.join(self.rec_pics_dir, "corrected_labels")

        self._annotation_list = None
        self._synth_annotation_list = None
        self._corrected_annotation_list = None
        self._fixed_label_list = None
        self._compr_annotation_list = None
        self._pic_list = None
        self._compr_pic_list = None

        if no_md:
            self.metadata = None
        else:
            self.metadata = metadata.RecordingMetadata(self)

        if recount_pictures:
            self.metadata.no_of_pictures = self._count_all_pictures()
            self.metadata._metadata['no_of_pictures'] = self.metadata.no_of_pictures
            self.metadata.store_metadata()

    def _get_annot_list(self):
        """Get a list of annotations generated in the picture directory"""
        ann_pattern = os.path.join(self.rec_pics_dir, '%s_*.txt' % self.pic_prefix)
        return sorted(glob.glob(ann_pattern), key=lambda x: int(utils.get_id_from_pic_name(os.path.basename(x))))

    def _get_synth_annot_list(self):
        """Get a list of synthetic annotations generated for synthetic recordings"""
        ann_pattern = os.path.join(self.synthetic_annotations_dir, '%s_*.txt' % self.pic_prefix)
        return sorted(glob.glob(ann_pattern), key=lambda x: int(utils.get_id_from_pic_name(os.path.basename(x))))

    def _get_corr_annot_list(self):
        """Get a list of corrected annotations, if available"""
        ann_pattern = os.path.join(self.corrected_annotations_dir, '%s_*.txt' % self.pic_prefix)
        return sorted(glob.glob(ann_pattern), key=lambda x: int(utils.get_id_from_pic_name(os.path.basename(x))))

    def _get_fixed_label_list(self):
        """Get a list of manually fixed labels"""
        ann_pattern = os.path.join(self.fixed_labels_dir, '%s_*.txt' % self.pic_prefix)
        return sorted(glob.glob(ann_pattern), key=lambda x: int(utils.get_id_from_pic_name(os.path.basename(x))))

    def _get_compr_annot_list(self):
        """Get a list of compressed annotations generated in the compressed picture directory"""
        ann_pattern = os.path.join(self.compressed_pics_dir, '%s_*.txt' % self.pic_prefix)
        return sorted(glob.glob(ann_pattern), key=lambda x: int(utils.get_id_from_pic_name(os.path.basename(x))))

    def _get_pic_list(self, prefix=''):
        """
        Gets the pictures generated for the recording
        """
        pic_pattern = os.path.join(self.rec_pics_dir, prefix + '*.jpg')
        return sorted(glob.glob(pic_pattern), key=lambda x: int(utils.get_id_from_pic_name(os.path.basename(x))))

    def _get_compr_pic_list(self, prefix=''):
        """
        Gets the compressed pictures generated for the recording
        """
        pic_pattern = os.path.join(self.compressed_pics_dir, prefix + '*.jpg')
        return sorted(glob.glob(pic_pattern), key=lambda x: int(utils.get_id_from_pic_name(os.path.basename(x))))

    def _get_file_size(self):
        """
        Calculates the disk space occupied by this recording, including the pictures generated by it
        """
        bytes_size = os.path.getsize(self.recfile)
        try:
            bytes_size += os.path.getsize(self.rec_pics_dir)
        except OSError:
            # No pictures directory
            pass
        return utils.convert_size(bytes_size)

    def _count_all_pictures(self):
        """
        Counts all pictures associated with this recording
        """
        return len(self.compressed_pic_list) + len(self.pic_list)

    @property
    def pic_list(self):
        """Returns a list of the generated pictures for the recording"""
        if not self._pic_list:
            self._pic_list = self._get_pic_list()
        return self._pic_list

    @property
    def annotation_list(self):
        """Returns a list of annotation files (absolute paths) located in the picture directory of the recording"""
        if not self._annotation_list:
            self._annotation_list = self._get_annot_list()
        return self._annotation_list

    @property
    def synth_annotation_list(self):
        """Returns a list of synthetic annotation files (absolute paths)"""
        if not self._synth_annotation_list:
            self._synth_annotation_list = self._get_synth_annot_list()
        return self._synth_annotation_list

    @property
    def corrected_annotation_list(self):
        """Return a list of corrected annotations"""
        if not self._corrected_annotation_list:
            self._corrected_annotation_list = self._get_corr_annot_list()
        return self._corrected_annotation_list

    @property
    def fixed_label_list(self):
        """Return list of manually fixed labels"""
        if not self._fixed_label_list:
            self._fixed_label_list = self._get_fixed_label_list()
        return self._fixed_label_list

    @property
    def compressed_annotation_list(self):
        """
        Returns a list of compressed annotation files (absolute paths) located in the compressed picture directory of
        the recording
        """
        if not self._compr_annotation_list:
            self._compr_annotation_list = self._get_compr_annot_list()
        return self._compr_annotation_list

    @property
    def compressed_pic_list(self):
        """
        Returns a list of compressed picture files (absolute paths) located in the compressed picture directory of
        the recording
        """
        if not self._compr_pic_list:
            self._compr_pic_list = self._get_compr_pic_list()
        return self._compr_pic_list

    @property
    def file_size(self):
        """
        Returns the recording size including the complex samples and the generated pictures.
        File size is read from metadata or if None, it's calculated by parsing the filesystem.
        """
        # return self.metadata.metadata.get('file_size', '')
        return self.metadata.metadata.get('file_size', str(self._get_file_size()))

    def play_samples(self):
        """
        Loads the complex samples and previews them with GNUradio
        """
        log.info("Playing recording %s.", self.name)
        flowgraphs.view_samples_from_file.main(options=Namespace(filename=self.recfile, freq=2.44e9,
                                                                 refresh_rate=30, samp_rate=100e6,
                                                                 fft_size=512))
        log.info("Done.")
        return

    def gen_dat_file(self, noise_pwr_db=None, fft_size=512):
        """
        Generates the SNR file
        """

        # By default, get the noise level from metadata
        if not noise_pwr_db:
            noise_pwr_db = int(round(float(self.metadata.noise_pwr_db)))
            # Noise metadata defaults to 0 if non existant.
            if noise_pwr_db == 0:
                noise_pwr_db = -50  # -50 is a reasonable starting point for noise level

        # Create the directory if needed
        if not os.path.isdir(self.noise_calc_dir):
            os.makedirs(self.noise_calc_dir)

        flowgraphs.samples_to_dat.main(options=Namespace(filename=self.recfile,
                                                         output=os.path.splitext(self.dat_file)[0],
                                                         noise_pwr_db=noise_pwr_db, fft_size=fft_size))

    def gen_fft_file(self, fft_size=512):
        """
        Generates the fft samples
        """
        # Create the directory if needed
        if not os.path.isdir(self.noise_calc_dir):
            os.makedirs(self.noise_calc_dir)

        flowgraphs.samples_fft.main(options=Namespace(filename=self.recfile, output=os.path.splitext(self.fft_file)[0],
                                                      fft_size=fft_size))

    def remove_dat_file(self):
        """
        Deletes the SNR file
        """
        try:
            os.remove(self.dat_file)
        except OSError:
            pass

    def remove_fft_file(self):
        """
        Deletes the fft samples
        """
        try:
            os.remove(self.fft_file)
        except OSError:
            pass

    def remove_pictures(self):
        """
        Deletes all pictures and noise calculations of the recording
        """
        cmd = "rm -r %s %s" % (self.noise_calc_dir, self.rec_pics_dir)
        subprocess.call(cmd.split())

    def create_artificial_data(self, mold=None, freq_steps=None, time_steps=None, prefix=None, figdir=None, label=None):
        """
        Uses a given transmission area as a mold to create artificial data on various
        """
        if not os.environ.get('DISPLAY', None):
            log.warning("No available X server. Interactive mold creation cannot proceed without display.\n\
                        Consider connecting with X server forwarding, otherwise consider passing an input array"
                        "to use as a mold.")
            return None

        if not self.metadata.noise_pwr_db:
            log_noise, noise_variance = self.calculate_noise()
            if not log_noise:
                log.error("Recording %s: Noise level could not be determined, unable to create mold.", self.name)
                return None
        else:
            log_noise = self.metadata.noise_pwr_db
            noise_variance = self.metadata.noise_variance
            if not noise_variance:
                noise_variance = 5.568650501352949 ** 2

        log.info("Creating artificial data for recording %s", self.name)

        if label:
            try:
                # If label is given like an integer use this to annotate the pictures
                label_index = int(label)
            except ValueError:
                # otherwise look for the dataset classes to find the corresponding index
                label_index = self.dataset.metadata.ds_classes().get(label.upper(), None)

            if not label_index:
                log.error("Label not found in the dataset classes. Please update the file %s to include the desired"
                          "label or provide a label index directly for a new class.",
                          self.dataset.metadata.class_names_file)
                return

        if not mold:
            if not os.path.isfile(self.dat_file):
                self.gen_dat_file()

            log.info("Please draw a region in the following picture to identify mold")

            npoints = 512 * 512
            nbytes = npoints * 4

            # Preview the first 10 images for the user to pick a mold region
            img_index = 0
            with open(self.dat_file, 'rb') as df:
                while True:
                    if img_index > 9:
                        break
                    data = utils.load_bytes_from_fd(df, img_index * nbytes, (img_index + 1) * nbytes)

                    if not data:  # No more data to unpack
                        break

                    data = utils.data_reshape(data, -1, 512)

                    # Process the data before creating the image, create a copy to keep original intact
                    img_data = utils.data_clip(np.copy(data), -10, 50)
                    img_data = utils.img_scale(img_data, -10, 50)
                    img_data = utils.img_flip(img_data)

                    subplot = plt.subplot()

                    pltr = Plotter()
                    pltr.plot(data=img_data, subplot=subplot, options={'noise_input': True})

                    # If input area was given, break
                    if pltr.selected_areas:
                        log.info("Mold region recognized:\n%s", pltr.pretty_area_print())

                        left, right, bottom, up = pltr.area_borders()

                        # Get the average SNR from the original data (mainly before scaling)
                        mold = data[up:bottom, left:right]
                        break

        # Create a background noise array for the artificial data
        mu = log_noise
        sigma = float(noise_variance) ** 0.5
        noise_array = np.random.normal(mu - log_noise, sigma, (512, 512))

        # Prepare the prefix and save directories
        if not prefix:
            prefix = self.pic_prefix

        if not figdir:
            figdir = os.path.join('.', '%s_artificial_data' % self.name)

        if not os.path.isdir(figdir):
            os.makedirs(figdir)

        # Prepare the annotations to be augmented along with the data
        if label:
            annot = Annotation.get_annotation_from_borders(
                label_index,
                Annotation.nrmlz(left, 512),
                Annotation.nrmlz(right, 512),
                Annotation.nrmlz(bottom, 512),
                Annotation.nrmlz(up, 512)
            )

            if not annot:
                log.error("There was an error creating the original annotation. Exiting.")
                return

        img_index = 0
        for tstep in time_steps:

            # Printed (saved) image is actually flipped over the time axes to better illustrate the flow of packets over
            # time. Thus, input time steps must also be corrected to follow the flipped orientation of the image.
            tstep = 512 - tstep
            t_start = tstep - mold.shape[0] / 2
            t_end = t_start + mold.shape[0]
            for fstep in freq_steps:
                f_start = fstep - mold.shape[1] / 2
                f_end = f_start + mold.shape[1]

                artif_arr = np.copy(noise_array)
                try:
                    artif_arr[t_start:t_end, f_start:f_end] = mold
                except ValueError:
                    log.error("There was an error patching the requested region at the position with:\n"
                              "Center: (%s, %s).\n Make sure the region can fit in the image. Skipping...",
                              fstep, tstep)
                    continue
                img_name = "%s_%d.jpg" % (prefix, img_index)

                artif_arr = utils.data_clip(artif_arr, -10, 50)
                artif_arr = utils.img_flip(utils.img_scale(artif_arr, -10, 50))

                pltr = Plotter()
                pltr.plot(data=artif_arr, outfile=img_name, figdir=figdir)

                # Shift annotation accordingly and save to file
                if label:
                    annot.shift_center((Annotation.nrmlz(fstep, 512), Annotation.nrmlz(tstep, 512)))
                    annot_str = annot.get_annot_str()
                    ann_file = os.path.join(figdir, "%s_%d.txt" % (prefix, img_index))

                    with open(ann_file, 'w') as af:
                        af.write(annot_str)

                img_index += 1
        log.info("Artificial data created for recording %s", self.name)

    def calculate_noise(self):
        """
        Calculate the noise level in dB in a given region of the picture
        """

        if not os.environ.get('DISPLAY', None):
            log.warning("No available X server. Interactive noise calculation cannot proceed without display.\n\
                        Consider connecting with X server forwarding, otherwise manually calculate noise and update\
                        the recording metadata accordingly.")
            return None, None

        # Always regenerate the dat file to make sure the ground truth is consistent
        self.gen_dat_file(noise_pwr_db=-50)

        npoints = 512 * 512
        nbytes = npoints * 4

        # Preview the first 10 images for the user to pick a noise region
        log_noise = None
        img_index = 0
        with open(self.dat_file, 'rb') as df:
            while True:
                if img_index > 9:
                    break
                data = utils.load_bytes_from_fd(df, img_index * nbytes, (img_index + 1) * nbytes)

                if not data:  # No more data to unpack
                    break

                data = utils.data_reshape(data, -1, 512)

                # Process the data before creating the image, create a copy to keep original intact
                img_data = utils.data_clip(np.copy(data), -10, 50)
                img_data = utils.img_scale(img_data, -10, 50)
                img_data = utils.img_flip(img_data)

                subplot = plt.subplot()

                pltr = Plotter()
                pltr.plot(data=img_data, subplot=subplot, options={'noise_input': True})

                # If input area was given, break
                if pltr.selected_areas:
                    log.info("Noise region recognized: %s", pltr.pretty_area_print())

                    left, right, bottom, up = pltr.area_borders()

                    # Get the average SNR from the original data (mainly before scaling)
                    cropped = data[up:bottom, left:right]

                    # This is the avg SNR in the cropped region, we need to add it to the noise level that was used to
                    # create the dat file in the first place
                    avg_snr_db = np.mean(cropped)
                    noise_variance = np.var(cropped)
                    log_noise = -50 + avg_snr_db

                    # Remove dat file because it was created with a default noise value rather than the real one
                    self.remove_dat_file()
                    log.info("Noise level calculated: %s dB", log_noise)
                    break

                img_index += 1
        return log_noise, noise_variance

    def compress_annotations(self, compr_factor, merge=True):
        """
        Compress annotations into the compressed picture directory. If no original annotations are found, an error is
        returned and nothing is generated.
        """

        to_compress = self.fixed_label_list if not self.metadata.synthetic else self.synth_annotation_list

        if not to_compress:
            log.info("No corrected labels found for recording %s. Nothing to compress...", self.name)
            return
        if not os.path.isdir(self.compressed_pics_dir):
            os.mkdir(self.compressed_pics_dir)

        compressed_pic_annotations = []

        # Fetch all original annotations for every picture
        for pic_ann in to_compress:
            new_pic_index = to_compress.index(pic_ann) / compr_factor
            pic_index = to_compress.index(pic_ann) % compr_factor
            with open(pic_ann, 'r') as orig_ann:
                pic_annotations = orig_ann.read().strip().split('\n')

            extend_annot = [annotation.Annotation.get_annotation_from_str(x) for x in pic_annotations]
            extend_annot = [annotation.Annotation.compress_annotation(x, compr_factor, pic_index) for x in
                            extend_annot]
            compressed_pic_annotations.extend(extend_annot)

            # Save the compressed annotation
            if pic_index == compr_factor - 1:
                if merge:
                    compressed_pic_annotations = annotation.Annotation.merge_annotations(compressed_pic_annotations)
                compressed_pic_annotations = '\n'.join([x.get_annot_str() for x in compressed_pic_annotations
                                                        if x.get_annot_str()])
                compressed_ann_file = os.path.join(self.compressed_pics_dir,
                                                   self.pic_prefix + "_" + str(new_pic_index) + ".txt")
                with open(compressed_ann_file, 'w') as comp_ann:
                    comp_ann.write(compressed_pic_annotations)
                compressed_pic_annotations = []

        log.info("Compressed annotations for recording %s were saved in: %s", self.name, self.compressed_pics_dir)

    def generate_pictures(self, log_noise=None, nfft=512, nlines=512, navg=3, nproc=4, npics=0, pic_prefix=None,
                          mode='grayscale', expand=None, trim=50):
        """
        Generates pictures from a recording file
        """

        # Clipping parameters
        min_snr = -10
        max_snr = 50

        log.info("Generating pictures for recording: %s", self.name)

        # Use recorded noise measurements unless overridden
        noise_var = None
        if not log_noise:
            log_noise = int(round(self.metadata.noise_pwr_db))
            if not log_noise:
                log_noise, noise_var = self.calculate_noise()
                if not log_noise:
                    log.error("Recording %s: Noise level could not be determined, no pictures generated.", self.name)
                    return
                else:
                    self.metadata.noise_pwr_db = log_noise
                    self.metadata.noise_variance = noise_var
                    self.metadata._metadata['noise_db'] = self.metadata.noise_pwr_db
                    self.metadata._metadata['noise_variance'] = self.metadata.noise_variance
                    self.metadata.store_metadata()
                    log_noise = int(round(float(self.metadata.noise_pwr_db)))
        if not noise_var:
            noise_var = float(self.metadata.noise_variance)
            if not noise_var:
                noise_var = Recording.heuristic_noise_calculation

        # If expanding to a wider bandwidth, create array with noise values as background
        if expand:
            transm_freq = float(expand[0])
            transm_rate = float(expand[1])
            wide_freq = float(expand[2])
            wide_rate = float(expand[3])
            avg_factor = int(wide_rate / transm_rate)
            mu = log_noise
            sigma = float(noise_var) ** 0.5
            noise_array = np.random.normal(mu-log_noise, sigma, (nlines, nfft * avg_factor))

        if not os.path.isdir(self.rec_pics_dir):
            os.makedirs(self.rec_pics_dir)

        # Use default picture prefix unless specified
        if not pic_prefix:
            pic_prefix = self.pic_prefix

        npoints = nfft * nlines * navg * nproc

        if mode.lower() == 'grayscale':

            if not os.path.isfile(self.dat_file):
                self.gen_dat_file()

            nbytes = npoints * 4

            img_index = 0
            with open(self.dat_file, "rb") as df:
                while True:
                    data = utils.load_bytes_from_fd(df, img_index * nbytes, (img_index + 1) * nbytes)

                    if not data:  # No more data to unpack
                        break

                    # Reshape into an array of (nfft, nlines)
                    data = utils.data_reshape(data, -1, nfft)

                    # If expanding to a wider bandwidth average the loaded data accordingly and fit them into the
                    # previously created noise array (background)
                    if expand:
                        if not trim:
                            trim = 0
                        # Position the transmission subarray in the new wider array
                        new_start_freq = wide_freq - wide_rate / 2.0
                        sub_array_center = int((transm_freq - new_start_freq) * (int(nfft) / wide_rate) * avg_factor)
                        sub_array_size = int(nfft)
                        sub_array_start = sub_array_center - sub_array_size / 2
                        sub_array_end = sub_array_start + sub_array_size

                        noise_array[:, sub_array_start + trim:sub_array_end - trim] = data[:, trim:-trim]

                        data = noise_array

                    greyscale_avg = navg * nproc
                    if greyscale_avg > 1 and type(greyscale_avg) is int:
                        avg_data = np.empty((int(data.shape[0] / greyscale_avg), data.shape[1]))
                        for i in range(0, data.shape[0], greyscale_avg):
                            try:
                                avg_data[int(i / greyscale_avg)] = np.mean(data[i:i + greyscale_avg], axis=0, keepdims=True)
                            except IndexError as e:
                                if int(i / greyscale_avg) >= data.shape[0] / greyscale_avg:
                                    # Last chunk of data reached
                                    break
                                else:
                                    raise e
                    else:
                        avg_data = data

                    avg_data = utils.data_clip(avg_data, min_snr, max_snr)
                    avg_data = utils.img_flip(utils.img_scale(avg_data, min_snr, max_snr))

                    img_name = "%s_%d.jpg" % (pic_prefix, img_index)

                    pltr = Plotter()
                    pltr.plot(data=avg_data, outfile=img_name, figdir=self.rec_pics_dir, resize=(nfft, nlines))

                    img_index += 1

                    # Check if img limit is reached and exit
                    if npics and npics > 0:
                        if img_index >= npics:
                            break

            self.remove_dat_file()

        elif mode.lower() == 'compressed':
            self.gen_fft_file()
            plot_recording(self.fft_file, self.compressed_pics_dir, pic_prefix, nfft, nlines, navg, nproc,
                           log_noise=log_noise, img_mode=mode, disp="save", img_limit=npics)
            self.remove_fft_file()

        if not npics:
            npics = 'All'
        pic_out_dir = self.rec_pics_dir if mode == 'grayscale' else self.compressed_pics_dir
        log.info("%s pictures were generated in the directory: %s", npics, pic_out_dir)
        return

    def print_info(self):
        """
        Prints info about the recording
        """
        log.info("\
Information about recording %s:\n\n\
Recorded on %s. \n\n\
Number of pictures generated: %s\n\n\
Metadata \n%s", self.name,
                 self.metadata.date_recorded,
                 self.metadata.no_of_pictures,
                 self.metadata.get_md_string())
        log.info(json.dumps(self.metadata.metadata))
