import os
DEFAULT_COLOR_MAP = {
    '1': 'orangered',
    '2': 'orange',
    '3': 'yellow',
    '4': 'yellowgreen',
    '5': 'deepskyblue'
}

# MATT_DIR = '.'
# DAN_DIR = "C:/Users/Daniel.Raven/OneDrive - Vertex, Inc/Documents/myStuff/WM/Python Pairing Process"
DIRECTORY = os.getcwd()

SCENARIO_MAP = {
    '1': "1 - Recon",
    '2': "2 - Battle Lines",
    '3': "3 - Wolves At Our Heels",
    '4': "4 - Payload",
    '5': "5 - Two Fronts",
    '6': "6 - Invasion"}

SCENARIO_TO_CSV_MAP = {
    0: 1,
    1: 7,
    2: 13,
    3: 19,
    4: 25,
    5: 31,
    6: 37
}
