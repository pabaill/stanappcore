import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from urllib.request import urlopen
from bs4 import BeautifulSoup
import numpy as np
from scipy import stats
from fractions import Fraction
import time

TEAMS = ["ATL", "BOS", "BRK", "CHI", "CHO", "CLE", "DAL", "DEN", "DET", "GSW", "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN", "NOP", "NYK", "OKC", "ORL", "PHI", "PHO", "POR", "SAC", "SAS", "TOR", "UTA", "WAS"]

"""
This is my Python based scraping and modeling tool that converts NBA players
into a series of Gaussian/Beta pairs in order to model their scoring tendencies.
It reads a table from Basketball Reference by using a player's player code, converts
the desired stat into a usable distribution, and stores the information in dictionary
format in a text file that is readable by the app_core.
"""

"""
Returns a list of table data for each game for a given player
@param url The url for a given player's Basketball Reference page for the current year
"""
def get_game_log_table(url):
    html = urlopen(url)
    soup = BeautifulSoup(html, features="lxml")

    if len(soup.findAll('tr', limit=2)) < 2:
        # This player has not played enough to have usable data
        return 'NO DATA FOUND'

    # Get the rows from the table, but only those representing actual games
    rows = soup.findAll('tr')
    rows_data = [[td.getText() for td in rows[i].findAll('td')]
                    for i in range(len(rows))]
    # Advance past empty games
    rows_data = rows_data[rows_data.index([]) + 1:rows_data.index([]) + 1 + 82 + 4]
    return rows_data


"""
Returns a normal distribution representing field goal attempts, assists, etc.
For percentages, a beta distribution is returned to model the consistency of the player.
Distributions are returns as scipy objects (stats.norm, etc)
@param stat The desired statistic to fetch (ppg, apg, etc)
@param rows_data the raw url data fetched from get_game_log_table
"""
def get_stat_dist(stat, rows_data):
    # percentage indexes map to made shots
    stat_to_index = {"points": -3, "2pfga": 10, "2pfgp": 9, "3pfga": 13, "3pfgp": 12, "fta": 16, "ftp": 15, "mins": 8, "ast": -8, "reb": -9, "blk": -6, "stl": -7}
    if stat not in stat_to_index:
        return
    ind = stat_to_index[stat]
    point_dict = {}
    point_set = []
    if stat == '2pfga':
        # Interpolated category that is not explicitly available; need to construct just 2pt data
        total = 10
        three = 13
        for row in rows_data:
            if len(row) > 0 and len(row[-1]) <= 3 and ind < len(row) and row[ind] != '':
                val = float(row[total]) - float(row[three])
                if val in point_dict.keys():
                    point_dict[val] = point_dict[val] + 1
                else:
                    point_dict[val] = 1
                point_set.append(val)
    elif stat == '2pfgp' or stat == '3pfgp' or stat == 'ftp':
        # Beta distributed random variables
        made = 0
        total = 0
        total_ind = stat_to_index[stat[:-1] + 'a']
        for row in rows_data:
            if len(row) > 0 and len(row[-1]) <= 3 and row[ind] != '' and row[total_ind] != '':
                # Read stat as normal or interpolate two pointers
                made += int(row[ind]) if stat != '2pfgp' else int(row[ind]) - int(row[stat_to_index['3pfgp']])
                total += int(row[total_ind]) if stat != '2pfgp' else int(row[total_ind]) - int(row[stat_to_index['3pfga']])
        if total == 0:
            # Defaults to league average with low consistency if no info available
            if stat == 'ftp': return stats.beta(4, 2)
            elif stat == '2pfgp': return stats.beta(4, 5)
            else: return stats.beta(3, 6)
        frac = Fraction(made, total).limit_denominator(30)
        alpha = 1 + frac.numerator
        beta = 1 + (frac.denominator - frac.numerator)
        return stats.beta(alpha, beta)
    else:
        # Explicit stats; these can be read from the table into a normal distribution
        for row in rows_data:
            if len(row) > 0 and len(row[-1]) <= 3 and row[ind] != '':
                val = 0
                if stat == 'mins':
                    val = float(row[ind][:row[ind].index(':')])
                else:
                    val = float(row[ind])
                if val in point_dict.keys():
                    point_dict[val] = point_dict[val] + 1
                else:
                    point_dict[val] = 1
                point_set.append(val)
        point_set = np.array(point_set)
        if np.mean(point_set) == 0:
            return stats.norm(0, 1)
    return stats.norm(np.mean(point_set), np.std(point_set))

"""
A sanity check function that projects a player's performance over a season (82 games)

Each parameter is a scipy distribution object from get_stat_dist for the associated statistic
"""
def generate_ppg_season(two_fga_dist, three_pfga_dist, fta_dist, two_fgp_rv, three_fgp_rv, ftp_rv):
    x = [round(abs(x)) for x in two_fga_dist.rvs(82)]
    y = [round(abs(y)) for y in three_pfga_dist.rvs(82)]
    z = [round(abs(z)) for z in fta_dist.rvs(82)]
    x_dict = {}
    avg = 0
    for i in range(len(x)):
        x[i] = (int(z[i] * ftp_rv.rvs())) + (int(x[i] * two_fgp_rv.rvs()) * 2) + (int(y[i] * three_fgp_rv.rvs()) * 3)
        avg += x[i]
        if x[i] not in x_dict:
            x_dict[x[i]] = 1
        else:
            x_dict[x[i]] = x_dict[x[i]] + 1
    print(sum(x) / len(x))

