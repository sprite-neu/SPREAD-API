"""
Definition of dataset tables
"""
import pandas as pd
import logging
import os
import json

from collections import defaultdict

log = logging.getLogger('spread')


class DatasetTable(object):
    """
    Represents an instance of a dataset content table containing information about the dataset recordings
    """

    # Table format
    # Any changes here will reflect on the output of the table
    # Mind that the separator must be comma and space (ie: ", ")
    # in order to be parsed 
    table_format = '''
    Recording, Synthetic, Sources, Class, Channel, Noise level (dB), SNR (dB; estimate)
    '''.strip()

    string_size_thres = 20

    @staticmethod
    def get_short_name(data_str):
        """
        Return a short name for a given string, mainly by shortening the class names
        in order to reduce the necessary table width and increase readability
        :param data_str:    original string
        :return:            short_version
        """
        # Set a threshold to avoid shortening when not necessary
        if len(str(data_str)) < DatasetTable.string_size_thres:
            return data_str
        else:
            return data_str.replace('lightbridge', 'LiBr').replace('bluetooth', 'Blth').replace('zigbee', 'ZgB')

    @staticmethod
    def table_to_md_mapping(column, rec):
        """
        Given a recording object, return the metadata info for the table columns
        """

        # Mapping between table columns and recording attributes
        table_rec_mapping = {
                'Recording':            rec.name,
                'Synthetic':            rec.metadata.synthetic,
                'Sources':              '-' if not rec.metadata.synthetic else ','.join(rec.metadata.sources),
                'Class':                DatasetTable.get_short_name(','.join(rec.metadata.d_class)),
                'Channel':              DatasetTable.get_short_name(','.join(rec.metadata.channel)),
                'Noise level (dB)':     round(rec.metadata.noise_pwr_db, 2),
                'SNR (dB; estimate)':   DatasetTable.get_short_name("%s (%s)" % (','.join(rec.metadata.snr),
                                                                                 ','.join(rec.metadata.snr_range))),
            }

        return table_rec_mapping[column]

    def __init__(self, dataset, csv_file=None, json_file=None):

        # Dataset
        self.dataset = dataset

        # CSV file
        self.csv_file = csv_file if csv_file else os.path.join(self.dataset.metadata_dir, "table_of_contents.csv")

        # JSON file
        self.json_file = json_file if json_file else os.path.join(self.dataset.metadata_dir, "table_of_contents.json")
        self.reclist_json_file = os.path.join(self.dataset.metadata_dir, "list_of_recordings.json")

        self.table_columns = self.table_format.split(', ')
        self.table_dict = defaultdict(list)

        for rec in self.dataset.sorted_recordings:
            for column in self.table_columns:
                try:
                    self.table_dict[column].append(DatasetTable.table_to_md_mapping(column, rec))
                except Exception as e:
                    print(e, column)
                    exit()

        self.table = pd.DataFrame(data=self.table_dict)
        self.table = self.table[self.table_format.split(', ')]

    def get_table_str(self, index=False):
        """
        Prints the table of contents
        """
        return self.table.to_string(index=index)

    def save_to_csv(self):
        """
        Saves the table of contents in the csv file
        """
        if not self.csv_file:
            log.error("No csv file specified.")
            return
        else:
            self.table.to_csv(self.csv_file, index=False, encoding='utf8')

    def save_to_json(self):
        """
        Saves the table of contents in the json file
        """
        if not self.json_file:
            log.error("No json file specified.")
            return
        else:
            self.table.to_json(self.json_file)

    def save_reclist_to_json(self):
        """
        Saves the list of recording names to a json file
        """
        with open(self.reclist_json_file, 'w') as jw:
            json.dump(self.dataset.sorted_recording_names, jw)
