from lineup.player import Hitter, Pitcher
from database.connect_local import Connection
from datetime import datetime, timedelta
import dateutil.parser

COMBINED_POSITIONS = 7,8,9
FIRST_POS = 1

SAL_MIN = 0
SAL_CAP = 350
SAL_INC = 1
SAL_TO_WEIGHT_RATIO = 100

hitter_list = []
pitcher_list = []

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

def getBestInGroup(group, players, w, groups, matrix, N, date, solution):
    max = 0
    best_weight = SAL_CAP * SAL_TO_WEIGHT_RATIO
    maxndx = -1
    for ndx in range(0, N):
        if groups[ndx] == group and solution[w][ndx]:
            if matrix[w][ndx] > max or (matrix[w][ndx] == max
                                        and players[ndx].get_salary(date) < best_weight):
                max = matrix[w][ndx]
                maxndx = ndx
                best_weight = players[ndx].get_salary(date)
    return players[maxndx]

def isBestInGroup(player, players, w, groups, matrix, N, pos_inc):
    if pos_inc == 0:
        return False
    for pos in range(1, pos_inc + 1):
        group = player.pos_num - pos
        max = 0
        maxndx = -1
        for ndx in range(0, N):
            if groups[ndx] == group:
                if matrix[w][ndx] > max:
                    max = matrix[w][ndx]
                    maxndx = ndx
        if max == 0:
            return False
        if players[maxndx] == player:
            return True
    return False

def isMaxInGroup(n, w, groups, matrix, N):
    group = groups[n]
    max = 0
    for ndx in range(0, N):
        if groups[ndx] == group:
            if matrix[w][ndx] > max:
                max = matrix[w][ndx]
    return matrix[w][n] == max

def generate_best_lineup(date):

    potential_players = get_potential_players(hitter_list, date)
    potential_players.extend(get_potential_players(pitcher_list, date))
    potential_players = sorted(potential_players, key = lambda player: player.pos_num)

    N = len(potential_players)

    groups = [player.pos_num for player in potential_players]

    score_table = [[0  for y in range(N)] for x in range(SAL_MIN, SAL_CAP, SAL_INC)]
    solution = [[0 for y in range(N)] for x in range(SAL_MIN, SAL_CAP, SAL_INC)]

    for w in range(SAL_MIN, SAL_CAP, SAL_INC):
        for n in range(0, N):
            player = potential_players[n]

            if player.pos_num == FIRST_POS:
                if player.get_salary(date) / SAL_TO_WEIGHT_RATIO <= w:
                    score_table[w][n] = player.predict_score(date)
                    solution[w][n] = True
            else:
                if player.pos_num != potential_players[n - 1].pos_num:
                    opt1 = getMax(potential_players[n - 1].pos_num, score_table[w], groups, n)
                    opt2 = -1
                    if player.get_salary(date) / SAL_TO_WEIGHT_RATIO < w:
                        opt2 = player.predict_score(date) + getMax(
                            potential_players[n - 1].pos_num, score_table[w - int(player.get_salary(date) / SAL_TO_WEIGHT_RATIO)], groups, n)
                    score_table[w][n] = max(opt1, opt2)
                    solution[w][n] = opt2 > opt1
                else:
                    opt1 = getMax(player.pos_num - 1, score_table[w], groups, n)
                    opt2 = -1
                    if player.get_salary(date) / SAL_TO_WEIGHT_RATIO < w:
                        opt2 = player.predict_score(date) + getMax(
                            player.pos_num - 1, score_table[w - int(player.get_salary(date) / SAL_TO_WEIGHT_RATIO)], groups, n)
                    score_table[w][n] = max(opt1, opt2)
                    solution[w][n] = opt2 > opt1

    to_take = []
    curr_group = potential_players[-1].pos_num + 1
    w = SAL_CAP - 1
    for n in range(N - 1, -1, -1):
        player = potential_players[n]
        if solution[w][n] and isMaxInGroup(n, w, groups, score_table, N) and player.pos_num < curr_group:
            to_take.append(player)
            w -= int(player.get_salary(date) / SAL_TO_WEIGHT_RATIO)
            curr_group = player.pos_num

    #for player in to_take:
    #    print(str(player), str(player.pos_num), str(player.predict_score(date)), str(player.get_salary(date)), sep=', ')
    #print()

    return to_take

