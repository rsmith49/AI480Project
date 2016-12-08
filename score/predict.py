import sklearn
from sklearn.neural_network import MLPRegressor
from sklearn.externals import joblib
from database.connect_local import Connection
from lineup.player import Hitter, Pitcher, Player
from datetime import datetime, timedelta
import dateutil.parser

# for some reason the datenum's in the database are off by a ton
DATE_OFFSET = 719529
epoch = datetime.utcfromtimestamp(0)

def datenumOf(datetime):
    return (datetime - epoch).total_seconds() / (24 * 60 * 60) + DATE_OFFSET

def tableName(player, date):
    return player.table_prefix + '_daily_' + str(date.year)

BEST_HITTER_MODEL_FILEPATH = 'Hitter_NNR_Model2016_11_26__9_37_51.pkl'
BEST_PITCHER_MODEL_FILEPATH = 'Pitcher_NNR_Model_2016_11_26__9_37_51.pkl'

HITTER_COLS = ['p.r', 'p.h', 'p.hr', 'p.k', 'p.fd_points']
PITCHER_COLS = ['p.pitches', 'p.er', 'p.hr', 'p.k', 'p.bb', 'p.fd_points']
GAME_COLS = ['g.temp', 'g.windSpeed', 'g.visibility', 'g.pressure']

HITTER_GAMES_BACK = 7
PITCHER_GAMES_BACK = 4

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

feature_data = {}

def load_all_feature_data(dates, conn, hitter_cols=HITTER_COLS, pitcher_cols=PITCHER_COLS, game_cols=GAME_COLS):
    for year in set([date.year for date in dates]):
        sqlquery = 'SELECT p.espnID, p.`date`'
        for col in hitter_cols:
            sqlquery += ', ' + col
        for col in game_cols:
            sqlquery += ', ' + col
        sqlquery += ' FROM game_info_' + str(year) + ' as g, player_daily_' + str(year) + ' as p ' + \
                    'WHERE (g.home = p.opp OR g.vis = p.opp) AND g.datenum = p.datenum ORDER BY p.datenum'
        query_player_output = conn.query(sqlquery)

        for line in query_player_output:
            feature_dict = {}
            for ndx in range(len(hitter_cols) + len(game_cols)):
                if ndx < len(hitter_cols):
                    feature_dict[hitter_cols[ndx]] = line[ndx + 2]
                else:
                    feature_dict[game_cols[ndx - len(hitter_cols)]] = line[ndx + 2]
            feature_data[(line[0], dateutil.parser.parse(line[1] + ' ' + str(year)))] = feature_dict

        sqlquery = 'SELECT p.espnID, p.`date`'
        for col in pitcher_cols:
            sqlquery += ', ' + col
        for col in game_cols:
            sqlquery += ', ' + col
        sqlquery += ' FROM game_info_' + str(year) + ' as g, pitcher_daily_' + str(year) + ' as p ' + \
                    'WHERE (g.home = p.opp OR g.vis = p.opp) AND g.datenum = p.datenum ORDER BY p.datenum'
        query_player_output = conn.query(sqlquery)

        for line in query_player_output:
            feature_dict = {}
            for ndx in range(len(pitcher_cols) + len(game_cols)):
                if ndx < len(pitcher_cols):
                    feature_dict[pitcher_cols[ndx]] = line[ndx + 2]
                else:
                    feature_dict[game_cols[ndx - len(pitcher_cols)]] = line[ndx + 2]
            feature_data[(line[0], dateutil.parser.parse(line[1] + ' ' + str(year)))] = feature_dict



def load_model(filepath):
    return joblib.load(filepath)

hitter_model = load_model(BEST_HITTER_MODEL_FILEPATH)
pitcher_model = load_model(BEST_PITCHER_MODEL_FILEPATH)

def find_previous_n_game_features(conn, player, date, n, scores_loaded=True):
    features = []

    if scores_loaded:
        if player.__class__ == Hitter:
            player_col_length = len(HITTER_COLS)
        else:
            player_col_length = len(PITCHER_COLS)

        prev_dates = [prev_date for espnID,prev_date in feature_data.keys() if
                      prev_date < date and prev_date.year == date.year and espnID == player.espnID]
        prev_dates = sorted(prev_dates)
        prev_dates = prev_dates[::-1]

        for ndx in range(n):
            if ndx >= len(prev_dates):
                for ndx0s in range(player_col_length):
                    features.append(0)
            else:
                prev_date = prev_dates[ndx]
                features.extend([feature_data[(player.espnID, prev_date)][key]
                            for key in sorted(feature_data[(player.espnID, prev_date)].keys()) if key not in GAME_COLS])
    else:
        ## Outdated for now
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

    if (player.espnID, date) not in feature_data:
        print()

    features.extend([feature_data[(player.espnID, date)][key]
                            for key in sorted(feature_data[(player.espnID, date)].keys())
                     if key in GAME_COLS])

    return features

def findAvgScoreForYear(conn, player, end_date, scores_loaded=True):
    if scores_loaded:
        avg = 0
        n = 0
        prev_dates = [date for date in player.dates_scored() if date < end_date and date.year == end_date.year]
        for date in prev_dates:
            if player.actual_score(end_date):
                avg += player.actual_score(end_date)
            n += 1
        if n > 0:
            avg /= n
        else:
            avg = 0
    else:
        avg = conn.query('SELECT avg(fd_points) FROM ' + tableName(player, end_date) +
                         ' WHERE espnID = ' + str(player.espnID) + ' AND datenum < ' +
                         str(datenumOf(end_date)))
        if avg:
            avg = avg[0][0]
        else:
            avg = 0
    return avg

# conn should already have connected
# THIS IS THE MOST IMPORTANT METHOD
def getHitterFeatures(conn, player, date):
    features = []
    features.extend(find_previous_n_game_features(conn, player, date, HITTER_GAMES_BACK))
    #features.append(findAvgScoreForYear(conn, player, date))

    return features

# THIS IS THE MOST IMPORTANT METHOD
def getPitcherFeatures(conn, player, date):
    features = []
    features.extend(find_previous_n_game_features(conn, player, date, PITCHER_GAMES_BACK))
    #features.append(findAvgScoreForYear(conn, player, date))

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