"""
Returns a dictionary of the distribution of all of a given player's shooting stats (points).

@param src The row data from the Basketball Reference page, as processed by get_game_log_table
"""
def get_player_data(src):
    two_fga_dist = get_stat_dist("2pfga", src)
    three_pfga_dist = get_stat_dist("3pfga", src)
    fta_dist = get_stat_dist("fta", src)
    # random variable representing 2pt fgp
    two_fgp_rv = get_stat_dist("2pfgp", src)
    # random variable representing 3pt fgp
    three_fgp_rv = get_stat_dist("3pfgp", src)
    #free throws
    ftp_rv = get_stat_dist("ftp", src)
    return {"2fga": two_fga_dist, "3fga": three_pfga_dist, "fta": fta_dist, "2fgp": two_fgp_rv, "3fgp": three_fgp_rv, "ftp": ftp_rv}

"""
Reads player codes from a list and appends them to the default file with point based stats for the given player

@param player_list The list of players (names or codes) to be written
@param year Optional parameter that allows for modeling players from past years with data
@param isExplicitCode Flag that allows for automatically generating or specifying player codes
@param noFileWrite Prints output to the console
"""
def write_players_to_file(player_list, year="2022", isExplicitCode=False, noFileWrite=False):
    f = open("assets/2022playerdata.txt", "a")
    for player in player_list:
        if not isExplicitCode:
            player = str(player[str(player).index(' ') + 1: str(player).index(' ') + 1 + 5] + player[:2] + '01').lower().replace(' ', '')
        url = f"https://www.basketball-reference.com/players/{player[0]}/{player}/gamelog/{year}"
        src = get_game_log_table(url)
        if noFileWrite:
            dat = get_player_data(src)
            print(f"{player} | 2fga, mean: {dat['2fga'].mean()}, std: {dat['2fga'].std()} | 3fga, mean: {dat['3fga'].mean()}, std: {dat['3fga'].std()} | fta, mean: {dat['fta'].mean()}, std: {dat['fta'].std()} | 2fgp: args: {dat['2fgp'].args} | 3fgp: {dat['3fgp'].args} | ftp: {dat['ftp'].args}")
        else:
            if src == 'NO DATA FOUND':
                f.write(f"{player}: NO DATA FOUND\n")
                print("NO DATA FOUND")
            else: 
                dat = get_player_data(src)
                f.write(f"{player} | 2fga, mean: {dat['2fga'].mean()}, std: {dat['2fga'].std()} | 3fga, mean: {dat['3fga'].mean()}, std: {dat['3fga'].std()} | fta, mean: {dat['fta'].mean()}, std: {dat['fta'].std()} | 2fgp: {dat['2fgp'].args} | 3fgp: {dat['3fgp'].args} | ftp: {dat['ftp'].args}\n")
                print(f"{player} written to file")
        time.sleep(10)
    f.close()

"""
Write all available stat distributions for all players in the league in one file.
"""
def write_complete():
    player_data = []
    with open('assets/2022playerdata.txt', 'r') as f:
        player_data = [line.strip() for line in f]
        f.close()
    dest = open("assets/2022playerdataFINAL.txt", "a")
    for line in player_data:
        if line[0] == '-':
            dest.write(line)
        else:
            player_code = line[:line.index(' ')]
            points_info = ""
            src = get_game_log_table(f"https://www.basketball-reference.com/players/{player_code[0]}/{player_code}/gamelog/{2022}")
            res = ""
            if src == 'NO DATA FOUND':
                res = f"({player_code}) | NO DATA FOUND\n"
            else:
                prev_mins = get_stat_dist("mins", src)
                ast = get_stat_dist("ast", src)
                reb = get_stat_dist("reb", src)
                blk = get_stat_dist("blk", src)
                stl = get_stat_dist("stl", src)
                res = f"({player_code}) | prev_mins, mean: {prev_mins.mean()}, std: {prev_mins.std()} | {points_info} | ast, mean: {ast.mean()}, std: {ast.std()} | reb, mean: {reb.mean()}, std: {reb.std()} | stl, mean: {stl.mean()}, std: {stl.std()} | blk, mean: {blk.mean()}, std: {blk.std()}\n"
            dest.write(res)
            print(res)
            time.sleep(5)
    dest.close()

"""
If this file is called explicitly, enter a player code to view their profile
"""
def main():
    player_code = input("Enter player code: ")
    src = get_game_log_table(f"https://www.basketball-reference.com/players/{player_code[0]}/{player_code}/gamelog/2023")
    dat = get_player_data(src)
    other = {"mins": get_stat_dist("mins", src), "ast": get_stat_dist("ast", src), "reb": get_stat_dist("reb", src), "blk": get_stat_dist("blk", src), "stl": get_stat_dist("stl", src)}
    info = {
            "curr_mins": other["mins"].mean(),
            "prev_mins": other["mins"].mean(),
            "2fg": {"2fga": {"mean": dat["2fga"].mean(), "std": dat["2fga"].std()}, "2fgp": {"make": dat["2fgp"].args[0], "miss": dat["2fgp"].args[1]}},
            "3fg": {"3fga": {"mean": dat["3fga"].mean(), "std": dat["3fga"].std()}, "3fgp": {"make": dat["3fgp"].args[0], "miss": dat["3fgp"].args[1]}},
            "ft": {"fta": {"mean": dat["fta"].mean(), "std": dat["fta"].std()}, "ftp": {"make": dat["ftp"].args[0], "miss": dat["ftp"].args[0]}},
            "ast": {"mean": other["ast"].mean(), "std": other["ast"].std()}, "reb": {"mean": other["reb"].mean(), "std": other["reb"].std()}, 
            "stl": {"mean": other["stl"].mean(), "std": other["stl"].std()}, "blk": {"mean": other["blk"].mean(), "std": other["blk"].std()}
            }
    print(info)


if __name__ == "__main__":
    main()