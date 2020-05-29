""" """

import string

from typing import Dict, Optional


def punct_stripper() -> Dict[int, Optional[int]]:
    return str.maketrans('', '', string.punctuation)
