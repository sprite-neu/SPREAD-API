"""
Constant values for the dataset toolset
"""
CLASSES = {
    0: 'wifi',
    1: 'bluetooth',
    2: 'zigbee',
    3: 'lightbridge',
    4: 'wmic'
}

CLASS_INDEX = {CLASSES[x]: x for x in CLASSES}

COLORS = {
    0: (82, 250, 88),
    1: (231, 242, 80),
    2: (240, 31, 38),
    3: (122, 57, 95),
    4: (43, 168, 224),
}

UNITS = {
    'Hz': 1,
    'B': 1,
    'K': 1e3,
    'M': 1e6,
    'G': 1e9,
    'T': 1e12,
}

# SNR ranges for each class were identified heuristically and are defined here
SNR_RANGES = {
    'label': ['high', 'mid', 'low'],
    'wifi': [27, 15, 0],
    'bluetooth': [22, 13, 0],
    'zigbee': [27, 13, 0],
    'lightbridge': [27, 13, 0],
    'wmic': [22, 15, 0],
}

# Thresholds for merging annotation boxes
# (different for each class depending on the possible overlapping with the adjacent channels
SIDE_THRESHOLD = {
    0: 0.1,
    1: 0.3,
    2: 0.5,
    3: 0.5,
    4: 0.5,
}

TIME_THRESHOLD = {
    0: 2 / 512.0,
    1: 1 / 512.0,
    2: 1 / 512.0,
    3: 2 / 512.0,
    4: 2 / 512.0,
}

# RF characteristics of the classes for all channels as a tuple of center frequencies and bw
CHANNELS = {
    0: ({x: y for x, y in zip(range(14), range(2412, 2475, 5))}, 22),
    1: ({x: y for x, y in zip(['n/a'], ['n/a'])}, 1),
    2: ({x: y for x, y in zip(range(11, 27), range(2405, 2485, 5))}, 2),
    3: ({x: y for x, y in zip(range(13, 21), range(2406, 2476, 10))}, 10),
    4: ({x: y for x, y in zip(['n/a'], ['n/a'])}, 2),
}

"""
Constant values for the augmentation script
"""

CATEGORIES = {
    -1: {"main": "background", "element": ["background"]},
    0: {"main": "wifi", "element": ["wifi_1", "wifi_2"]},
    1: {"main": "bluetooth", "element": ["bt_1", "bt_2"]},
    2: {"main": "zigbee", "element": ["zigbee"]},
    3: {"main": "lightbridge", "element": ["lightbridge"]},
    4: {"main": "wmic", "element": ["wmic"]}
}

MOLD_PATHS = {
    'background': 'augmentation_data/molds/background.npy',
    'wifi_1': 'augmentation_data/molds/wifi_1.npy',
    'wifi_2': 'augmentation_data/molds/wifi_2.npy',
    'bt_1': 'augmentation_data/molds/bt_1.npy',
    'bt_2': 'augmentation_data/molds/bt_2.npy',
    'zigbee': 'augmentation_data/molds/zigbee.npy',
    'lightbridge': 'augmentation_data/molds/lightbridge.npy',
    'wmic': 'augmentation_data/molds/wmic.npy',
}

VAR = {
    'background': None,
    'wifi_1': True,
    'wifi_2': False,
    'bt_1': True,
    'bt_2': True,
    'zigbee': True,
    'lightbridge': True,
    'wmic': True,
}

# Mimicking wireless channels.
# Recording frequency range 2390 - 2490
AUGMENT_CHANNELS = {
    0: {'start': 56, 'space': 25, 'skip': 2},
    # WiFi: From 2401 MHz -> (2401-2390)/100*512 ~ 56, channel splace 5 MHz -> 5/100*512 ~25
    1: {'start': 56, 'space': 10, 'skip': 5},
    # Bluetooth (Considering BLE): From 2401 MHz -> (2401-2390)/100*512 ~ 56, channel splace 2 MHz -> 2/100*512 ~ 10
    2: {'start': 71, 'space': 25, 'skip': 2},
    # Zigbee: From 2404 MHz -> (2404-2390)/100*512 ~ 71, channel splace 5 MHz -> 5/100*512 ~25
    3: {'start': 61, 'space': 51, 'skip': 1},
    # Lightbridge: From 2402 MHz -> (2402-2390)/100*512 ~ 61, channel space 10 MHz -> 10/100*512 ~ 51
    4: {'start': 56, 'space': 25, 'skip': 2},  # Wireless microphone: Avoid complexity, set it the same as Zigbee.
}

LIMIT_INDEX = 476  # Max. freq = 2483 MHz (WiFi), (2483-2390)/100*512 ~ 476

# IMAGE MAPPING
VMIN = -10
VMAX = 50
