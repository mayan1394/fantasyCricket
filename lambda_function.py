import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from bs4 import BeautifulSoup
from battingpoints import BattingPoints
from bowlingpoints import BowlingPoints
from fieldingpoints import FieldingPoints
from datetime import datetime,timedelta
from gspread.exceptions import APIError 


scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',"https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

credentials = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
client = gspread.authorize(credentials)



base_url = "https://www.espncricinfo.com"
fixture_url = f"{base_url}/series/icc-cricket-world-cup-2023-24-1367856/match-schedule-fixtures-and-results"

google_spreadsheet = 'cricOMania Prod'
spreadsheet = client.open(google_spreadsheet)



def lambda_handler(event, context):
    # Iterate through the match dates in the loaded match data
    with open('matc_data_wc.json', 'r') as json_file:
        match_data = json.load(json_file)
    
    today_date = datetime.now().date()
    one_day_behind = today_date - timedelta(days=1)
    filtered_match_data = {}
    
    
    for match_date, urls in match_data.items():
        match_date_obj = datetime.strptime(match_date, '%Y-%m-%d').date()
        #print(match_date_obj)
        # Check if the match date is 1 day behind today's date
        if match_date_obj == one_day_behind:
            filtered_match_data[match_date] = urls
    # Print the filtered match data
    #for date, urls in filtered_match_data.items():
        #print(f"Match Date: {date}")
        #print(f"Scorecard URLs: {urls}\n")
            response = requests.get(fixture_url)
            soup = BeautifulSoup(response.content,"html.parser")
            match_result_elements = soup.find_all("a", class_="ds-no-tap-higlight")
            spreadsheet = client.open(google_spreadsheet)


            batting_worksheet = spreadsheet.get_worksheet(0)
            bowling_worksheet = spreadsheet.get_worksheet(1)
            fielding_worksheet = spreadsheet.get_worksheet(2)
            
            batting_last_row = len(batting_worksheet.get_all_values()) + 1
            bowling_last_row = len(bowling_worksheet.get_all_values()) + 1
            fielding_last_row = len(fielding_worksheet.get_all_values()) + 1
            
            
            
            """
            for element in match_result_elements:
                if "indian-premier-league" in element["href"] and "scorecard" in element["href"]:
                    match_url = base_url + element["href"]
                    print(match_url)
                    match_response = requests.get(match_url)
                    match_soup = BeautifulSoup(match_response.content, "html.parser")
            gspre
                    #rows = match_soup.find_all("tbody")
                    #print(rows)
            """
            for element in urls:
                if "icc-cricket-world-cup" in element and "full-scorecard" in element:
                    match_url = base_url + element
                    #print(match_url)
                    
                    batting_df = BattingPoints(url=match_url)
                    bowling_df = BowlingPoints(url=match_url)
                    fielding_df = FieldingPoints(url=match_url)
                    
                    batting_value = batting_df.create_battingscorecard()
                    bowling_value = bowling_df.create_bowlingscorecard()
                    fielding_value = fielding_df.create_fieldingscorecard()
                    
                    
                    bat_to_list_value = batting_value.values.tolist()
                    bowl_to_list_value = bowling_value.values.tolist()
                    field_to_list_value = fielding_value.values.tolist()
                    
                    
                    try:
                        batting_worksheet.insert_rows(bat_to_list_value, row=batting_last_row)
                        bowling_worksheet.insert_rows(bowl_to_list_value, row=bowling_last_row)
                        fielding_worksheet.insert_rows(field_to_list_value, row=fielding_last_row)
                    except APIError as e:
                        print('Error Occured')
                    finally:
                        batting_last_row += len(bat_to_list_value)
                        bowling_last_row += len(bowl_to_list_value)
                        fielding_last_row += len(field_to_list_value)

      
    
    # TODO implement
    return {
        'statusCode': 200,
        #'body': json.dumps('Hello from Lambda!')
    }


