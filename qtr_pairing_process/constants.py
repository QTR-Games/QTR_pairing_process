""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """

import os
DEFAULT_COLOR_MAP = {
    '1': 'orangered',
    '2': 'orange',
    '3': 'yellow',
    '4': 'greenyellow',
    '5': 'lime'
}

# MATT_DIR = '.'
# DAN_DIR = "C:/Users/Daniel.Raven/OneDrive - Vertex, Inc/Documents/myStuff/WM/Python Pairing Process"
DIRECTORY = os.getcwd()

SCENARIO_MAP = {
    0: "0 - Neutral",
    1: "1 - Recon",
    2: "2 - Battle Lines",
    3: "3 - Wolves At Our Heels",
    4: "4 - Payload",
    5: "5 - Two Fronts",
    6: "6 - Invasion"}

SCENARIO_RANGES = {
    0: (1, 6),    # Scenario Agnostic
    1: (7, 12),
    2: (13, 18),
    3: (19, 24),
    4: (25, 30),
    5: (31, 36),
    6: (37, 42)
}

SCENARIO_TO_CSV_MAP = {
    0: "1,6",
    1: "7,12",
    2: "13,18",
    3: "19,24",
    4: "25,30",
    5: "31,36",
    6: "37,42"
}

