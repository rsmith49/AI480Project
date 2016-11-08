from lineup.player import Hitter, Pitcher
from database.connect_local import Connection
from datetime import datetime, timedelta
import dateutil.parser

SAL_MIN = 0
SAL_CAP = 350
SAL_INC = 1

hitter_list = []
pitcher_list = []

def score_lineup(players, date):
    total_score = 0
    for player in players:
        total_score += player.predict_score(date)
    return total_score

def get_potential_players(player_list, date):
    potential_players = []
    for player in player_list:
        if player.get_salary(date):
            potential_players.append(player)
    return potential_players

def create_player_lists():
    conn = Connection()
    conn.connect()
    players = conn.query("SELECT playerName, espnID, position FROM active_players")
    for playerName, espnID, pos in players:
        if not pos in ['RP', 'SP']:
            hitter_list.append(Hitter(espnID))
        else:
            pitcher_list.append(Pitcher(espnID))
    conn.close()

def generate_lineup(date):
    potential_hitters = get_potential_players(hitter_list, date)
    potential_pitchers = get_potential_players(pitcher_list, date)

    test_potential = list(potential_hitters)
    test_potential.extend(list(potential_pitchers))

    print(len(potential_hitters))
    print(len(potential_pitchers))

    score_table = [[0 for x in range(SAL_MIN, SAL_CAP, SAL_INC)] for y in range(len(test_potential))]

    for player_num in range(1,len(test_potential)):
        for salary_cap in range(SAL_MIN, SAL_CAP, SAL_INC):
            if test_potential[player_num].get_salary(date)/100 > salary_cap:
                score_table[player_num][salary_cap] = score_table[player_num - 1][salary_cap]
            else:
                score_table[player_num][salary_cap] = max(
                    score_table[player_num - 1][salary_cap],
                    score_table[player_num - 1][salary_cap - int(test_potential[player_num].get_salary(date)/100)]
                                + test_potential[player_num].predict_score(date)
                )
    print(score_table)

create_player_lists()
generate_lineup(dateutil.parser.parse('Apr 6 2015'))