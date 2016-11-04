date_string_map = {
        "key-string": {
            "Jan": 1,
            "Feb": 2,
            "Mar": 3,
            "Apr": 4,
            "May": 5,
            "Jun": 6,
            "Jul": 7,
            "Aug": 8,
            "Sep": 9,
            "Oct": 10,
            "Nov": 11,
            "Dec": 12
        }, "key-num": {
            1: "Jan",
            2: "Feb",
            3: "Mar",
            4: "Apr",
            5: "May",
            6: "Jun",
            7: "Jul",
            8: "Aug",
            9: "Sep",
            10: "Oct",
            11: "Nov",
            12: "Dec"
        }
    }

class Date:

    def __init__(self, date_string=None, day=0, month=0, year=2002):
        if date_string:
            self.month = date_string[:3]
            self.day = int(date_string[3:])
            self.year = year
        else:
            self.day = day
            self.month = month
            self.year = year

    def date_string(self):
        date_str = ''
        date_str += date_string_map['key-num'][self.month]
        date_str += ' '
        date_str += self.day

