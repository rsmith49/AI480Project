import sklearn
from sklearn.neural_network import MLPRegressor
from sklearn.externals import joblib
from database.connect_local import Connection
from lineup.player import Hitter, Pitcher, Player
from datetime import datetime, timedelta
import dateutil.parser

BEST_HITTER_MODEL_FILEPATH = ''
BEST_PITCHER_MODEL_FILEPATH = ''

HITTER_GAMES_BACK = 7
PITCHER_GAMES_BACK = 3

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

def load_model(filepath):
    return joblib.load(filepath)

if __name__ == '__main__':
    hitter_model = load_model(BEST_HITTER_MODEL_FILEPATH)
    pitcher_model = load_model(BEST_PITCHER_MODEL_FILEPATH)

def find_previous_n_game_scores(conn, player, date, n, scores_loaded=True):
    if scores_loaded:
        prev_dates = [prev_date for prev_date in player.real_score.keys() if
                      prev_date < date and prev_date.year == date.year]
        prev_dates = sorted(prev_dates)
        prev_dates = prev_dates[::-1]
        if len(prev_dates) < n:
            scores = [player.actual_score(prev_date) for prev_date in prev_dates]
        else:
            scores = [player.actual_score(prev_date) for prev_date in prev_dates[:n]]
    else:
        table = player.table_prefix + '_daily_' + str(date.year)
        sqlquery = 'SELECT datenum FROM ' + table + \
                " WHERE `date` = '" + datenum_to_str[date.month] + ' ' + str(date.day) + "'"
        datenum = conn.query(sqlquery)[0][0]
        sqlquery = 'SELECT fd_points FROM ' + table + ' WHERE datenum < ' + str(datenum) + \
                ' AND espnID = ' + str(player.espnID) + ' ORDER BY datenum DESC LIMIT ' + str(n)
        results = conn.query(sqlquery)
        scores = [score[0] for score in results]
    if len(scores) < n:
        for ndx in range(n - len(scores)):
            scores.append(0)
    for ndx in range(len(scores)):
        if scores[ndx] is None:
            scores[ndx] = 0
    return scores

# conn should already have connected
# THIS IS THE MOST IMPORTANT METHOD
def getHitterFeatures(conn, player, date):
    features = []
    features = find_previous_n_game_scores(conn, player, date, HITTER_GAMES_BACK)

    return features

# THIS IS THE MOST IMPORTANT METHOD
def getPitcherFeatures(conn, player, date):
    features = []
    features = find_previous_n_game_scores(conn, player, date, PITCHER_GAMES_BACK)

    return features

def getPlayerFeatures(conn, player, date):
    if player.__class__ == Hitter:
        return getHitterFeatures(conn, player, date)
    else:
        return getPitcherFeatures(conn, player, date)

def scorePlayer(player, date, conn):
    features = getPlayerFeatures(conn, player, date)
    if player.__class__ == Hitter:
        return hitter_model.predict([features])[0]
    else:
        return pitcher_model.predict([features])[0]


def scorePlayerFake(player, date, conn):
    sqlquery = "SELECT fd_points FROM " + player.table_prefix + "_daily_" + str(date.year) + " WHERE espnID = "\
               + str(player.espnID) + " AND `date` = '" + datenum_to_str[date.month] + " " + str(date.day) + "'"
    score = conn.query(sqlquery)
    if score:
        return score[0][0]
    else:
        print(sqlquery)
        return 0


if __name__ == '__main__':
    pass