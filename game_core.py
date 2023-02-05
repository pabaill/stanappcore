from scipy import stats
import math
import re
from basketball_reference_scraper.players import get_game_logs
import bbrefscraper
import time
import ast

TEAMS = ["ATL", "BOS", "BRK", "CHI", "CHO", "CLE", "DAL", "DEN", "DET", "GSW", "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN", "NOP", "NYK", "OKC", "ORL", "PHI", "PHO", "POR", "SAC", "SAS", "TOR", "UTA", "WAS"]
EAST_CONF = ["ATL", "BOS", "BRK", "CHI", "CHO", "CLE", "DET", "IND", "MIA", "MIL", "NYK", "ORL", "PHI", "TOR", "WAS"]
WEST_CONF = ["DAL", "DEN", "GSW", "HOU", "LAC", "LAL", "MEM", "MIN", "NOP", "OKC", "PHO", "POR", "SAC", "SAS", "UTA"]

# Average field goal attempts per team
PACE = 84

"""
Get all player data for a given day and write it to the backup text file fname.
@param dict The object in which to store all player data while writing it
@param fname If not specified, the user is prompted for a file name. Otherwise
it can be created procedurally as needed.
"""
def scrape_today(dict, fname=""):
    for team in TEAMS:
        dict["teams"][team] = {}
    with open("assets/2022playerdataFINAL.txt", "r", encoding="utf-8") as f:
        while fname == "":
            fname = input("Enter a nickname for the backup file: ")
        dest = open(f"assets/2023playerdata{fname}.txt", "x", encoding="utf-8")
        curr_team = ''
        for line in f:
            line = line.strip()
            if line[0] != '-':
                player_name = line[:line.index(' (')]
                player_code = line[line.index('(') + 1:line.index(')')]
                url = f"https://www.basketball-reference.com/players/{player_code[0]}/{player_code}/gamelog/2023"
                src = bbrefscraper.get_game_log_table(url)
                if src == "NO DATA FOUND":
                    # Use default data when 2023 data not available/malformed
                    line = line.split(' | ')
                    dict["teams"][curr_team][line[0][:line[0].index('(') - 1]] = {
                        "curr_mins": float(line[1][line[1].index(',') + 2:]),
                        "prev_mins": float(line[2].split(', ')[1][6:]),
                        "2fg": {"2fga": {"mean": float(line[3].split(', ')[1][6:]), "std": float(line[3].split(', ')[2][5:])}, "2fgp": {"make": int(line[6][line[6].index('(') + 1:line[6].index(',')]), "miss": int(line[6][line[6].index(',') + 2:line[6].index(')')])}},
                        "3fg": {"3fga": {"mean": float(line[4].split(', ')[1][6:]), "std": float(line[4].split(', ')[2][5:])}, "3fgp": {"make": int(line[7][line[7].index('(') + 1:line[7].index(',')]), "miss": int(line[7][line[7].index(',') + 2:line[7].index(')')])}},
                        "ft": {"fta": {"mean": float(line[5].split(', ')[1][6:]), "std": float(line[5].split(', ')[2][5:])}, "ftp": {"make": int(line[8][line[8].index('(') + 1:line[8].index(',')]), "miss": int(line[8][line[8].index(',') + 2:line[8].index(')')])}},
                        "ast": {"mean": float(line[9].split(', ')[1][6:]), "std": float(line[9].split(', ')[2][5:])}, "reb": {"mean": float(line[10].split(', ')[1][6:]), "std": float(line[10].split(', ')[2][5:])}, 
                        "stl": {"mean": float(line[11].split(', ')[1][6:]), "std": float(line[11].split(', ')[2][5:])}, "blk": {"mean": float(line[12].split(', ')[1][6:]), "std": float(line[12].split(', ')[2][5:])}
                    }
                    dest.write(f"{player_name} ({player_code}) " + str(dict["teams"][curr_team][player_name]) + "\n")
                    print(str(dict["teams"][curr_team][player_name]) + "\n")
                else:
                    dat = bbrefscraper.get_player_data(src)
                    other = {"mins": bbrefscraper.get_stat_dist("mins", src), "ast": bbrefscraper.get_stat_dist("ast", src), "reb": bbrefscraper.get_stat_dist("reb", src), "blk": bbrefscraper.get_stat_dist("blk", src), "stl": bbrefscraper.get_stat_dist("stl", src)}
                    dict["teams"][curr_team][player_name] = {
                                    "curr_mins": other["mins"].mean(),
                                    "prev_mins": other["mins"].mean(),
                                    "2fg": {"2fga": {"mean": dat["2fga"].mean(), "std": dat["2fga"].std()}, "2fgp": {"make": dat["2fgp"].args[0], "miss": dat["2fgp"].args[1]}},
                                    "3fg": {"3fga": {"mean": dat["3fga"].mean(), "std": dat["3fga"].std()}, "3fgp": {"make": dat["3fgp"].args[0], "miss": dat["3fgp"].args[1]}},
                                    "ft": {"fta": {"mean": dat["fta"].mean(), "std": dat["fta"].std()}, "ftp": {"make": dat["ftp"].args[0], "miss": dat["ftp"].args[0]}},
                                    "ast": {"mean": other["ast"].mean(), "std": other["ast"].std()}, "reb": {"mean": other["reb"].mean(), "std": other["reb"].std()}, 
                                    "stl": {"mean": other["stl"].mean(), "std": other["stl"].std()}, "blk": {"mean": other["blk"].mean(), "std": other["blk"].std()}
                                }
                    dest.write(f"{player_name} ({player_code}) " + str(dict["teams"][curr_team][player_name]) + "\n")
                    print(str(dict["teams"][curr_team][player_name]) + "\n")
                time.sleep(5 + stats.randint(0, 5).rvs())
            else:
                curr_team = line[4:7]
                dest.write(line + "\n")
                print(f"Loading {line[4:7]}...")
    return dict
                

