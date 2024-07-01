""" © Daniel P Raven and Matt Russell 2024 All Rights Reserved """

def cycle_list(lst):
    return lst[1:] + lst[:1]

def maximum(a, b):
    return a if a >= b else b