import sklearn
from database.connect_local import Connection
from datetime import datetime, timedelta
import dateutil.parser

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

# conn should already have connected
def getBatterFeatures(conn, date):
    features = {}

def scorePlayer(player, date, conn, hitter=True):
    sqlquery = "SELECT fd_points FROM " + player.table_prefix + "_daily_" + str(date.year) + " WHERE espnID = "\
               + str(player.espnID) + " AND `date` = '" + datenum_to_str[date.month] + " " + str(date.day) + "'"
    score = conn.query(sqlquery)
    if score:
        return score[0][0]
    else:
        print(sqlquery)
        return 0