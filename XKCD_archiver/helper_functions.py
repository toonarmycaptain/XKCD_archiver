""" """

import string


def punct_stripper():
    return str.maketrans('', '', string.punctuation)
