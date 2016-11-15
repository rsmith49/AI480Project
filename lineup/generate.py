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

def lineup_cost(players, date):
    total_cost = 0
    for player in players:
        total_cost += player.get_salary(date)
    return total_cost

def get_potential_players(player_list, date):
    potential_players = []
    for player in player_list:
        if player.get_salary(date):
            potential_players.append(player)
    return potential_players

def create_player_lists():
    conn = Connection()
    conn.connect()
    players = conn.query("SELECT playerName, espnID, position FROM active_players LIMIT 20")
    for playerName, espnID, pos in players:
        if not pos in ['RP', 'SP']:
            hitter_list.append(Hitter(espnID, playerName))
        else:
            pitcher_list.append(Pitcher(espnID, playerName))
    conn.close()

def generate_lineup(date):
    potential_hitters = get_potential_players(hitter_list, date)
    potential_pitchers = get_potential_players(pitcher_list, date)

    test_potential = list(potential_hitters)
    test_potential.extend(list(potential_pitchers))

    print(len(potential_hitters))
    print(len(potential_pitchers))

    score_table = [[0 for x in range(SAL_MIN, SAL_CAP, SAL_INC)] for y in range(len(test_potential))]
    best_lineup = []
    selected = set()
    not_selected = set()
    not_selected.add(test_potential[0])

    for player_num in range(1,len(test_potential)):
        not_selected.add(test_potential[player_num])
        for salary_cap in range(SAL_MIN, SAL_CAP, SAL_INC):
            if test_potential[player_num].get_salary(date)/100 > salary_cap:
                score_table[player_num][salary_cap] = score_table[player_num - 1][salary_cap]
            else:
                score1 = score_table[player_num - 1][salary_cap]
                score2 = score_table[player_num - 1][salary_cap - int(test_potential[player_num].get_salary(date)/100)]\
                                + test_potential[player_num].predict_score(date)
                if score1 >= score2:
                    score_table[player_num][salary_cap] = score1
                else:
                    score_table[player_num][salary_cap] = score2
                    if lineup_cost(best_lineup, date)/100 + test_potential[player_num].get_salary(date)/100 > salary_cap:
                        best_lineup.sort(key=lambda player: player.predict_score(date))
                        best_lineup.pop()
                        best_lineup.append(test_potential[player_num])
                    else:
                        best_lineup.append(test_potential[player_num])

    ndx = 0
    for player in best_lineup:
        print(player.name, end=' ')
        print(score_table[ndx][-1])
        ndx += 1
    print(score_lineup(best_lineup, date))
    print(score_table[-1][-1])


create_player_lists()
generate_lineup(dateutil.parser.parse('Apr 6 2015'))