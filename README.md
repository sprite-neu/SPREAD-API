# SPREAD supporting API

This is a set of tools for parsing and printing the information about the signal classification dataset, and performing some operations on the recordings.

## Requirements

Tested in Ubuntu 18.04.

- python 2.7
- numpy
- pillow
- pandas
- matplotlib
- python-tk
- Gnuradio Companion 3.7 (tested in 3.7.10.1)

Optional:
- hurry.filesize (pip install hurry.filesize)

## SPREAD Dataset structure (Medium and Large)

Structure goes here (maybe using `tree`)

dataset\
├── annotations\
│   ├── noi_1\
│   │   ├── noi_1_pic_0.jpg\
│   │   ├── noi_1_pic_1.jpg\
│   ├── rec_1\
│   │   ├── rec_1_pic_0.jpg\
│   │   ├── rec_1_pic_1.jpg\
... ... ... ...\
└── recordings\
     ├── noi_1.32fc\
     ├── noi_1.json\
     ├── rec_1.32fc\
     ├── rec_1.json\
     ├── rec_2.32fc\
     ├── rec_2.json\
     │  ...  ...\
└── anechoic_data\
     ├── rec_154.32fc\
     ├── rec_154.json\
     ├── rec_155.32fc\
     ├── rec_155.json\
     │  ...  ...



## Tools

**Note:** All tools require the `--dataset` option to point to the root directory of the dataset.

### Usage

We recommend users to use our developed functions for flexible usage of the API. Additionally, we also create example scripts for getting started with the API in some basic cases. The details of those scripts is presented below. 

### Print info

`print_dataset.py`

Prints information about the dataset. Options:

```
--recordings rec_1 rec_2 ...:   Prints information about the specified recordings

--show class=wifi duration=10 ...: Prints recordings that satisfy the given filters

--contents: Print out and save a table of contents for the dataset that includes important information about each recording

--no-show: Don't print out the table of contents, just save to files (under dataset/metadata as csv and json files)
```

Examples:
```
python2.7 print_dataset.py --dataset /path/to/dataset/root --recordings rec_12 syn_1324
python2.7 print_dataset.py --dataset /path/to/dataset/root --contents --no-show
```

#### Augment dataset

`augment_dataset.py`

Augment the dataset by creating synthetic emissions.

```
--categories wifi, bt: Type of synthetic emission to create. Specifying two categories simulates an emission.  

--snr-range -10 0 10: SNR values for the synthetic emissions

--length-range 62 512: Range for adjustment of emissions length

--length-step 15: Length adjustment step (for 100MHz recordings, a step of 10 corresponds to ~50us)
```

Example:
```
python2.7 augment_dataset.py --categories 1 --save-path /path/to/save/directory
```

#### Generate pictures

`generate_pictures.py`

Generates the pictures for the specified recordings. If no recordings are specified, it creates the pictures for all dataset recordings that do not have any pictures associated with them.

```
--recordings rec_1 rec_2 ...: Recording files

--mode: Choose mode to generate pictures. Choices are 'grayscale' or 'compressed'.
        Grayscale pictures are the depiction of SNR levels in the recording.
        In the compressed mode, the original pictures are compressed by a certain factor
        and the result is depicted in the RGB channel. The compression factor is dictated by
        `compr-avg` and `compr-proc` arguments: `compr-factor = compr-avg * compr-proc`.
        
--compr-avg, --compr-proc: Default values set to 3 and 4, meaning default compression factor is 12.

--log-noise: Use a specified noise level instead of the noise measured and stored in the recording metadata

--img-limit: Only generate that many pictures

--overwrite: Generate even if there are already pictures. Delete the old ones first.
```

Example:
```
python2.7 generate_pictures.py --dataset /path/to/dataset/root --recordings rec_12 rec_54 --mode compressed
```

#### Generate compressed data

`generate_compressed_data.py`

Generates compressed pictures and/or annotations for the specified recordings.

```
--recordings rec_1 rec_2 ...: Recording files

--compr-avg, --compr-proc: Default values set to 3 and 4, meaning default compression factor is 12.

--pictures-only, --annotations-only: only creates compressed pictures or annotations respectively. If
not specified, both pictures and annotations are created.
```

Example:
```
python2.7 generate_compressed_data.py --dataset /path/to/dataset/root --recordings rec_12 --compr-factor 12
```

### Combine recordings

`combine_recordings.py`

Combine recorded data to create simulated recordings. The same script can also be used to combine the annotations for a
created synthetic recording.

```
--from-files rec_1 rec_2 ...: Source files (in crop mode only 1st argument is parsed, rest are ignored)

--from-properties class=wifi,channel=3 class=zigbee,type=data class=bluetooth,transmission=continuous ...: Source files in the form of property filters

--to-files syn_1 syn_2 ...: Output files (in merge mode only 1st argument is parsed, rest are ignored)

--combine-annotations: Create annotations for the specified (or all) synthetic recordings.

--synthetics syn_1 syn_32: Specify the synthetic recordings to combine annotations for. If not specified, all synthetics
are processed.
```

Example:
```
python2.7 combine_recordings.py --dataset /path/to/dataset/root --from-files rec_53 rec_12
```


## Notes

### Recordings

The recordings were attempted in various SNR levels in order to identify a proper range of SNR for each class.
SNR levels are categorized in three ranges, high, mid, and low, each of them different for each class. Two DC peaks are observed when converting recorded samples to pictures: One at 2.440GHz and one at the RX center frequency. They are uncontrolled artifacts from the RX radio hardware (ETTUS USRP X310). These properties are not labelled in the dataset and generally have no impact on training and testing.

### Metadata

To resolve some technical issues and support additional use cases, we applied a small change to the metadata of recordings, compared to the example demonstation in the paper (*This only changes the format of some metadata fields and does not affect the functionality of the API*). Specifically, for fields where multiple values are required, a comma-separated string is used
instead of a dictionary. For example, for the SNR values of a recording with more than one
transmission, the field would be: `"snr": "wifi_17,wmic_18,wifi_21"`, instead of
`"snr": {"wifi":17, "wmic":18, "wifi":21}`. This way ordering is strictly preserved in SNR
values, and type of transmissions, e.g.: `"classes": "wifi,wmic,wifi`. Additionally,
multiple instances of the same transmission type are allowed.


## Reference our project

For any use of this project for research, academic publications, or other publications which include a bibliography, please include the citations in the [Bibtex](https://github.com/sprite-neu/SPREAD-API/blob/master/ref.bib) file. 
This is the reference for the dataset only:

```
@electronic{spread:project,
        author = {Nguyen, Hai N and Vomvas, Marinos and Vo-Huu, Triet and Noubir, Guevara},
        title = {SPREAD: An Open Dataset for Spectro-Temporal RF Identification},
        url = {https://sprite.ccs.neu.edu/datasets/SPREAD/},
        year = {2023}
}       
```