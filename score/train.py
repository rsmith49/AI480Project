from sklearn.neural_network import MLPRegressor
from sklearn.externals import joblib
from dateutil.parser import parse
from database.connect_local import Connection
from score.predict import getPlayerFeatures, datenum_to_str, load_all_feature_data
from score.predict import HITTER_COLS, PITCHER_COLS, GAME_COLS
from lineup.player import Hitter, Pitcher
from datetime import datetime, timedelta
import random, score.predict, numpy

default_hitter_params = {
    'hidden_layer_sizes': (32, 20),
    'solver': 'lbfgs',
    'max_iter': 1000
}

default_pitcher_params = {
    'hidden_layer_sizes': (22, 11),
    'solver': 'lbfgs',
    'max_iter': 1000
}

PITCHER_FILE_PREFIX = 'score/Pitcher_NNR_Model_'
HITTER_FILE_PREFIX = 'score/Hitter_NNR_Model'
FILE_POSTFIX = '.pkl'

INFO_FILE = 'model_info.txt'
DATES_QUERY_2014 = "SELECT DISTINCT `date` FROM player_daily_2014 WHERE datenum > 735700 " + \
               "AND datenum <= (SELECT max(datenum) FROM game_info_2014)"

def saveModel(model, filepath):
    joblib.dump(model, filepath)


def getInputOutput(dates, players, days_back_window = 0):
    conn = Connection()
    conn.connect()
    # To speed it up (not fully optimized, but oh well)
    dates_to_load = []
    for ndx in range(days_back_window, 0, -1):
        dates_to_load.append(dates[0] - timedelta(days=ndx))
    dates_to_load.extend(dates)
    for player in players:
        player.load_actual_scores(dates_to_load)

    train_x = []
    train_y = []
    for date in dates:
        # THIS IS GOING TO MAKE IT SO THAT IT IS ONLY GAMES THE PLAYERS PLAYED
        # Does not account for sit out bias -- when a player gets benched or hurt
        players_for_date = [player for player in players if player.actual_score(date) is not None]

        for player in players_for_date:
            train_x.append(getPlayerFeatures(conn, player, date))
            if player.actual_score(date):
                train_y.append(player.actual_score(date))
            else:
                train_y.append(0)
    conn.close()

    return train_x, train_y

# must create separate model for pitcher and hitter
def trainPlayerModel(dates, players, hitter_params, pitcher_params):

    model = MLPRegressor()
    if players[0].__class__ == Hitter:
        model.set_params(**hitter_params)
    else:
        model.set_params(**pitcher_params)

    train_x, train_y = getInputOutput(dates, players, days_back_window=7)

    model.fit(train_x, train_y)

    return model

#Default: no test, 10% test set, don't save model, don't exclude any fields from
#the ones in predict.py
def create_models(dates, hitter_params, pitcher_params, should_test = False, test_perc = .1, save_model=False, exclude_col_names=()):
    conn = Connection()
    conn.connect()

    final_hitter_columns = [col for col in HITTER_COLS if col not in exclude_col_names]
    final_pitcher_columns = [col for col in PITCHER_COLS if col not in exclude_col_names]
    final_game_columns = [col for col in GAME_COLS if col not in exclude_col_names]

    load_all_feature_data(dates, conn, final_hitter_columns, final_pitcher_columns, final_game_columns)

    hitters = []
    pitchers = []

    for year in set([date.year for date in dates]):
        dates_this_year = [date for date in dates if date.year == year]

        datestr = '('
        for date in dates_this_year:
            datestr += "'" + datenum_to_str[date.month] + " " + str(date.day) + "',"
        datestr = datestr[:-1] + ')'

        # Get the IDs of all active hitters
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
    hitterModel = trainPlayerModel(dates, train_hitters, hitter_params, pitcher_params)

    print("Training Pitchers")
    pitcherModel = trainPlayerModel(dates, train_pitchers, hitter_params, pitcher_params)

    if should_test:
        test_hitter_data_in, test_hitter_data_out = getInputOutput(dates, test_hitters, days_back_window=7)
        test_pitcher_data_in, test_pitcher_data_out = getInputOutput(dates, test_pitchers, days_back_window=7)

        hitter_score = hitterModel.score(test_hitter_data_in, test_hitter_data_out)
        pitcher_score = pitcherModel.score(test_pitcher_data_in, test_pitcher_data_out)

        print("Hitter model R^2 on test data: " + str(hitter_score))
        print("Pitcher model R^2 on test data: " + str(pitcher_score))


    if save_model:
        curr_time = datetime.now()
        timestamp_str = str(curr_time.year) + '_' + str(curr_time.month) + '_' + str(curr_time.day) \
                + '__' + str(curr_time.hour) + '_' + str(curr_time.minute) + '_' + str(curr_time.second)
        filename_pitcher = PITCHER_FILE_PREFIX + timestamp_str + FILE_POSTFIX
        filename_hitter = HITTER_FILE_PREFIX + timestamp_str + FILE_POSTFIX

        saveModel(hitterModel, filename_hitter)
        saveModel(pitcherModel, filename_pitcher)

        if should_test:
            # Need to add code to save metrics (R^2) about the filename, so we
            # know which model is which
            info_file = open(INFO_FILE, 'a')
            info_file.write(filename_hitter + ' R^2: ' + str(hitter_score) + '\n')
            info_file.write(filename_pitcher + ' R^2: ' + str(pitcher_score) + '\n')
            info_file.close()

    return hitterModel, pitcherModel

def train_new_models(hitter_params, pitcher_params, *exclude_col_names):
    print("Creating new models")
    print("Hitter params: " + str(hitter_params))
    print("Pitcher params: " + str(pitcher_params))

    dates = []
    conn = Connection()
    conn.connect()

    datestrs = conn.query(DATES_QUERY_2014)
    conn.close()
    dates = [parse(datestr[0] + ' 2014') for datestr in datestrs]
    create_models(dates, hitter_params, pitcher_params, should_test=True, save_model=True, exclude_col_names=exclude_col_names)



if __name__ == '__main__':
    train_new_models(default_hitter_params, default_pitcher_params)

