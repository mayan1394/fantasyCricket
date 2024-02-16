import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

class FieldingPoints:
    def __init__(self, url):
        self.url = url
        self.create_fieldingscorecard()

    def create_fieldingscorecard(self):
        # Define the regex pattern to pull out expected match value
        pattern = re.compile(r'(\d+)(st|nd|rd|th)-(match|semi-final|final)')
        # Find the match using regex
        match = pattern.search(self.url)
        # Extract the match value
        if match:
            if match.group(3) == "semi-final":
                if match.group(2) == "st":
                    match_number = 46
                elif match.group(2) == "nd":
                    match_number = 47
                # Add conditions for "rd" and "th" if needed
            elif match.group(3) == "final":
                match_number = 48
            else:
                match_number = int(match.group(1))
        else:
            match_number = "Match value not found"
        response = requests.get(self.url)
        soup = BeautifulSoup(response.text, "html.parser")
        team = soup.find_all("span", class_="ds-text-title-xs ds-font-bold ds-capitalize")
        player_of_match_element = soup.find("span", text="Player Of The Match")
        if player_of_match_element:
            player_of_match = player_of_match_element.find_next("a").text.strip()
            #print("Player Of The Match:", player_of_match)
        else:
            player_of_match = "POTM not found"
        tables = pd.read_html(self.url, match="BATTING")
        team_fielding_first = tables[0].iloc[:, :-2].dropna(subset="BATTING")
        team_fielding_second = tables[1].iloc[:, :-2].dropna(subset="BATTING")
        runs_team_fielding_second = \
        team_fielding_first[team_fielding_first['BATTING'].str.contains('Total', case=False)]['R'].values[0]
        runs_team_fielding_first = \
        team_fielding_second[team_fielding_second['BATTING'].str.contains('Total', case=False)]['R'].values[0]
        team_fielding_second = team_fielding_second[
            team_fielding_second["BATTING"].str.contains("Fall of wickets|Extras|TOTAL") == False]
        team_fielding_first = team_fielding_first[
            team_fielding_first["BATTING"].str.contains("Fall of wickets|Extras|TOTAL") == False]
        playing_11_team_fielding_first = self.playing_11(team_fielding_second["BATTING"])
        playing_11_team_fielding_second = self.playing_11(team_fielding_first["BATTING"])

        catch_pattern = r'(?:c & b (.*))|(?:c (.*?) b)'
        catches_team_fielding_first = self.extract_raw_player_names_v3(catch_pattern, team_fielding_first["Unnamed: 1"])
        team1_catch_list = self.fielding_players(catches_team_fielding_first, playing_11_team_fielding_first)
        catches_team_fielding_second = self.extract_raw_player_names_v3(catch_pattern, team_fielding_second["Unnamed: 1"])
        team2_catch_list = self.fielding_players(catches_team_fielding_second, playing_11_team_fielding_second)

        stump_pattern = r'st (.*?) b'
        stumping_team_fielding_second = self.extract_raw_player_names_v3(stump_pattern, team_fielding_second["Unnamed: 1"])
        team2_stumping_list = self.fielding_players(stumping_team_fielding_second, playing_11_team_fielding_second)
        stumping_team_fielding_first = self.extract_raw_player_names_v3(stump_pattern, team_fielding_first["Unnamed: 1"])
        team1_stumping_list = self.fielding_players(stumping_team_fielding_first, playing_11_team_fielding_first)

        run_out_pattern = r'run out \((.*?)\)'
        run_outs_team_fielding_first = self.extract_raw_player_names_v3(run_out_pattern, team_fielding_first["Unnamed: 1"])
        if len(run_outs_team_fielding_first) == 0:
            run_outs_team_fielding_first_list = run_outs_team_fielding_first

        elif '/' in run_outs_team_fielding_first:
            run_outs_team_fielding_first_list = run_outs_team_fielding_first

        else:
            run_outs_team_fielding_first_list = run_outs_team_fielding_first[0].split('/')
        team1_run_outs_list = self.fielding_players(run_outs_team_fielding_first_list, playing_11_team_fielding_first)

        run_outs_team_fielding_second = self.extract_raw_player_names_v3(run_out_pattern, team_fielding_second["Unnamed: 1"])
        if len(run_outs_team_fielding_second) == 0:
            run_outs_team_fielding_second_list = run_outs_team_fielding_second

        elif '/' in run_outs_team_fielding_second:
            run_outs_team_fielding_second_list = run_outs_team_fielding_second

        else:
            run_outs_team_fielding_second_list = run_outs_team_fielding_second[0].split('/')
        team2_run_outs_list = self.fielding_players(run_outs_team_fielding_second_list, playing_11_team_fielding_second)

        catches = team1_catch_list + team2_catch_list
        stumpings = team1_stumping_list + team2_stumping_list
        run_outs = team1_run_outs_list + team2_run_outs_list

        data = []
        catch_counts = {}  # Dictionary to keep track of catch counts
        for player in catches:
            if player in catch_counts:
                catch_counts[player] += 1
            else:
                catch_counts[player] = 1

        for player, count in catch_counts.items():
            points = 10 * count  # Points for catches
            if count >= 3:
                points += 20  # Bonus points for 3 or more catches
            data.append((player, 'Catch', points))

        for player in stumpings:
            data.append((player, 'Stumping', 20))  # Points for a stumping

        if len(run_outs) == 1:
            data.append((run_outs[0], 'Direct Hit', 20))  # Points for a direct hit
        else:
            for player in run_outs:
                data.append((player, 'Run Out', 10))  # Points for a standard run out

        df = pd.DataFrame(data, columns=['Player Name', 'Category', 'Points'])
        df = df.groupby(['Player Name', 'Category']).sum().reset_index()
        df.loc[len(df.index)] = [player_of_match, "POTM", 25]

        #runs_team_fielding_second = \
        #team_fielding_first[team_fielding_first['BATTING'].str.contains('Total', case=False)]['R'].values[0]
        if "/" not in runs_team_fielding_second:
            # print(runs_team_fielding_second)
            runs_team_fielding_second = int(runs_team_fielding_second)
        else:
            runs_team_fielding_second = runs_team_fielding_second.split("/")[0]
            runs_team_fielding_second = int(runs_team_fielding_second.split("/")[0])

        #runs_team_fielding_first = \
        #team_fielding_second[team_fielding_second['BATTING'].str.contains('Total', case=False)]['R'].values[0]
        if "/" not in runs_team_fielding_first:
            # print(runs_team_fielding_first)
            runs_team_fielding_first = int(runs_team_fielding_first)
        else:
            runs_team_fielding_first = int(runs_team_fielding_first.split("/")[0])

        if runs_team_fielding_second > runs_team_fielding_first:
            data_to_append = [{"Player Name": player_name, "Category": "Winning Team Playing 11", "Points": 5} for
                              player_name in playing_11_team_fielding_second]
            df = pd.concat([df, pd.DataFrame(data_to_append)], ignore_index=True)
        else:
            data_to_append = [{"Player Name": player_name, "Category": "Winning Team Playing 11", "Points": 5} for
                              player_name in playing_11_team_fielding_first]
            df = pd.concat([df, pd.DataFrame(data_to_append)], ignore_index=True)

        df["Match #"] = match_number
        return df


    def playing_11(self, batting_list):
        names = []
        # list_players = batting_list.str.findall(r'\w+(?:\s\w+)?').tolist()
        for entry in batting_list:
            player_names = re.findall(r'[A-Za-z]+(?:\s[A-Za-z]+)+', entry)
            names.extend(player_names)
        playing_11 = [names for names in names if not names.startswith(("Did not", "Yet to"))]
        return playing_11


    def extract_raw_player_names_v3(self, regex, fielding_column):
        raw_player_names = fielding_column.str.extract(regex, expand=False).fillna('')
        if isinstance(raw_player_names, pd.DataFrame):
            # If there are multiple columns, concatenate them into a single "Result" column
            raw_player_names["Result"] = raw_player_names.apply(lambda row: ''.join(row), axis=1)
        else:
            # If it's already a Series, create a "Result" column
            raw_player_names = pd.DataFrame({"Result": raw_player_names})

        raw_player_names = raw_player_names[raw_player_names["Result"] != ""]
        raw_players = raw_player_names["Result"].tolist()
        raw_players = [item for item in raw_players if not item.startswith("sub")]
        return raw_players

    def fielding_players(self, fielding_list, team_list):
        fielding = []
        for item in fielding_list:
            best_match = process.extractOne(item, team_list, scorer=fuzz.partial_ratio)
            fielding.append(best_match[0])
        return fielding
