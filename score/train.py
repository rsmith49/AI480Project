from sklearn.neural_network import MLPRegressor
from sklearn.externals import joblib
from dateutil.parser import parse
from database.connect_local import Connection
from score.predict import getPlayerFeatures, datenum_to_str
from lineup.player import Hitter, Pitcher
from datetime import datetime, timedelta
import random

hitter_params = {
    'hidden_layer_sizes': (5, 5),
    'solver': 'lbfgs',
    'max_iter': 1000
}

pitcher_params = {
    'hidden_layer_sizes': (3, 3),
    'solver': 'lbfgs',
    'max_iter': 1000
}

PITCHER_FILE_PREFIX = 'Pitcher_NNR_Model_'
HITTER_FILE_PREFIX = 'Hitter_NNR_Model'
FILE_POSTFIX = '.pkl'

def saveModel(model, filepath):
    joblib.dump(model, filepath)


def getInputOutput(dates, players):
    conn = Connection()
    conn.connect()
    # To speed it up (not fully optimized, but oh well)
    for player in players:
        player.load_actual_scores(dates)

    train_x = []
    train_y = []
    for date in dates:
        for player in players:
            train_x.append(getPlayerFeatures(conn, player, date))
            if player.actual_score(date):
                train_y.append(player.actual_score(date))
            else:
                train_y.append(0)
    conn.close()

    return train_x, train_y

# must create separate model for pitcher and hitter
def trainPlayerModel(dates, players):

    model = MLPRegressor()
    if players[0].__class__ == Hitter:
        model.set_params(**hitter_params)
    else:
        model.set_params(**pitcher_params)

    train_x, train_y = getInputOutput(dates, players)
    model.fit(train_x, train_y)

    return model

def create_models(dates, should_test = False, test_perc = .1, save_model=False):
    conn = Connection()
    conn.connect()

    hitters = []
    pitchers = []

    for year in set([date.year for date in dates]):
        dates_this_year = [date for date in dates if date.year == year]

        datestr = '('
        for date in dates_this_year:
            datestr += "'" + datenum_to_str[date.month] + " " + str(date.day) + "',"
        datestr = datestr[:-1] + ')'

        # hitters
        sqlquery = 'SELECT distinct espnID FROM player_daily_' + str(year) \
                + ' WHERE `date` in ' + datestr
        hitterIDs = conn.query(sqlquery)
        hitterIDstr = '('
        for id in hitterIDs:
            hitterIDstr += str(id[0]) + ','
        hitterIDstr = hitterIDstr[:-1] + ')'

        # pitchers
        sqlquery = 'SELECT distinct espnID FROM pitcher_daily_' + str(year) \
                + ' WHERE `date` in ' + datestr
        pitcherIDs = conn.query(sqlquery)
        pitcherIDstr = '('
        for id in pitcherIDs:
            pitcherIDstr += str(id[0]) + ','
        pitcherIDstr = pitcherIDstr[:-1] + ')'

        sqlquery = 'SELECT playerName, espnID, position FROM active_players WHERE espnID in '
        hitterRes = conn.query(sqlquery + hitterIDstr)
        hitters.extend([Hitter(espnID, position, playerName) for (playerName, espnID, position) in hitterRes])
        pitcherRes = conn.query(sqlquery + pitcherIDstr)
        pitchers.extend([Pitcher(espnID, position, playerName) for (playerName, espnID, position) in pitcherRes])

    conn.close()
    hitters = list(set(hitters))
    pitchers = list(set(pitchers))

    if should_test:
        random.shuffle(hitters)
        random.shuffle(pitchers)
        test_hitters = hitters[:int(test_perc * len(hitters))]
        train_hitters = hitters[int(test_perc * len(hitters)):]
        test_pitchers = pitchers[:int(test_perc * len(pitchers))]
        train_pitchers = pitchers[int(test_perc * len(pitchers)):]

    else:
        train_hitters = hitters
        train_pitchers = pitchers

    print("Training Hitters")
    hitterModel = trainPlayerModel(dates, train_hitters)

    print("Training Pitchers")
    pitcherModel = trainPlayerModel(dates, train_pitchers)

    if should_test:
        test_hitter_data_in, test_hitter_data_out = getInputOutput(dates, test_hitters)
        test_pitcher_data_in, test_pitcher_data_out = getInputOutput(dates, test_pitchers)

        print("Hitter model R^2 on test data: " + str(hitterModel.score(test_hitter_data_in, test_hitter_data_out)))
        print("Pitcher model R^2 on test data: " + str(pitcherModel.score(test_pitcher_data_in, test_pitcher_data_out)))


    if save_model:
        curr_time = datetime.now()
        timestamp_str = str(curr_time.year) + '_' + str(curr_time.month) + '_' + str(curr_time.day) \
                + '__' + str(curr_time.hour) + '_' + str(curr_time.minute) + '_' + str(curr_time.second)
        filename_pitcher = PITCHER_FILE_PREFIX + timestamp_str + FILE_POSTFIX
        filename_hitter = HITTER_FILE_PREFIX + timestamp_str + FILE_POSTFIX

        saveModel(hitterModel, filename_hitter)
        saveModel(pitcherModel, filename_pitcher)

    return hitterModel, pitcherModel

if __name__ == '__main__':
    dates = []
    conn = Connection()
    conn.connect()
    sqlquery = 'SELECT DISTINCT `date` FROM player_daily_2014 WHERE datenum > 735700'
    datestrs = conn.query(sqlquery)
    conn.close()
    dates = [parse(datestr[0] + ' 2014') for datestr in datestrs]

    create_models(dates, should_test=True, save_model=False)