from database.connect_local import Connection
import score.predict
from dateutil.parser import parse

datenum_to_str = {
    1: 'Jan',
    2: 'Feb',
    3: 'Mar',
    4: 'Apr',
    5: 'May',
    6: 'Jun',
    7: 'Jul',
    8: 'Aug',
    9: 'Sep',
    10: 'Oct',
    11: 'Nov',
    12: 'Dec'
}

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

num_to_pos_map = {
    1: 'SP',
    2: 'C',
    3: '1B',
    4: '2B',
    5: '3B',
    6: 'SS',
    7: 'LF',
    8: 'CF',
    9: 'RF'
}


class Player:

    def __init__(self, espnID, pos, name=None, fd_salary=None):
        self.espnID = espnID
        if pos in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
            self.pos_num = pos
            self.position = num_to_pos_map[pos]
        else:
            self.pos_num = pos_to_num_map[pos]
            self.position = pos
        self.name = name
        self.pred_score = {}
        self.fd_salary = {}
        self.real_score = {}
        if fd_salary:
            for key in fd_salary.keys():
                self.fd_salary[key] = fd_salary[key]
        self.table_prefix = "player"

    def predict_score(self, date):
        if date in self.pred_score:
            return self.pred_score[date]
        else:
            conn = Connection()
            conn.connect()
            self.pred_score[date] = score.predict.scorePlayer(self, date, conn)
            conn.close()
            return self.pred_score[date]

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
        new_dates = [date for date in dates if not dates in self.fd_salary.keys()]
        if len(new_dates) == 0:
            return

        conn = Connection()
        conn.connect()

        distinct_years = list(set([date.year for date in new_dates]))

        for year in distinct_years:
            sqlquery = "SELECT `date`, fd_salary FROM " + self.table_prefix + "_daily_" + str(year)\
                    + " WHERE espnID = " + str(self.espnID) + " AND `date` in ("
            for date in [date for date in new_dates if date.year == year]:
                sqlquery += "'" + datenum_to_str[date.month] + " " + str(date.day) + "',"
            sqlquery = sqlquery[:-1] + ")"

            salaries = conn.query(sqlquery)
            for date_str, salary in salaries:
                date = parse(date_str + " " + str(year))
                self.fd_salary[date] = salary

        conn.close()

    def actual_score(self, date):
        if date in self.real_score:
            return self.real_score[date]
        conn = Connection()
        conn.connect()

        sqlquery = "SELECT fd_points FROM " + self.table_prefix + "_daily_" + str(date.year) + " WHERE espnID = " \
                   + str(self.espnID) + " AND `date` = '" + datenum_to_str[date.month] + " " + str(date.day) + "'"
        score = conn.query(sqlquery)
        if score:
            score = score[0][0]
        else:
            score = None
        self.real_score[date] = score

        return score

    def load_actual_scores(self, dates):
        new_dates = [date for date in dates if not date in self.real_score.keys()]
        if len(new_dates) == 0:
            return

        conn = Connection()
        conn.connect()

        distinct_years = list(set([date.year for date in new_dates]))

        for year in distinct_years:
            sqlquery = "SELECT `date`, fd_points FROM " + self.table_prefix + "_daily_" + str(year) \
                       + " WHERE espnID = " + str(self.espnID) + " AND `date` in ("
            for date in [date for date in new_dates if date.year == year]:
                sqlquery += "'" + datenum_to_str[date.month] + " " + str(date.day) + "',"
            sqlquery = sqlquery[:-1] + ")"

            scores = conn.query(sqlquery)
            for date_str, score in scores:
                date = parse(date_str + " " + str(year))
                self.real_score[date] = score
        for date in dates:
            if date not in self.real_score.keys():
                self.real_score[date] = None

        conn.close()

    def dates_scored(self):
        return self.real_score.keys()

    def sals_loaded(self):
        return self.fd_salary.keys()

    def dates_predicted(self):
        return self.pred_score.keys()

    def __eq__(self, other):
        if (not hasattr(other, 'espnID')) or self.espnID != other.espnID:
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

    def __str__(self):
        if self.name:
            return 'Hitter(' + str(self.name) + ', ' + str(self.position) + ')'
        else:
            return 'Hitter(' + str(self.espnID) + ', ' + str(self.position) + ')'

    def __copy__(self):
        new_hitter = Hitter(self.espnID, self.pos_num, self.name)
        new_hitter.fd_salary = self.fd_salary
        new_hitter.pred_score = self.pred_score
        return new_hitter


class Pitcher(Player):

    def __init__(self, espnID, pos, name=None, fd_salary=None):
        super().__init__(espnID, pos, name, fd_salary)
        self.table_prefix = 'pitcher'

    def __str__(self):
        if self.name:
            return 'Pitcher(' + str(self.espnID) + ', ' + str(self.name) + ')'
        else:
            return 'Pitcher(' + str(self.espnID) + ')'