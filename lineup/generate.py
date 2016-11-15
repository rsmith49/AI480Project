from lineup.player import Hitter, Pitcher
from database.connect_local import Connection
from datetime import datetime, timedelta
import dateutil.parser

SAL_MIN = 0
SAL_CAP = 350
SAL_INC = 1
FIRST_POS = 1

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
    players = conn.query("SELECT playerName, espnID, position FROM active_players")
    for playerName, espnID, pos in players:
        if not pos in ['RP', 'SP']:
            hitter_list.append(Hitter(espnID, pos, playerName))
        else:
            pitcher_list.append(Pitcher(espnID, pos, playerName))
    conn.close()

def getMax(group, row, groups, n):
    max = 0
    for ndx in range(0,n):
        if groups[ndx] == group:
            if row[ndx] > max:
                max = row[ndx]
    return max

def isMaxInGroup(n, w, groups, matrix, N):
    group = groups[n]
    max = 0
    for ndx in range(0, N):
        if groups[ndx] == group:
            if matrix[w][ndx] > max:
                max = matrix[w][ndx]
    return matrix[w][n] == max

def generate_lineup(date):

    potential_players = get_potential_players(hitter_list, date)
    potential_players.extend(get_potential_players(pitcher_list, date))
    potential_players = sorted(potential_players, key = lambda player: player.pos)

    N = len(potential_players)

    groups = [player.pos for player in potential_players]

    score_table = [[0  for y in range(N)] for x in range(SAL_MIN, SAL_CAP, SAL_INC)]
    solution = [[0 for y in range(N)] for x in range(SAL_MIN, SAL_CAP, SAL_INC)]

    for w in range(SAL_MIN, SAL_CAP, SAL_INC):
        for n in range(0, N):
            player = potential_players[n]

            if player.pos == FIRST_POS:
                if player.get_salary(date) / 100 <= w:
                    score_table[w][n] = player.predict_score(date)
                    solution[w][n] = True
            else:
                if player.pos != potential_players[n - 1].pos:
                    opt1 = getMax(potential_players[n - 1].pos, score_table[w], groups, n)
                    opt2 = -1
                    if player.get_salary(date) / 100 < w:
                        opt2 = player.predict_score(date) + getMax(
                            potential_players[n - 1].pos, score_table[w - int(player.get_salary(date) / 100)], groups, n)
                    score_table[w][n] = max(opt1, opt2)
                    solution[w][n] = opt2 > opt1
                else:
                    opt1 = getMax(player.pos - 1, score_table[w], groups, n)
                    opt2 = -1
                    if player.get_salary(date) / 100 < w:
                        opt2 = player.predict_score(date) + getMax(
                            player.pos - 1, score_table[w - int(player.get_salary(date) / 100)], groups, n)
                    score_table[w][n] = max(opt1, opt2)
                    solution[w][n] = opt2 > opt1

    to_take = []
    curr_group = potential_players[-1].pos + 1
    w = SAL_CAP - 1
    for n in range(N - 1, -1, -1):
        player = potential_players[n]
        if solution[w][n] and isMaxInGroup(n, w, groups, score_table, N) and player.pos < curr_group:
            to_take.append(player)
            w -= int(player.get_salary(date) / 100)
            curr_group = player.pos

    for player in to_take:
        print(str(player), str(player.pos), str(player.predict_score(date)), str(player.get_salary(date)), sep=', ')
    print()

    return to_take





create_player_lists()
generate_lineup(dateutil.parser.parse('Apr 6 2015'))
generate_lineup(dateutil.parser.parse('Apr 6 2016'))