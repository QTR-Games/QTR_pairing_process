""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """

import os
# Rating System Configurations
RATING_SYSTEMS = {
    '1-3': {
        'name': '1-3 (Green/Yellow/Red)',
        'range': (1, 3),
        'description': '1=Worst, 2=Even (50/50), 3=Best',
        'color_map': {
            '1': 'orangered',    # Red - Worst matchup
            '2': 'yellow',       # Yellow - Even matchup
            '3': 'lime'          # Green - Best matchup
        }
    },
    '1-5': {
        'name': '1-5 (Standard)',
        'range': (1, 5),
        'description': '1=Worst, 3=Even, 5=Best',
        'color_map': {
            '1': 'orangered',
            '2': 'orange',
            '3': 'yellow',
            '4': 'greenyellow',
            '5': 'lime'
        }
    },
    '1-10': {
        'name': '1-10 (British)',
        'range': (1, 10),
        'description': '1=Worst, 5-6=Even, 10=Best',
        'color_map': {
            '1': 'darkred',
            '2': 'red',
            '3': 'orangered',
            '4': 'orange',
            '5': 'gold',
            '6': 'yellow',
            '7': 'yellowgreen',
            '8': 'greenyellow',
            '9': 'lightgreen',
            '10': 'lime'
        }
    }
}

# Default system (backward compatibility)
DEFAULT_RATING_SYSTEM = '1-5'
DEFAULT_COLOR_MAP = RATING_SYSTEMS[DEFAULT_RATING_SYSTEM]['color_map']

# MATT_DIR = '.'
# DAN_DIR = "C:/Users/Daniel.Raven/OneDrive - Vertex, Inc/Documents/myStuff/WM/Python Pairing Process"
DIRECTORY = os.getcwd()

SCENARIO_MAP = {
    0: "1 - Trench Warfare",
    1: "2 - Two Fronts",
    2: "3 - Wolves At Our Heels",
    3: "4 - Pressure Point",
    4: "5 - High Stakes",
    5: "6 - Fault Line",
    6: "7 - Payload"}

SCENARIO_RANGES = {
    0: (1, 6),
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

