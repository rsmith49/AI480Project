from sklearn.neural_network import MLPRegressor
from sklearn.externals import joblib
from dateutil.parser import parse
from database.connect_local import Connection
from score.predict import getPlayerFeatures, datenum_to_str
from lineup.player import Hitter, Pitcher
from datetime import datetime, timedelta

PITCHER_FILE_PREFIX = 'Pitcher_NNR_Model_'
HITTER_FILE_PREFIX = 'Hitter_NNR_Model'
FILE_POSTFIX = '.pkl'

def saveModel(model, filepath):
    joblib.dump(model, filepath)


# must create separate model for pitcher and hitter
def trainPlayerModel(dates, players):
    conn = Connection()
    conn.connect()
    model = MLPRegressor(activation='logistic')

    # To speed it up (not fully optimized, but oh well)
    for player in players:
        player.load_actual_scores(dates)

    train_x = []
    train_y = []
    for date in dates:
        for player in players:
            train_x.append(getPlayerFeatures(conn, player, date))
            train_y.append(player.actual_score(date))
    conn.close()
    model.fit(train_x, train_y)

    return model

def create_models(dates, save_model=False):
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

    print("Training Hitters")
    hitterModel = trainPlayerModel(dates, hitters)
    print("Training Pitchers")
    pitcherModel = trainPlayerModel(dates, pitchers)

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
    sqlquery = 'SELECT DISTINCT `date` FROM player_daily_2014 LIMIT 30'
    datestrs = conn.query(sqlquery)
    dates = [parse(datestr[0] + ' 2014') for datestr in datestrs]

    create_models(dates, save_model=True)