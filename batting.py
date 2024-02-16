import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

class BattingPoints:
    def __init__(self, url):
        self.url = url
        self.create_battingscorecard()

    def create_battingscorecard(self):
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
        tables = pd.read_html(self.url, match="BATTING")
        result_soup = soup.find_all("div", class_="ds-px-4 ds-py-3 ds-border-b ds-border-line")
        match_result = result_soup[0].text.split(',')[0]
        batting_df = pd.DataFrame()
        try:
            team1 = tables[0].iloc[:, :-2].dropna(subset=["BATTING"])
            team2 = tables[1].iloc[:, :-2].dropna(subset=["BATTING"])
            batting_data_frames_list = [team1, team2]
        except IndexError as e:
            # Handle the IndexError here (skip the loop run)
            pass
        else:
            # Dataframe manipulation of the batting table - cleaning table and adding points calculation, batting position, and match number
            # Check if "NO RESULT" is not present in the match result
            if "NO RESULT" not in match_result:
                df_list = []
                i = 0
                for item in batting_data_frames_list:
                    df = item
                    df = df[df["BATTING"].str.contains("Fall of wickets|Extras|TOTAL|Did not bat|Yet to bat") == False]
                    df = df.rename(columns={'Unnamed: 1': "Details"})
                    df['Team'] = team[i].text
                    df["BATTING"] = df["BATTING"].replace([r"\(c\)", "\†"], ["", ""], regex=True)
                    df["BATTING"] = df["BATTING"].str.strip()
                    df['R'] = df['R'].astype(str).astype(int)
                    df['B'] = df['B'].astype(str).astype(int)
                    df['6s'] = df['6s'].astype(str).astype(int)
                    df['batting_pace'] = df.apply(lambda x : self.batting_impact(x), axis=1)
                    df['batting_bonus'] = df['R'].apply(self.batting_milestones)
                    df["duck_calc"] = df.apply(lambda row: self.duck(row), axis=1)
                    df["Batting_Points"] = df['R'] + (2 * df['6s']) + df['batting_bonus'] + df[
                        "duck_calc"] + df['batting_pace']
                    df['Batting_Pos'] = df.reset_index().index + 1
                    df['Match #'] = match_number
                    i += 1
                    df_list.append(df)
                batting_df = pd.concat(df_list, ignore_index=True)
            else:
                batting_df = pd.DataFrame()  # Create an empty DataFrame when "NO RESULT" is present

        return batting_df

    def batting_milestones(self,x):
        if x >= 200:
            return 490
        if x >= 150:
            return 190
        elif x >= 100:
            return 90
        elif x >= 75:
            return 50
        elif x >= 50:
            return 25
        elif x >= 25:
            return 10
        else:
            return 0

    def duck(self,row):
        if row["Details"] != "not out" and row["R"] == int(0):
            return -5
        else:
            return 0

    def batting_impact(self, x):
        if (x["R"] - x["B"]) >= 0:
            return 2 * (x["R"] - x["B"])
        else:
            return x["R"] - x["B"]

