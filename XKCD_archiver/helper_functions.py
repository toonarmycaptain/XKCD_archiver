""" """

import string


def punct_stripper() -> dict[int, int | None]:
    return str.maketrans("", "", string.punctuation)
