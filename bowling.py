import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

class BowlingPoints:
    def __init__(self, url):
        self.url = url
        self.create_bowlingscorecard()

    def create_bowlingscorecard(self):
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
        tables = pd.read_html(self.url, match="BOWLING")
        result_soup = soup.find_all("div", class_="ds-px-4 ds-py-3 ds-border-b ds-border-line")
        match_result = result_soup[0].text.split(',')[0]
        bowling_df = pd.DataFrame()
        try:
            team1 = tables[1].iloc[:, :-2].dropna(subset=["BOWLING"])
            team2 = tables[0].iloc[:, :-2].dropna(subset=["BOWLING"])
            batting_data_frames_list = [team1, team2]
        except IndexError as e:
            # Handle the IndexError here (skip the loop run) if match is abandoned and less than 4 innings played
            pass
        else:
            # Dataframe manipulation of the batting table - cleaning table and adding points calculation, batting position, and match number
            # Check if "NO RESULT" is not present in the match result
            if "NO RESULT" not in match_result:
                df_list = []
                j = 0
                for item in batting_data_frames_list:
                    df = item
                    df = df[df["BOWLING"].str.contains(" to | Titans") == False]
                    df['Team']=team[j].text
                    df['Balls'] = df['O'].astype(str).astype(float)
                    df['Balls'] = df['Balls'].apply(self.over_toBalls)
                    df['R'] = df['R'].astype(str).astype(int)
                    df['M'] = df['M'].astype(str).astype(int)
                    df['W'] = df['W'].astype(str).astype(int)
                    df['0s'] = df['0s'].astype(str).astype(int)
                    df['bowling_pace'] = df.apply(lambda x: self.impact(x), axis=1)
                    df['wicket_points'] = df['W'].apply(self.wicket_points)
                    #df["Bowling_Points"] = df["wicket_points"] + df["bowling_pace"] + df["0s"] + (20 * df["M"])
                    df.loc[:, "Bowling_Points"] = df["wicket_points"] + df["bowling_pace"] + df["0s"] + (20 * df["M"])
                    df['Match #'] = match_number
                    j += 1
                    df_list.append(df)
                bowling_df = pd.concat(df_list, ignore_index=True)
            else:
                bowling_df = pd.DataFrame()  # Create an empty DataFrame when "NO RESULT" is present

        return bowling_df


    def over_toBalls(self, x):
        if x % 1 ==0:
            return int (x*6)
        else:
            return int(int(x) * 6) + (round((x % 1), 1) * 10)

    def impact(self, z):
        if (z["Balls"] * 1.0) - z["R"] >= 0:
            return 2 * ((z["Balls"] * 1.0) - z["R"])
        else:
            return z["Balls"] * 1.0 - z["R"]

    def wicket_points(self,y):
        if y == 1:
            return 20
        elif y == 2:
            return 20 * y
        elif y == 3:
            return 30 * y
        elif y == 4:
            return 40 * y
        elif y >= 5:
            return 50 * y
        else:
            return 0