"""
Get all player data from a text file and store it in the dictionary. Returns
a dictionary that has all player data and can be populated with game data.
@param readFromDefaultFile If true reads from the default file, which is in
a deprecated format. If false, prompts the user to specify a newer file that
has info stored as dictionary literals.
"""
def load_players(readFromDefaultFile=True):
    dict = {"teams": {}}
             
    current_team = ""
    if readFromDefaultFile:
        with open('assets/2022playerdataFINAL.txt', 'r', encoding='utf8') as f:
            for line in f:
                if line[0] == '-':
                    current_team = line[4:7]
                    dict["teams"][current_team] = {}
                else:
                    line = line.strip().split(' | ')
                    dict["teams"][current_team][line[0][:line[0].index('(') - 1]] = {
                        "curr_mins": float(line[1][line[1].index(',') + 2:]),
                        "prev_mins": float(line[2].split(', ')[1][6:]),
                        "2fg": {"2fga": {"mean": float(line[3].split(', ')[1][6:]), "std": float(line[3].split(', ')[2][5:])}, "2fgp": {"make": int(line[6][line[6].index('(') + 1:line[6].index(',')]), "miss": int(line[6][line[6].index(',') + 2:line[6].index(')')])}},
                        "3fg": {"3fga": {"mean": float(line[4].split(', ')[1][6:]), "std": float(line[4].split(', ')[2][5:])}, "3fgp": {"make": int(line[7][line[7].index('(') + 1:line[7].index(',')]), "miss": int(line[7][line[7].index(',') + 2:line[7].index(')')])}},
                        "ft": {"fta": {"mean": float(line[5].split(', ')[1][6:]), "std": float(line[5].split(', ')[2][5:])}, "ftp": {"make": int(line[8][line[8].index('(') + 1:line[8].index(',')]), "miss": int(line[8][line[8].index(',') + 2:line[8].index(')')])}},
                        "ast": {"mean": float(line[9].split(', ')[1][6:]), "std": float(line[9].split(', ')[2][5:])}, "reb": {"mean": float(line[10].split(', ')[1][6:]), "std": float(line[10].split(', ')[2][5:])}, 
                        "stl": {"mean": float(line[11].split(', ')[1][6:]), "std": float(line[11].split(', ')[2][5:])}, "blk": {"mean": float(line[12].split(', ')[1][6:]), "std": float(line[12].split(', ')[2][5:])}
                    }
            f.close()
    else:
        fname = input("File Name: ")
        with open(f'assets/{fname}', "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line[0] == '-':
                    current_team = line[4:7]
                    dict["teams"][current_team] = {}
                else:
                    # Players are stored in the format PLAYER_NAME (PLAYER_CODE) {...}
                    dict["teams"][current_team][line[:line.index(' (')]] = ast.literal_eval(line[line.index(')') + 2:])
    dict["standings"] = {}
    dict["standings"]["east"] = {}
    for team in EAST_CONF:
        dict["standings"]["east"][team] = {"w": 0, "l": 0}
    dict["standings"]["west"] = {}
    for team in WEST_CONF:
        dict["standings"]["west"][team] = {"w": 0, "l": 0}
    
    dict["gamelogs"] = {}

    dict["league leaders"] = {}
    for team in TEAMS:
        for player in dict["teams"][team]:
            dict["league leaders"][player] = {"pts": 0.0, "reb": 0.0, "ast": 0.0, "stl": 0.0, "blk": 0.0}

    return dict

"""
Simulate a game outcome for the player with profile "info" (as stored in the dictionary
with all of the league data). Samples and creates convolutions that are normalized by
minutes played.
@param info Values to use for stat distributions and random sampling
@param overtime If true, only simulates a single five minute period
"""
def simulate_box_score(info, overtime=False):
    two_fga = round(stats.norm(info["2fg"]["2fga"]["mean"], info["2fg"]["2fga"]["std"]).rvs())
    if two_fga < 0: two_fga = 0
    two_fgm = round(two_fga * stats.beta(info["2fg"]["2fgp"]["make"], info["2fg"]["2fgp"]["miss"]).rvs())
    three_fga = round(stats.norm(info["3fg"]["3fga"]["mean"], info["3fg"]["3fga"]["std"]).rvs())
    if three_fga < 0: three_fga = 0
    three_fgm = round(three_fga * stats.beta(info["3fg"]["3fgp"]["make"], info["3fg"]["3fgp"]["miss"]).rvs())
    fta = round(stats.norm(info["ft"]["fta"]["mean"], info["ft"]["fta"]["std"]).rvs())
    if fta < 0: fta = 0
    ftm = round(fta * stats.beta(info["ft"]["ftp"]["make"], info["ft"]["ftp"]["miss"]).rvs())

    scale = info["curr_mins"]/info["prev_mins"] if info["prev_mins"] > 0 else 0
    if scale > 1.5:
        scale = math.log(scale)

    pts = round(scale * (ftm + 2 * two_fgm + 3 * three_fgm))
    if pts < 0: pts = 0
    ast = round(scale * stats.norm(info["ast"]["mean"], info["ast"]["std"]).rvs())
    if ast < 0: ast = 0
    reb = round(scale * stats.norm(info["reb"]["mean"], info["reb"]["std"]).rvs())
    if reb < 0: reb = 0
    stl = round(scale * stats.norm(info["stl"]["mean"], info["stl"]["std"]).rvs())
    if stl < 0: stl = 0
    blk = round(scale * stats.norm(info["blk"]["mean"], info["blk"]["std"]).rvs())
    if blk < 0: blk = 0

    result = {"mins": info["curr_mins"], "pts": pts, "reb": reb, "ast": ast, "stl": stl, "blk": blk, "fga": two_fga + three_fga, "fg%": (two_fgm + three_fgm)/(two_fga + three_fga) if two_fga + three_fga != 0 else 0, "3pt%": three_fgm/three_fga if three_fga != 0 else 0, "ft%": ftm/fta if fta != 0 else 0}
    if overtime:
        for cat in result:
            # Simulate a five minute period
            result[cat] = int(result[cat] * (5/48))

    return result

"""
Simulate a game outcome for the player with profile "info" (as stored in the dictionary
with all of the league data). Samples and creates convolutions that are normalized by
minutes played.
@param dict Object that contains data for the league
@param date The day of the given matchup in the format YYYY-MM-DD
@param away The name of the away team (ex. ATL)
@param home The name of the home team (ex. DET)
@param isPlayoff Handles saving playoff games, which have irregular dates
"""
def simulate_game(dict, date, away, home, isPlayoff=False):
    dict["gamelogs"][date][f"{away} v. {home}"][away] = {}
    dict["gamelogs"][date][f"{away} v. {home}"][home] = {}
    pts = {home: 0, away: 0}
    for team in [home, away]:
        fga = 0
        while fga < PACE:
            for player in dict["teams"][team]:
                rem_pace = player in dict["gamelogs"][date][f"{away} v. {home}"][team]
                if not rem_pace:
                    dict["gamelogs"][date][f"{away} v. {home}"][team][player] = {}
                box = simulate_box_score(dict["teams"][team][player], overtime=rem_pace)
                pts[team] += box["pts"]

                for category in dict["league leaders"][player]:
                    if category not in dict["gamelogs"][date][f"{away} v. {home}"][team][player]:
                        dict["gamelogs"][date][f"{away} v. {home}"][team][player][category] = box[category]
                    else:
                        dict["gamelogs"][date][f"{away} v. {home}"][team][player][category] += box[category]
                    dict["league leaders"][player][category] += ((1 / 82) * box[category])
                
                fga += box["fga"]
                if fga >= PACE:
                    break

    overtime = 0
    while pts[home] == pts[away]:
        for team in [home, away]:
            fga = 0
            for player in dict["teams"][team]:
                box = simulate_box_score(dict["teams"][team][player], overtime=True)
                pts[team] += box["pts"]

                dict["gamelogs"][date][f"{away} v. {home}"][team][player] = box
                for category in dict["league leaders"][player]:
                    dict["league leaders"][player][category] += ((1 / 82) * box[category])
        
                fga += box["fga"]
                if fga >= PACE * (5/48):
                    break
        overtime += 1

    
    dict["gamelogs"][date][f"{away} v. {home}"]["result"] = f"{away} {pts[away]} - {home} {pts[home]}{' OT' + str(overtime) if overtime > 0 else '' }"
    winner = away if pts[away] > pts[home] else home
    loser = away if winner != away else home
    winner_conf = "west" if winner in WEST_CONF else "east"
    loser_conf = "west" if loser in WEST_CONF else "east"
    if not isPlayoff:
        dict["standings"][winner_conf][winner]["w"] = dict["standings"][winner_conf][winner]["w"] + 1
        dict["standings"][loser_conf][loser]["l"] = dict["standings"][loser_conf][loser]["l"] + 1
    return away == winner

"""
Simulate a game outcome for the player with profile "info" (as stored in the dictionary
with all of the league data). Samples and creates convolutions that are normalized by
minutes played.
@param dict Object that contains data for the league
@param low Team name for the lower seed (ex. ATL)
@param high Team name for the higher seed (ex. DET)
@param series_type Round of the playoffs
"""
def simulate_series(dict, low, high, series_type):
    round = [0, 0]
    while round[0] != 4 and round[1] != 4:
        pseudo_date = f"{series_type} {low} v. {high} G{round[0] + round[1] + 1}"
        dict["gamelogs"][pseudo_date] = {}
        dict["gamelogs"][pseudo_date][f"{low} v. {high}"] = {}
        result = simulate_game(dict, pseudo_date, low, high, isPlayoff=True)
        if result:
            round[0] = round[0] + 1
        else:
            round[1] = round[1] + 1
    print(f"{series_type}: {low} {round[0]} - {high} {round[1]}")
    return low if round[0] == 4 else high

"""
Simulate every playoff series and print the winning team
@param dict Object that contains data for the league, including standings from the previous season
@param east Eastern conference teams in a list, where each entry is [TEAM_NAME, RECORD]
@param west Western conference teams in a list, where each entry is [TEAM_NAME, RECORD]
"""
def simulate_playoffs(dict, east, west):
    # Eastern Conference
    east_champ1 = simulate_series(dict, simulate_series(dict, east[4][0], east[3][0], "ECR1"), simulate_series(dict, east[7][0], east[0][0], "ECR1"), "ECSF")
    east_champ2 = simulate_series(dict, simulate_series(dict, east[5][0], east[2][0], "ECR1"), simulate_series(dict, east[6][0], east[1][0], "ECR1"), "ECSF")
    # Western Conference
    west_champ1 = simulate_series(dict, simulate_series(dict, west[4][0], west[3][0], "WCR1"), simulate_series(dict, west[7][0], west[0][0], "WCR1"), "WCSF")
    west_champ2 = simulate_series(dict, simulate_series(dict, west[5][0], west[2][0], "WCR1"), simulate_series(dict, west[6][0], west[1][0], "WCR1"), "WCSF")

    champ = simulate_series(dict, simulate_series(dict, east_champ2, east_champ1, "ECF"), simulate_series(dict, west_champ2, west_champ1, "ECF"), "NBA FINALS")
    print(f"{champ} has won the NBA Finals!")

"""
Print wins and losses for each team in the list
@param rankings A list in which each entry is of the format [TEAM_NAME, {'w': WINS, 'l': LOSSES}]
"""
def print_standings(rankings):
    for i in range(len(rankings)):
        print(f"{i + 1}. {rankings[i][0]} ({rankings[i][1]['w']} - {rankings[i][1]['l']})")

"""
Print the league leaders in each statistical category
@param rankings A list in which each entry is of the format [PLAYER_NAME, STAT]
@param category The statistical category to view (PTS, REB, AST, STL, BLK)
"""
def print_ranks(rankings, category):
    print(f"--- {category} ---")
    for i in range(len(rankings)):
        print(f"{i + 1}. {rankings[i][0]} ({rankings[i][1][category]})")

"""
Simulate an entire 82 game regular season and playoffs
@param dict A dictionary storing information about the entire league
"""
def simulate_season(dict):
    with open("assets/2022schedule", "r") as f:
        for line in f:
            line = line.strip().split(' ')
            date = line[0][:-1]
            if date not in dict["gamelogs"]:
                dict["gamelogs"][date] = {}
            dict["gamelogs"][date][f"{line[1]} v. {line[3]}"] = {}
            simulate_game(dict, date, line[1], line[3])
    east_conf_stadings = sorted(dict["standings"]["east"].items(), key = lambda x: x[1]["w"], reverse=True)
    west_conf_stadings = sorted(dict["standings"]["west"].items(), key = lambda x: x[1]["w"], reverse=True)
    print("EAST")
    print_standings(east_conf_stadings)
    print("WEST")
    print_standings(west_conf_stadings)
    print("League Leaders")
    print_ranks(sorted(dict["league leaders"].items(), key = lambda x: x[1]["pts"], reverse=True)[:10], "pts")
    print_ranks(sorted(dict["league leaders"].items(), key = lambda x: x[1]["reb"], reverse=True)[:10], "reb")
    print_ranks(sorted(dict["league leaders"].items(), key = lambda x: x[1]["ast"], reverse=True)[:10], "ast")
    print_ranks(sorted(dict["league leaders"].items(), key = lambda x: x[1]["stl"], reverse=True)[:10], "stl")
    print_ranks(sorted(dict["league leaders"].items(), key = lambda x: x[1]["blk"], reverse=True)[:10], "blk")
    print("Simulating Playoffs...")
    simulate_playoffs(dict, east_conf_stadings, west_conf_stadings)

"""
Uses bootstrapping with 1000 samples to generate the probability a given
team wins. Also generates the averages for each player across those 1000 games,
as well as the option to query these samples to explore conditional probabilities
(ex. "What is the probability the Lakers win given LeBron James scores more than 30 points?")
@param dict A dictionary storing information about the entire league
"""
def give_game_odds(dict):
    date = input("Enter a date (YYYY-MM-DD): ")
    while re.search("\d\d\d\d-\d\d-\d\d", date) == None:
        date = input(f"Invalid date {date}\nEnter a date (YYYY-MM-DD): ")
    date = re.search("\d\d\d\d-\d\d-\d\d", date).group(0)
    options = []
    with open("assets/2022schedule", "r") as f:
        for line in f:
            line = line.strip().split(': ')
            if line[0] == date:
                options.append(line[1])
    for i in range(len(options)):
        print(f"{i}. {options[i]}")
    choice = input("Select a game: ")
    while choice not in [str(x) for x in range(len(options))]:
        choice = input(f"Invalid choice {choice}\nSelect a game: ")
    choice = int(choice)

    away, home = options[choice][:3], options[choice][-3:]
    away_w, home_w = 0, 0
    dict["gamelogs"] = {}
    for i in range(1000):
        # Use playoff bool so stats aren't saved and rewritten for each simulation
        dict["gamelogs"][date + f' {i}'] = {}
        dict["gamelogs"][date + f' {i}'][options[choice]] = {}
        result = simulate_game(dict, date + f' {i}', away, home, isPlayoff=True)
        if result:
            away_w += 1
        else:
            home_w += 1
        if i % 100 == 0:
            print(f"{1000 - i} games remaining...")
    print(f"{away}: {away_w/10}%, {home}: {home_w/10}%\n")
    for team in [home, away]:
        print(team)
        for player in dict["teams"][team]:
            for cat in dict["league leaders"][player]:
                # Reuse League Leaders functionality that reduces scores to an average over 82 games,
                # and instead average over 1000 games
                dict["league leaders"][player][cat] = 82 * dict["league leaders"][player][cat] / 1000
            print(f"{player}: {dict['league leaders'][player]}")

    # Additional functionality allows for queries like "what is the probability the TEAM wins if PLAYER scores POINTS points?"
    if input('Would you like to explore conditional probabilities? (y/n): ') == 'y':
        end = ''
        while end != 'y':
            team = away if input(f"Choose 0 for {away}, 1 for {home}: ") == '0' else home
            roster = list(dict['teams'][team].keys())
            for i in range(len(roster)):
                print(f"{i}. {roster[i]}")
            player = roster[int(input('Choose a player: '))]
            point_val = int(input('At least how many points do they score?: '))
            win_and_pv = 0
            pv = 0
            for i in range(1000):
                if dict["gamelogs"][date + f' {i}'][f"{away} v. {home}"][team][player]['pts'] >= point_val:
                    pv += 1
                    result = dict["gamelogs"][date + f' {i}'][f"{away} v. {home}"]['result']
                    away_pts = int(result[result.find(away) + 4:result.find(away) + 7])
                    home_pts = int(result[result.find(home) + 4:result.find(home) + 7])
                    if (team == away and away_pts > home_pts) or (team == home and home_pts > away_pts):
                        win_and_pv += 1

            print(f"{team} wins {win_and_pv/pv}% of the time when {player} scores {point_val} or more points")
            end = input('Quit? (y/n): ')

"""
Allows a user to explore specific game outcomes after a season is stored in dict
@param dict A dictionary storing information about the entire league
"""
def explore_results(dict):
    choice = input("Enter a date (MM-DD) to view a game, or 'q' to quit: ")
    while choice != 'q':
        choice = '2022-' + choice
        if choice in dict["gamelogs"]:
            date = choice
            options = list(dict["gamelogs"][date].keys())
            for i in range(len(options)):
                print(f"{i}. {options[i]}")
            choice = input("Choose a game: ")
            while choice not in [str(x) for x in range(len(options))]:
                choice = input(f"Invalid choice {choice}\nSelect a game: ")
            choice = int(choice)
            for team in dict["gamelogs"][date][options[choice]]:
                if team == 'result':
                    print(dict["gamelogs"][date][options[choice]][team])
                    break
                print(team)
                for player in dict["teams"][team]:
                    if player in dict['gamelogs'][date][options[choice]][team].keys():
                        print(f"{player}: {dict['gamelogs'][date][options[choice]][team][player]}")
        choice = input("Enter a date (MM-DD) to view a game, or 'q' to quit: ")
                

def main():
    print("Loading players and rotations from file...")
    scrape = input("Would you like to update priors with game data to today's date? This could take a while... (y/n): ")
    if scrape == 'y':
        dict = {"teams": {}}
        dict = scrape_today(dict)
    defaultPlayers = input("Would you like to give a custom player file? (y/n): ") == 'n'
    dict = load_players(readFromDefaultFile=defaultPlayers)
    print("Welcome to my CS109 Project, PIECH for NBA! Select a simulation mode:\n1. Full Season\n2. Single Game\n")
    resp = input("Type 1 or 2 (q to quit): ")
    while resp != 'q':
        if resp == '1':
            simulate_season(dict)
            explore_results(dict)
        elif resp == '2':
            give_game_odds(dict)
            # Reset dict
            dict = load_players(readFromDefaultFile=defaultPlayers)
        resp = input("Type 1 or 2 (q to quit): ")

if __name__ == "__main__":
    main()