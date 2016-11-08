from database.connect_local import Connection
from score.predict import scorePlayer, datenum_to_str


class Player:

    def __init__(self, espnID, fd_salary=None):
        self.espnID = espnID
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
                print("No salary data available for date " + str(date))
                conn.close()
                self.fd_salary[date] = None
                return False
            salary = salary[0][0]
            self.fd_salary[date] = salary
            conn.close()
            return salary

    def load_salaries(self, dates):
        for date in dates:
            self.get_salary(date)


    def actual_score(self, date):
        return None


class Hitter(Player):

    def predict_score(self, date):
        if date in self.pred_score:
            return self.pred_score[date]
        else:
            conn = Connection()
            conn.connect()
            self.pred_score[date] = scorePlayer(self.espnID, date, conn)
            conn.close()
            return self.pred_score[date]


class Pitcher(Player):

    def __init__(self, espnID, fd_salary=None):
        super().__init__(espnID, fd_salary)
        self.table_prefix = 'pitcher'

    def predict_score(self, date):
        if date in self.pred_score:
            return self.pred_score[date]
        else:
            conn = Connection()
            conn.connect()
            self.pred_score[date] = scorePlayer(self.espnID, date, conn, hitter=False)
            conn.close()
            return self.pred_score[date]