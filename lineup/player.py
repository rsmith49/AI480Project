from database.connect_local import Connection
from score.predict import scorePlayer, datenum_to_str
from dateutil.parser import parse

pos_to_num_map = {
    'DH': 5,
    'SP': 1,
    'RP': 1,
    'C': 2,
    '1B': 3,
    '2B': 4,
    '3B': 5,
    'SS': 6,
    'LF': 7,
    'CF': 8,
    'RF': 9
}


class Player:

    def __init__(self, espnID, pos, name=None, fd_salary=None):
        self.espnID = espnID
        if pos in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
            self.pos = pos
        else:
            self.pos = pos_to_num_map[pos]
        self.name = name
        self.pred_score = {}
        self.fd_salary = {}
        if fd_salary:
            for key in fd_salary.keys():
                self.fd_salary[key] = fd_salary[key]
        self.table_prefix = "player"

    def predict_score(self, date):
        pass

    def get_salary(self, date):
        if date in self.fd_salary:
            return self.fd_salary[date]
        else:
            conn = Connection()
            conn.connect()
            sqlquery = "SELECT fd_salary FROM " + self.table_prefix + "_daily_" + str(date.year)\
            + " WHERE espnID = " + str(self.espnID) + " AND `date` = '" + datenum_to_str[date.month]\
            + " " + str(date.day) + "'"
            salary = conn.query(sqlquery)
            if not salary:
                #print("No salary data available for date " + str(date))
                conn.close()
                self.fd_salary[date] = None
                return False
            salary = salary[0][0]
            self.fd_salary[date] = salary
            conn.close()
            return salary

    def load_salaries(self, dates):
        if dates == self.fd_salary.keys():
            return
        conn = Connection()
        conn.connect()

        distinct_years = list(set([date.year for date in dates]))

        for year in distinct_years:
            sqlquery = "SELECT `date`, fd_salary FROM " + self.table_prefix + "_daily_" + str(year)\
                    + " WHERE espnID = " + str(self.espnID) + " AND `date` in ("
            for date in [date for date in dates if date.year == year]:
                sqlquery += "'" + datenum_to_str[date.month] + " " + str(date.day) + "',"
            sqlquery = sqlquery[:-1] + ")"

            salaries = conn.query(sqlquery)
            for date_str, salary in salaries:
                date = parse(date_str + " " + str(year))
                self.fd_salary[date] = salary

        conn.close()

    def actual_score(self, date):
        return None

    def __eq__(self, other):
        if (not hasattr(other, 'espnID')) or self.espnID != other.espnID:
            return False
        if (not hasattr(other, 'name')) or self.name != other.name:
            return False
        if (not hasattr(other, 'table_prefix')) or self.table_prefix != other.table_prefix:
            return False
        return True

    def __str__(self):
        if self.name:
            return 'Player(' + str(self.espnID) + ', ' + str(self.name) + ')'
        else:
            return 'Player(' + str(self.espnID) + ')'

    def __hash__(self):
        return hash(self.espnID)


class Hitter(Player):

    def predict_score(self, date):
        if date in self.pred_score:
            return self.pred_score[date]
        else:
            conn = Connection()
            conn.connect()
            self.pred_score[date] = scorePlayer(self, date, conn)
            conn.close()
            return self.pred_score[date]

    def __str(self):
        if self.name:
            return 'Hitter(' + str(self.espnID) + ', ' + str(self.name) + ')'
        else:
            return 'Hitter(' + str(self.espnID) + ')'


class Pitcher(Player):

    def __init__(self, espnID, pos, name=None, fd_salary=None):
        super().__init__(espnID, pos, name, fd_salary)
        self.table_prefix = 'pitcher'

    def predict_score(self, date):
        if date in self.pred_score:
            return self.pred_score[date]
        else:
            conn = Connection()
            conn.connect()
            self.pred_score[date] = scorePlayer(self, date, conn, hitter=False)
            conn.close()
            return self.pred_score[date]

    def __str__(self):
        if self.name:
            return 'Pitcher(' + str(self.espnID) + ', ' + str(self.name) + ')'
        else:
            return 'Pitcher(' + str(self.espnID) + ')'