def generate_best_lineup_2(date):

    potential_players = get_potential_players(hitter_list, date)
    potential_players.extend(get_potential_players(pitcher_list, date))

    combined_position_players = []
    ndx = 0
    while ndx < len(potential_players):
        player = potential_players[ndx]
        if player.pos_num in COMBINED_POSITIONS:
            combined_position_players.append(player)
            del potential_players[ndx]
            ndx -= 1
        ndx += 1
    for player in combined_position_players:
        for pos_num in COMBINED_POSITIONS:
            new_player = player.__copy__()
            new_player.pos_num = pos_num
            potential_players.append(new_player)

    potential_players = sorted(potential_players, key=lambda player: player.pos_num)

    N = len(potential_players)

    groups = [player.pos_num for player in potential_players]

    score_table = [[0 for y in range(N)] for x in range(SAL_MIN, SAL_CAP, SAL_INC)]
    solution = [[0 for y in range(N)] for x in range(SAL_MIN, SAL_CAP, SAL_INC)]

    for w in range(SAL_MIN, SAL_CAP, SAL_INC):
        for n in range(0, N):
            player = potential_players[n]

            if player.pos_num == FIRST_POS:
                if player.get_salary(date) / SAL_TO_WEIGHT_RATIO <= w:
                    score_table[w][n] = player.predict_score(date)
                    solution[w][n] = True
            elif player.pos_num in COMBINED_POSITIONS  and w > player.get_salary(date) / SAL_TO_WEIGHT_RATIO\
                    and isBestInGroup(player, potential_players,
                                      w - int(player.get_salary(date) / SAL_TO_WEIGHT_RATIO), groups,
                                      score_table, N, player.pos_num - COMBINED_POSITIONS[0]):
                #print(player)
                score_table[w][n] = getMax(potential_players[n - 1].pos_num, score_table[w], groups, n)
                solution[w][n] = False

            else:
                if player.pos_num != potential_players[n - 1].pos_num:
                    opt1 = getMax(potential_players[n - 1].pos_num, score_table[w], groups, n)
                    opt2 = -1
                    if player.get_salary(date) / SAL_TO_WEIGHT_RATIO < w:
                        opt2 = player.predict_score(date) + getMax(
                            potential_players[n - 1].pos_num,
                            score_table[w - int(player.get_salary(date) / SAL_TO_WEIGHT_RATIO)], groups, n)
                    score_table[w][n] = max(opt1, opt2)
                    solution[w][n] = opt2 > opt1
                else:
                    opt1 = getMax(player.pos_num - 1, score_table[w], groups, n)
                    opt2 = -1
                    if player.get_salary(date) / SAL_TO_WEIGHT_RATIO < w:
                        opt2 = player.predict_score(date) + getMax(
                            player.pos_num - 1, score_table[w - int(player.get_salary(date) / SAL_TO_WEIGHT_RATIO)], groups,
                            n)
                    score_table[w][n] = max(opt1, opt2)
                    solution[w][n] = opt2 > opt1

    to_take = []
    curr_group = potential_players[-1].pos_num + 1
    w = SAL_CAP - 1
    all_groups = sorted(list(set([player.pos_num for player in potential_players])), key=lambda pos: -pos)

    for group in all_groups:
        player = getBestInGroup(group, potential_players, w, groups, score_table, N, date, solution)
        w -= int(player.get_salary(date) / SAL_TO_WEIGHT_RATIO)
        to_take.append(player)



    """for n in range(N - 1, -1, -1):
        player = potential_players[n]
        if solution[w][n] and isMaxInGroup(n, w, groups, score_table, N) \
                and player.pos_num < curr_group:
            to_take.append(player)
            w -= int(player.get_salary(date) / SAL_TO_WEIGHT_RATIO)
            curr_group = player.pos_num"""

    # for player in to_take:
    #    print(str(player), str(player.pos_num), str(player.predict_score(date)), str(player.get_salary(date)), sep=', ')
    # print()



    return to_take

def getLineupsForDates(dates):
    create_player_lists()
    for hitter in hitter_list:
        hitter.load_salaries(dates)
    for pitcher in pitcher_list:
        pitcher.load_salaries(dates)

    def score_lineup(lineup, date):
        score = 0
        weight = 0
        for player in lineup:
            score += player.predict_score(date)
            weight += player.get_salary(date)
        if weight / SAL_TO_WEIGHT_RATIO > SAL_CAP:
            print("UH OH, lineup is too big")
        return score

    lineups = []
    for date in dates:
        print("Date: " + str(date))
        lineup1 = generate_best_lineup(date)
        print("lineup 1 score: " + str(score_lineup(lineup1, date)))
        lineup2 = generate_best_lineup_2(date)
        print("lineup 2 score: " + str(score_lineup(lineup2, date)))
        print()

        lineups.append((date, generate_best_lineup_2(date)))

    return lineups

dates = []
for day_num in range(6, 20):
    dates.append(dateutil.parser.parse('Apr ' + str(day_num) + ' 2015'))

#dates = [dateutil.parser.parse('Apr 6 2015'), dateutil.parser.parse('Apr 6 2016')]
best_lineups = getLineupsForDates(dates)

# DATE TO USE: 4/19/15

for date, lineup in best_lineups:
    print("Date: " + str(date))
    for player in lineup:
        print(str(player), end=', ')
    print()