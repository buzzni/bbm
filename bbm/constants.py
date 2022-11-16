from enum import Enum

import pytz

KST = pytz.timezone("Asia/Seoul")


class Interval(int, Enum):
    A_MINUTE = 60
    TWO_MINUTES = A_MINUTE * 2
    FIVE_MINUTES = A_MINUTE * 5
    TEN_MINUTES = A_MINUTE * 10
    THIRTY_MINUTES = A_MINUTE * 30

    A_HOUR = 60 * 60
    TWO_HOURS = A_HOUR * 2
    TWO_AND_HALF_HOURS = (A_HOUR * 2) + (A_MINUTE * 30)
    SIX_HOURS = A_HOUR * 6

    A_DAY = A_HOUR * 24
