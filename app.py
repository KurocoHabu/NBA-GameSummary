import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import time
import plotly.graph_objects as go

import warnings
warnings.filterwarnings('ignore')


def _pbp_scrape(url):
    df = pd.DataFrame(columns=['time', 'event_away', 'point_away', 'score', 'point_home','event_home', 'game_id'])

    tables = pd.io.html.read_html(url)[0]['1st Q']
    tables.set_axis(['time', 'event_away', 'point_away', 'score', 'point_home','event_home'], axis=1, inplace=True)
    df = pd.concat([df, tables])
    
    df['periodTime'] = df.time.apply(createTime)
    df = df[df['periodTime'].apply(lambda x: isinstance(x, (int, float)))]
    df["game_id"]=2
    df.drop(columns=['time'], inplace=True)
    
    df["period_start"] = np.where(df["event_away"].str.contains("Start of", na=False), 1, 0)
    
    prevGame_id = 0
    lst = []
    
    for i, row in df.iterrows():
        if prevGame_id != row.game_id:
            lst.append(1)
            prevGame_id = row.game_id
            continue
        if (row.periodTime == 720) & (row.period_start==1):
            lst.append(lst[-1] + 1)
            continue
        elif (row.periodTime == 300) & (row.period_start)==1:
            lst.append(lst[-1] + 1)
            continue
        else:
            lst.append(lst[-1])
            
    df['period'] = lst
    
    pointsAway = []
    pointsHome = []

    for i, row in df.iterrows():
        point_lst = createScore(row)
        if point_lst != None:
            pointsAway.append(point_lst[0])
            pointsHome.append(point_lst[1])
        else:
            if row.period == 1 and row.periodTime == 720:
                pointsAway.append(0)
                pointsHome.append(0)
            else:
                pointsAway.append(pointsAway[-1])
                pointsHome.append(pointsHome[-1])
                
    df['homePoints'] = pointsHome
    df['awayPoints'] = pointsAway

    df.drop(columns=['score'], inplace=True)
    
    df['point_away'] = cleanDuplicateValues(df, 'point_away')
    df['point_home'] = cleanDuplicateValues(df, 'point_home')
    df['event_home'] = cleanDuplicateValues(df, 'event_home')
    
    return df
    


def createTime(row):
    try:
        minute, sec = row.split(":")
        sec = sec.split('.')[0]
        return int(minute)*60 + int(sec)
    except:
        return row
    


def createScore(row):
    try:
        return [int(i) for i in row.score.split('-')]
    except:
        return None
    
    

def cleanDuplicateValues(df, colName):
    return_lst = []
    for i, row in df.iterrows():
        if row.event_away == row.point_away:
            return_lst.append(None)
        elif row.point_away == None:
            return_lst.append(None)
        else:
            return_lst.append(row[colName])
    return return_lst


def _get_games(matchup, date):
    games = pd.read_csv("data/games2023-2024.csv")
    game_df = games[(games["datetime"]==date)&(games["MatchUp"]==matchup)]
    
    if len(games)==0:
        return (-1, -1, -1, -1, -1)
    
    else:
        game_id = game_df["game_id"].iloc[-1]
        pbp_url = game_df["pbp_url"].iloc[-1]
        bs_url = game_df["bs_url"].iloc[-1]
#         matchup = game_df["MatchUp"].iloc[-1]
        
        return game_id, pbp_url, bs_url



def _pbp_cleaning(df):
    teamAbbreviation = {'Dallas Mavericks':'DAL', 'Phoenix Suns':'PHO', 'Boston Celtics':'BOS',
       'Portland Trail Blazers':'POR', 'New Jersey Nets':'NJN', 'Toronto Raptors':'TOR',
       'Los Angeles Lakers':'LAL', 'Utah Jazz':'UTA', 'Philadelphia 76ers':'PHI',
       'New York Knicks':'NYK', 'Minnesota Timberwolves':'MIN', 'Orlando Magic':'ORL',
       'San Antonio Spurs':'SAS', 'Sacramento Kings':'SAC', 'Atlanta Hawks':'ATL',
       'Seattle SuperSonics':'SEA', 'Washington Bullets':'WSB', 'Indiana Pacers':'IND',
       'Los Angeles Clippers':'LAC', 'Miami Heat':'MIA', 'Milwaukee Bucks':'MIL',
       'Charlotte Hornets':'CHA', 'Cleveland Cavaliers':'CLE', 'Houston Rockets':'HOU',
       'Denver Nuggets':'DEN', 'Vancouver Grizzlies':'VAN', 'Golden State Warriors':'GSW',
       'Chicago Bulls':'CHI', 'Detroit Pistons':'DET', 'Washington Wizards':'WAS',
       'Memphis Grizzlies':'MEM', 'New Orleans Hornets':'NOH', 'Charlotte Bobcats':'CHA',
       'New Orleans/Oklahoma City Hornets':'NOK', 'Oklahoma City Thunder':'OKC',
       'Brooklyn Nets':'BRK', 'New Orleans Pelicans':'NOP', 'Buffalo Braves': 'BUF',
        'Kansas City-Omaha Kings':'KCO', 'New Orleans Jazz':'NOJ', 'Kansas City Kings':'KCK',
        'New York Nets':'NYN', 'San Diego Clippers':'SDC'}
    
    df["event_away"] = df["event_away"].str.replace("3-pt tip-in", "3-pt jump shot")
    df["event_home"] = df["event_home"].str.replace("3-pt tip-in", "3-pt jump shot")
    df["event_away"] = df["event_away"].str.replace("3-pt dunk", "2-pt dunk")
    df["event_home"] = df["event_home"].str.replace("3-pt dunk", "2-pt dunk")
    df["event_away"] = df["event_away"].str.replace("3-pt layup at rim", "2-pt layup at rim")
    df["event_home"] = df["event_home"].str.replace("3-pt layup at rim", "2-pt layup at rim")
    df["event_away"] = df["event_away"].str.replace("3-pt layup", "3-pt jump shot")
    df["event_home"] = df["event_home"].str.replace("3-pt layup", "3-pt jump shot")
    df["event_away"] = df["event_away"].str.replace("3-pt shot", "3-pt jump shot")
    df["event_home"] = df["event_home"].str.replace("3-pt shot", "3-pt jump shot")
    df["event_away"] = df["event_away"].str.replace("2-pt shot", "2-pt jump shot")
    df["event_home"] = df["event_home"].str.replace("2-pt shot", "2-pt jump shot")

    df["ShotType"] = np.where((df["event_away"].str.contains("dunk", na=False))|(df["event_home"].str.contains("dunk", na=False)),"dunk",
                            np.where((df["event_away"].str.contains("layup", na=False))|(df["event_home"].str.contains("layup", na=False)),"layup",
                            np.where((df["event_away"].str.contains("jump shot", na=False))|(df["event_home"].str.contains("jump shot", na=False)),"jump shot",
                            np.where((df["event_away"].str.contains("hook", na=False))|(df["event_home"].str.contains("hook", na=False)),"hook",
                            np.where((df["event_away"].str.contains("tip-in", na=False))|(df["event_home"].str.contains("tip-in", na=False)),"tip-in",
                            np.where((df["event_away"].str.contains("free throw", na=False))|(df["event_home"].str.contains("free throw", na=False)),"FT",
                            np.where((df["event_away"].str.contains("no shot", na=False))|(df["event_home"].str.contains("no shot", na=False)),"FT", "")))))))

    map_words = {"dunk": "FG", "layup": "FG", "jump shot": "FG", "hook": "FG", "tip-in": "FG", "FT": "FT"}

    df["ShotClass"] = df["ShotType"].map(map_words)

    df["ShotScore"] = np.where((df["event_away"].str.contains("3-pt", na=False))|(df["event_home"].str.contains("3-pt", na=False)),3,
                            np.where((df["event_away"].str.contains("free throw", na=False))|(df["event_home"].str.contains("free throw", na=False)),1,2))

    df["awayTeam_abb"] = df["awayTeam"].map(teamAbbreviation)
    df["homeTeam_abb"] = df["homeTeam"].map(teamAbbreviation)

    df["eventTeam"] = np.where(df["event_away"].isna(), df["homeTeam"], df["awayTeam"])
    df["eventTeam_abb"] = df["eventTeam"].map(teamAbbreviation)

    df["Assister"] = ""
    df.loc[df['event_away'].astype(str).str.contains('assist by'), 'Assister'] = df['event_away'].str.replace(r'(.*assist by)','',regex=True)
    df.loc[df['event_home'].astype(str).str.contains('assist by'), 'Assister'] = df['event_home'].str.replace(r'(.*assist by)','',regex=True)
    df["Assister"] = df["Assister"].str.replace(")", "")
    df["Assister"] = df["Assister"].str.replace(" ", "")

    df["Shooter"] = ""
    df.loc[df['event_away'].astype(str).str.contains('makes'), 'Shooter'] = df['event_away'].str.replace(r'(makes.*)','',regex=True)
    df.loc[df['event_home'].astype(str).str.contains('makes'), 'Shooter'] = df['event_home'].str.replace(r'(makes.*)','',regex=True)
    df.loc[df['event_away'].astype(str).str.contains('misses'), 'Shooter'] = df['event_away'].str.replace(r'(misses.*)','',regex=True)
    df.loc[df['event_home'].astype(str).str.contains('misses'), 'Shooter'] = df['event_home'].str.replace(r'(misses.*)','',regex=True)
    df["Shooter"] = df["Shooter"].str.replace(")", "")
    df["Shooter"] = df["Shooter"].str.replace(" ", "")
    
    df["ShotResult"] = ""
    df.loc[df['event_away'].astype(str).str.contains('misses'), "ShotResult"] = 0
    df.loc[df['event_home'].astype(str).str.contains('misses'), "ShotResult"] = 0
    df.loc[df['event_away'].astype(str).str.contains('makes'), "ShotResult"] = 1
    df.loc[df['event_home'].astype(str).str.contains('makes'), "ShotResult"] = 1
    df["play_id"] = [x+1 for x in range(len(df))]
    
    period_num = len(df["period"].unique())

    time_dic = {a: period_num-a for a in range(1, period_num+1)}
    # print(time_dic)

    df["left_period"] = df["period"].map(time_dic)

    df["Time"] = [x*720 + y for x, y in zip(df["left_period"], df["periodTime"])]
    df["Time_shift"] = df["Time"].shift(fill_value=720*len(df.period.unique()))
    df["Time_Span"] = df["Time_shift"] - df["Time"]
    df["Time_Span_0"] = np.where(df["Time_Span"]==0, 1, 0)

    df["MemberChange"] = np.where((df["event_away"].str.contains("enters the game ", na=False))|
                                (df["event_home"].str.contains("enters the game ", na=False)), 1, 0)
    
    for i in range(1, 6):
        df["MemberChange_shift_" + str(i)] = df["MemberChange"].shift(i)

    df["MemberChange_+5"] = np.where((df["MemberChange_shift_1"]==1)|
                                      (df["MemberChange_shift_2"]==1)|
                                      (df["MemberChange_shift_3"]==1)|
                                      (df["MemberChange_shift_4"]==1)|
                                      (df["MemberChange_shift_5"]==1), 1, 0)

    df["MemberChange_H"] = np.where((df["MemberChange"]==1)&(df["event_away"].isna()), 1, 0)

    df["MemberChangeEvent"] = np.where((df["MemberChange"]==1)&(df["event_away"].isna()), df["event_home"], 
                                    np.where((df["MemberChange"]==1)&(df["event_home"].isna()), df["event_away"], np.nan))

    df["MemberIn"] = np.where(~df["MemberChangeEvent"].isna(), df["MemberChangeEvent"].str.replace("( enters the game.*)", ""), "")
    df["MemberOut"] = np.where(~df["MemberChangeEvent"].isna(), df["MemberChangeEvent"].str.replace("(.*enters the game for )", ""), "")

    df["delay of game"] = np.where((df["event_away"].str.contains("delay of game", na=False))|
                               (df["event_home"].str.contains("delay of game", na=False)), 1, 0)
    df["Technical foul"] = np.where((df["event_away"].str.contains("Technical foul", na=False))|
                                   (df["event_home"].str.contains("Technical foul", na=False)), 1, 0)
    df["DOGorTECH"] = np.where((df["delay of game"]==1)|(df["Technical foul"]==1), 1, 0)
    df["Technical FT"] = np.where((df["event_away"].str.contains("makes technical free throw", na=False))|
                                             (df["event_home"].str.contains("makes technical free throw", na=False)), 1, 0)
    
    df["event"] = np.where(df["event_away"].isna(), df["event_home"], df["event_away"])
    df["event_shift+1"] = df["event"].shift(1)
    df["event_shift-1"] = df["event"].shift(-1)

    df["LFoul after DRB"] = np.where((df["event"].str.contains("Defensive rebound by Team")&(df["event_shift+1"].str.contains("Loose ball foul"))), 1, 0)

    df["LFoul after DRB_shift"] = df["LFoul after DRB"].shift(-1)

    df["Foul after FT"] = np.where((df["event_shift+1"].str.contains("free throw"))&(df["LFoul after DRB"]==1), 1, 0)
    
    df["FT"] = np.where(df["event"].str.contains("free throw"), 1, 0)
    df["FT_shift+1"] = df["FT"].shift(1)
    df["FT_shift-1"] = df["FT"].shift(-1)
    df["FT_shift+-1"] = np.where((df["FT_shift-1"]==1)|(df["FT_shift+1"]==1), 1, 0)
    
    df["TO"] = np.where(df["event"].str.contains("Turnover by .*", regex=True), 1, 0)
    df["TimeOut"] = np.where(df["event"].str.contains("timeout", regex=True), 1, 0)


    return df


def _players_dict(team):
    if team == "ATL":
        players = {"T.Young": "Trae", "D.Murray": "Dejo", "J.Collins": "John", "C.Capela": "Clint", "D.Hunter": "Hunter", "O.Okongwu": "Oko", 
                   "J.Johnson": "Jalen", "A.Holiday": "A-Holi", "J.Holiday": "J-Holi", "B.Bogdanović": "Bog", "A.Griffin": "AJ", "V.Krejci": "Vit",
                   "F.Kaminsky": "Frank", "S.Bey": "Bey", "G.Mathews": "Mathews", "B.Fernando": "Bruno", "T.Forrest":"Trent", "V.Krejci": "Vit"}
    elif team == "BOS":
        players = {"J.Tatum": "Tatum","J.Brown": "JB" , "A.Horford": "Al", "M.Smart": "Smart", "D.White": "White", "G.Williams": "Grant", 
                   "S.Hauser": "Sam", "R.Williams": "RobW", "L.Kornet": "Luke", "M.Muscala": "Mike", "J.Davidson": "JDD", "M.Brogdon": "Brogdon",
                   "B.Griffin": "Blake", "P.Pritchard": "Pritchard", "M.Kabengele": "Kabengele"}
    elif team == "BRK":
        players = {"B.Simmons": "Ben", "S.Curry": "Seth", "J.Harris": "Joe", "N.Claxton": "Clax", "R.O'Neale": "Royce", 
                   "C.Thomas": "CamT", "D.Sharpe": "D.S", "M.Bridges": "Mikal", "Y.Watanabe": "Yuta", "S.Dinwiddie": "DinW", "C.Johnson": "CamJ", "P.Mills": "Patty",
                   "D.Finney-Smith": "DFS", "E.Sumner": "Sumner", "D.Smith": "Dru", "D.Duke": "DDJ", "M.Brown": "Moses"}
    elif team == "CHO":
        players = {"P.Washington": "PJW","L.Ball": "Ball" , "K.Oubre": "Oubre", "D.Smith": "DSJ", "T.Rozier": "Terry", "J.Thor": "Thor", 
                   "N.Richards": "Nick", "G.Heyward": "Gordon", "B.McGowens": "Bryce", "K.Jones": "Kai", "M.Williams": "Mark", "T.Maledon": "Théo",
                   "J.Bouknight": "JamesB", "S.Mykhailiuk": "Svi", "C.Martin": "Cody", "X.Sneed": "Sneed", "K.Simmons": "Kobi"}        
    elif team == "CHI":
        players = {"D.DeRozan": "DeMar","Z.LaVine": "Zach" , "N.Vučević": "Vuče", "A.Dosunmu": "Dosun", "P.Williams": "P.W", "A.Caruso": "Caruso", 
                   "P.Beverley": "Beverley", "J.Green": "Green", "A.Drummond": "Drumm", "D.Jones": "DJJ", "C.White": "Coby", "T.Bradley": "Tony",
                   "D.Terry": "Terry", "M.Hill": "Hill", "M.Simonovic": "Marko", "C.Jones": "CJones"}
    elif team == "CLE":
        players = {"D.Garland": "Garland","D.Mitchell": "Mitchell" , "J.Allen": "Allen", "L.Stevens": "Lamar", "C.LeVert": "LeVert", 
                   "C.Osman": "Osman", "I.Okoro": "Okoro", "R.Rubio": "Rubio", "R.Lopez": "Lopez", "D.Green": "Danny", "M.Diakite": "Mamadi",
                   "E.Mobley": "Mobley",}
    elif team == "DAL":
        players = {"L.Dončić": "Luka","K.Irving": "Kyrie" , "T.Hardaway": "THJ", "R.Bullock": "Bullock", "D.Powell": "Powell", 
                   "C.Wood": "Wood", "J.Green": "JoshG", "J.Hardy": "Hardy", "F.Ntilikina": "Frank", "D.Bertāns": "Bertāns", "J.McGee": "McGee",
                   "T.Pinson": "Theo","M.Kleber":"Kleber", "J.Holiday": "JHoli", "A.Lawson": "AJL", "M.Morris": "Morris"}
    elif team == "DEN":
        players = {"N.Jokić": "Jokić", "J.Murray": "Jamal", "A.Gordon": "AG", "M.Porter": "MPJ",  "K.Caldwell-Pope": "KCP", "B.Brown": "BB",
                   "J.Green": "Jeff", "B.Hyland": "Bones", "I.Smith": "Ish", "C.Braun": "Braun", "P.Watson": "Watson", "D.Jordan": "DAJ", 
                   "V.Čančar": "Čančar", "D.Reed": "Reed", "Z.Nnaji": "Zeke", "J.White": "Jack", "T.Bryant": "T.B", "R.Jachson": "R.J"}
    elif team == "DET":
        players = {"C.Cunningham": "Cade", "B.Bogdanović": "Bog", "I.Stewart": "Stewart", "J.Ivey": "Ivey", "J.Duren": "Duren", "C.Joseph": "Cory", 
                   "S.Bey": "Bey", "K.Hayes": "Hayes", "K.Knox": "Knox", "H.Diallo": "Hami", "I.Livers": "Livers", "N.Noel": "Noel",
                   "A.Burks": "Alec", "B.Boeheim": "Buddy"}
    elif team == "GSW":
        players = {"S.Curry": "Steph", "D.Green": "Dray", "K.Thompson": "Klay", "J.Poole": "JP", "A.Wiggins": "Wig", "K.Looney": "Loon", 
                   "D.DiVincenzo": "Donte", "J.Wiseman": "Wise", "M.Moody": "Moo", "R.Rollins": "Ryan", "R.Rollins": "Ryan", "J.Kuminga": "JK", "J.Green": "JMG",
                   "A.Iguodala": "Andre", "T.Jerome": "Ty", "P.Baldwin": "PBJ", "A.Lamb": "Lamb", "G.Payton": "GP2"}    
    elif team == "HOU":
        players = {"J.Green": "Jalen","K.Porter": "KPJ" , "K.Martin": "KJMart", "A.Şengün": "Şengün", "J.Smith": "Jabari", "T.Eason": "Eason", 
                   "J.Christopher": "Josh", "D.Nix": "Nix", "F.Kaminsky": "Frank", "B.Marjanović": "Boban", "U.Garuba": "Usman",
                   "J.Tate": "Tate", "T.Washington": "TWJ", "D.Augustin": "DJA", "T.Hudgins": "Trevor", "D.Days": "Days"}
    elif team == "IND":
        players = {"T.Haliburton": "T.Hali","B.Hield": "Hield" , "B.Mathurin": "Mathurin", "T.McConell": "TJM", "A.Nambhard": "Nambhard", "A.Nesmith": "Nesmith", 
                   "J.Smith": "Jalen", "M.Turner": "Turner", "O.Brissett": "Oshae", "I.Jackson": "Isaiah", "C.Duarte": "Duarte", "J.Nwora": "Nwora",
                   "J.Johnson": "J.J", "G.Hill": "Hill", "D.Theis": "Theis", "K.Brown": "Brown", "G.York": "York"}
    elif team == "LAC":
        players = {"K.Leonard": "Kawhi","P.George": "PG13" , "R.Westbroook": "Russ", "E.Gordon": "Eric", "I.Zubac": "Zubac", "B.Hyland": "Bones", 
                   "N.Batum": "Batum", "T.Mann": "Mann", "M.Plumlee": "Mason", "R.Covington": "R.C", "A.Coffey": "Amir", "M.Diabaté": "M.D",
                   "X.Moon": "Moon", "J.Minott": "Josh", "N.Knight": "Knight", "L.Garza": "Garza"}    
    elif team == "LAL":
        players = {"L.James": "LBJ","A.Davis": "AD" , "A.Reaves": "Reaves", "J.Vanderbilt": "Vando", "D.Schröder": "Schrö", "D.Russell": "Dlo", 
                   "R.Hachimura": "Rui", "M.Christie": "Max", "D.Reed": "Reed", "T.Brown": "TBJ", "L.Walker": "LW", "W.Gabriel": "W.G",
                   "M.Beasley": "Malik", "K.Ellis": "Keon", "A.Len": "Len", "L.Garza": "Garza"}   
    elif team == "MEM":
        players = {"J.Morant": "Ja","J.Jackson": "JJJ" , "T.Jones": "Tyus", "X.Tillman": "Xavier", "D.Bane": "bane", "D.Brooks": "Brooks", 
                   "S.Aldama": "Aldama", "D.Roddy": "Roddy", "L.Kennard": "Luke", "J.Konchar": "John", "K.Lofton": "KLJ", "K.Chandler": "K.C",
                   "P.Dozier": "PJD", "K.Ellis": "Keon", "A.Len": "Len", "L.Garza": "Garza"}
    elif team == "MIA":
        players = {"J.Butler": "Jimmy","B.Adebayo": "Bam" , "T.Herro": "Herro", "G.Vincent": "Gabe", "K.Love": "Love", "M.Strus": "Strus", 
                   "C.Martin": "Caleb", "K.Lowry": "Lowry", "H.Highsmith": "H.H", "O.Yurtseven": "Omer", "D.Robinson": "Duncan", "U.Haslem": "Haslem",
                   "V.Oladipo": "Victor", "J.Minott": "Josh", "N.Knight": "Knight", "L.Garza": "Garza"}        
    elif team == "MIL":
        players = {"G.Antetokounmpo": "Giannis","K.Middleton": "Khris" , "J.Holiday": "Jrue", "G.Allen": "Allen", "B.Lopez": "Lopez", "B.Portis": "Bobby", 
                   "P.Connaughton": "Pat", "J.Ingles": "Joe", "J.Carter": "Jevon", "W.Matthews": "Wesley", "M.Beauchamp": "MarJon", "T.Antetokounmpo": "Thana",
                   "J.Crowder": "Jae", "J.Minott": "Josh", "N.Knight": "Knight", "L.Garza": "Garza"}        
    elif team == "MIN":
        players = {"K.Towns": "KAT","A.Edwards": "Anto" , "R.Gobert": "Gobert", "J.McDaniels": "Jaden", "J.Nowell": "Nowell", 
                   "T.Prince": "Prince", "J.McLaughlin": "JMac", "K.Anderson": "SloMo", "B.Forbes": "Bryn", "A.Rivers": "Rivers", "N.Reid": "Reid",
                   "W.Moore": "WMJ","N.Knight": "Knight", "J.Minott": "Josh", "M.Conley": "Conley", "N.Alexander-Walker": "NAW", "W.Moore": "WMJ"}
    elif team == "NOP":
        players = {"Z.Williamson": "Zion","C.McCollum": "CJ" , "B.Ingram": "Ingram", "J.Valančiūnas": "Jonas", "T.Murphy": "Trey", "H.Jones": "Jones", 
                   "J.Richardson": "Josh", "N.Marshall": "Naji", "L.Nance": "Nance", "D.Daniels": "Dyson", "W.Hernangómez": "Willy", "G.Temple": "Temple",
                   "J.Hayes": "Hayes", "K.Lewis": "Lewis", "N.Knight": "Knight", "L.Garza": "Garza"}
    elif team == "NYK":
        players = {"J.Brunson": "Brunson","J.Rundle": "Rundle" , "R.Burrett": "RJB", "E.Fournier": "Evan", "M.Robinson": "M.R", "I.Hartenstein": "I.H", 
                   "I.Quickley": "IQ", "C.Reddish": "Reddish", "O.Toppin": "Obi", "D.Rose": "Rose", "Q.Grimes": "Grimes", "M.McBride": "Miles",
                   "S.Mykhailiuk": "Svi", "J.Sims": "Sims", "J.Hart": "Hart", "D.Jeffries": "DaQuan"}
    elif team == "OKC":
        players = {"J.Giddey": "Josh","J.Williams": "Jalen" , "S.Gilgeous-Alexander": "SGA", "L.Dort": "Dort", "J.Williams": "Jaylin", "I.Joe": "Joe", 
                   "L.Waters": "Lindy", "J.Robinson-Earl": "JRE", "A.Wiggins": "Aaron", "Q.Dieng": "Q.D", "T.Mann": "Mann", "A.Pokusevski": "A.P",
                   "D.Šarić": "Šarić", "O.Sarr": "Sarr", "A.Len": "Len", "L.Garza": "Garza"}    
    elif team == "ORL":
        players = {"F.Wagner": "Franz","P.Banchero": "Paolo" , "B.Bol": "BolBol", "C.Anthony": "Cole", "M.Fultz": "Fultz", "W.Carter": "WCJ", 
                   "M.Wagner": "Wagner", "J.Suggs": "Suggs", "C.Houstan": "Celeb", "G.Harris": "Harris", "A.Schofield": "Admiral", "K.Harris": "Kevon",
                   "C.Okeke": "Okeke", "G.Bitadze": "Goga", "J.Isaac": "Issac", "J.Scrubb": "Scrubb", "M.Carter-Williams": "MCW"}
    elif team == "PHI":
        players = {"J.Embiid": "Joel","T.Maxey": "Maxey" , "J.Harden": "Harden", "P.Tucker": "PJT", "T.Harris": "Harris", "D.Melton": "Melton", 
                   "S.Milton": "Shake", "G.Niang": "Niang", "J.McDaniels": "J-Mac", "D.Dedmon": "Dedmon", "P.Reed": "Reed", "F.Korkmaz": "F.K",
                   "J.Springer": "Jaden", "M.Harrell": "Harrell", "D.House": "DHJ", "L.Garza": "Garza"}
    elif team == "PHO":
        players = {"D.Booker": "Book","C.Paul": "CP3" , "D.Ayton": "Ayton", "K.Durant": "KD", "J.Okogie": "Josh", "T.Craig": "Craig", 
                   "B.Biyombo": "B.B", "T.Warren": "TJW", "T.Ross": "Ross", "C.Payne": "Payne", "J.Landale": "Jock", "L.Shamet": "Shamet",
                   "I.Wainright": "Ish", "D.Bazley": "Bazley", "D.Lee": "Lee", "L.Garza": "Garza"}   
    elif team == "POR":
        players = {"D.Lillard": "Dame", "J.Grant": "Grant","C.Reddish": "Cam" , "M.Thybulle": "Thy", "D.Eubanks": "Drew", "T.Watford": "T.W", 
                   "N.Little": "Little", "S.Sharpe": "Sharpe", "J.Walker": "J.W", "K.Johnson": "Keon", "K.Knox": "Knox", "M.Williams": "Mark",
                   "N.Reid": "Reid", "W.Moore": "WMJ", "J.Minott": "Josh", "N.Knight": "Knight", "L.Garza": "Garza"}
    elif team == "SAC":
        players = {"D.Fox": "Fox","D.Sabonis": "Doma" , "K.Huerter": "Kevin", "K.Murray": "Keegan", "D.Mitchell": "Davion", "M.Dellavedova": "M.Della", 
                   "T.Lyles": "Trey", "K.Edwards": "Kess", "M.Monk": "Monk", "R.Holmes": "R.H", "C.Metu": "Metu", "T.Davis": "Davis",
                   "P.Dozier": "PJD", "K.Ellis": "Keon", "A.Len": "Len", "L.Garza": "Garza"}
    elif team == "SAS":
        players = {"K.Johnson": "Keldon","T.Jones": "Tre" , "S.Mamukelashvili": "Sandro", "M.Branham": "Malaki", "K.Bates-Diop": "Keita", "D.Graham": "Graham", 
                   "B.Wesley": "Blake", "J.Champagnie": "Julian", "G.Dieng": "Dieng", "D.Barlow": "Barlow", "D.McDermott": "Doug", "D.Vassell": "Devin"
        }
    elif team == "TOR":
        players = {"P.Siakam": "Siakam","F.VanVleet": "Fred" , "J.Poeltl": "Jakob", "O.Anunoby": "OGA", "W.Barton": "Will", "C.Boucher": "Chris", 
                   "J.Dowtin": "Jeff", "C.Koloko": "Koloko", "M.Frynn": "Frynn", "P.Achiuwa": "P.A", "T.Young": "Young", "T.Davis": "Davis",
                   "P.Dozier": "PJD", "K.Ellis": "Keon", "A.Len": "Len", "L.Garza": "Garza"}
    elif team == "UTA":
        players = {"L.Markkanen": "Lauri","K.Olynyk": "Olynyk" , "W.Kessler": "Kessler", "T.Horton-Tucker": "THT", "J.Clarkson": "Clarkson", "R.Gay": "Gay", 
                   "O.Agbaji": "Achai", "C.Sexton": "Sexton", "S.Fontecchio": "Simone", "U.Azubuike": "Udoka", "K.Dunn": "Dunn", "J.Toscano-Anderson": "JTA",
                   "J.Juzang": "Juzang", "D.Jones": "DJones", "M.Porter": "Micah", "L.Šamanić": "Šamanić"}   
    elif team == "WAS":
        players = {".Fox": "Fox","D.Sabonis": "Doma" , "K.Huerter": "Kevin", "K.Murray": "Keegan", "D.Mitchell": "Davion", "M.Dellavedova": "M.Della", 
                   "T.Lyles": "Trey", "K.Edwards": "Kess", "M.Monk": "Monk", "R.Holmes": "R.H", "C.Metu": "Metu", "T.Davis": "Davis",
                   "P.Dozier": "PJD", "K.Ellis": "Keon", "A.Len": "Len", "L.Garza": "Garza"}
        
    
    return players 



# def _make_textfile(df, team, filename):
def _make_textfile(df, team, matchup, tag):
    players = _players_dict(team)
    df_pivot = df[df["ShotResult"]==1].pivot_table(index=["Assister", "Shooter", "eventTeam_abb"], values="play_id", aggfunc="count").reset_index()
    df_pivot2 = df[df["ShotResult"]==1].pivot_table(index=["Assister", "Shooter", "eventTeam_abb", "ShotResult", "ShotScore"], values="play_id", aggfunc="count").reset_index()
    df_pivot3 = df[df["ShotResult"]==1].pivot_table(index=["Shooter", "eventTeam_abb", "period", "ShotResult", "ShotScore"], values="play_id", aggfunc="count").reset_index()
    # print(team)
    
    aaa = df_pivot[(df_pivot["eventTeam_abb"]==team)]
    bbb = df_pivot2[(df_pivot2["eventTeam_abb"]==team)]
    ccc = df_pivot3[(df_pivot3["eventTeam_abb"]==team)]
    
    plusminus_table = _calc_plusminus(df, players, ishome=ishome)
    plusminus_table.to_csv("./TeamPBPdata/" + team + " PlusMinus 2022-2023.csv", index=False)
    plusminus_table["nicknames"] = plusminus_table["LineUps"].replace(players, regex=True)
    plusminus_table["text"] = plusminus_table["nicknames"].replace(",", "-", regex=True)
    
    aaa["Assister_nickname"] = aaa["Assister"].map(players)
    aaa["Shooter_nickname"] = aaa["Shooter"].map(players)
    aaa = aaa.replace(np.nan, "")
    
    bbb["Assister_nickname"] = bbb["Assister"].map(players)
    bbb["Shooter_nickname"] = bbb["Shooter"].map(players)
    bbb = bbb.replace(np.nan, "")
    
    ccc["Points"] = ccc["ShotScore"] * ccc["play_id"]
    ccc = ccc.groupby(["Shooter", "period"]).sum().reset_index()
    ccc["Shooter_nickname"] = ccc["Shooter"].map(players)
    
    
    
    datestr = date[2:4] + date[5:7] + date[8:10]
    
    # ディレクトリ作成
    date_dir = os.path.join(os.getcwd(), "Twitter", datestr)
    
    if os.path.exists(date_dir):
        pass
    else:
        os.mkdir(date_dir)


    
    filename1 = matchup + " " + datestr + " " + team + "1.txt"
    filename2 = matchup + " " + datestr + " " + team + "2.txt"
    filename3 = matchup + " " + datestr + " " + team + "3.txt"
    
    with open("./Twitter/" + datestr + "/" + filename1, mode="w") as f:
        # df["datetime"] = pd.to_datetime(df["datetime"])
        # print(date)
        
        f.write("▼" + df["awayTeam_abb"].unique()[0] + "@" + df["homeTeam_abb"].unique()[0] + " " + datestr + "\n")
        f.write(team + " TeamAssist:" + str(int(aaa[aaa["Assister"]!=""]["play_id"].sum())) + "\n")
        f.write("[Assister→Scorer]\n")
        for player, nickname in players.items():
            tmp = aaa[aaa["Assister"]==player].sort_values("play_id", ascending=False)
            
            if len(tmp)==0:
                pass
            else:
                f.write(nickname + "→")
                sample = ""
                for i, row in enumerate(tmp.to_dict(orient="records")):
                    if i == len(tmp)-1:
                        sample += row["Shooter_nickname"] + str(int(row["play_id"]))
                        f.write(sample)
                    else:
                        sample += row["Shooter_nickname"] + str(int(row["play_id"])) + "/"
                
                f.write("\n")
                
        f.write("\n")
        f.write(tag)
    
    
    with open("./Twitter/" + datestr + "/" + filename2, mode="w") as f:
        f.write("▼" + df["awayTeam_abb"].unique()[0] + "@" + df["homeTeam_abb"].unique()[0] + " " + datestr + "\n")
        f.write(team + " -FG Detail-\n")
        f.write("A:Assisted ua:unassist\n\n")
        f.write("[A2P/A3P/ua2P/ua3P]\n")
        for player, nickname in players.items():
            tmp = bbb[(bbb["Shooter"]==player)&(bbb["ShotScore"]>=2)].sort_values("play_id", ascending=False)
            
            if len(tmp)==0:
                pass
            else:
                f.write(nickname + ":")
            
                sample = ""

                sample += str(tmp[(tmp["Assister"]!="")&(tmp["ShotScore"]==2)]["play_id"].sum()) + "/"
                sample += str(tmp[(tmp["Assister"]!="")&(tmp["ShotScore"]==3)]["play_id"].sum()) + "/"
                sample += str(tmp[(tmp["Assister"]=="")&(tmp["ShotScore"]==2)]["play_id"].sum()) + "/"
                sample += str(tmp[(tmp["Assister"]=="")&(tmp["ShotScore"]==3)]["play_id"].sum())

                sample += "\n"

                f.write(sample)
        
        total = ""
        
        total += str(bbb[(bbb["Assister"]!="")&(bbb["ShotScore"]==2)]["play_id"].sum()) + "/"
        total += str(bbb[(bbb["Assister"]!="")&(bbb["ShotScore"]==3)]["play_id"].sum()) + "/"
        total += str(bbb[(bbb["Assister"]=="")&(bbb["ShotScore"]==2)&(bbb["ShotResult"]==1)]["play_id"].sum()) + "/"
        total += str(bbb[(bbb["Assister"]=="")&(bbb["ShotScore"]==3)&(bbb["ShotResult"]==1)]["play_id"].sum())
        
        f.write("total:" + total)
        f.write("\n\n")
        f.write(tag)
        
        
        
    with open("./Twitter/" + datestr + "/" + filename3, mode="w") as f:
    # with open("Plus Minus test.txt", mode="w") as f:
        f.write("▼" + df["awayTeam_abb"].unique()[0] + "@" + df["homeTeam_abb"].unique()[0] + " " + datestr + "\n")
        f.write(team + " -Lineups [+/-] -\n")
        f.write("Best3\n")
        
        for i in range(3):
            f.write(plusminus_table.nlargest(3, columns="Plus_Minus").iloc[i, -1])
            f.write(":+" + str(plusminus_table.nlargest(3, columns="Plus_Minus").iloc[i, 4]))
            f.write("\n")
            
        f.write("\n")
        f.write("Worst3\n")
        
        for i in range(3):
            f.write(plusminus_table.nsmallest(3, columns="Plus_Minus").iloc[i, -1])
            f.write(":" + str(plusminus_table.nsmallest(3, columns="Plus_Minus").iloc[i, 4]))
            f.write("\n")
        
        f.write("\n")
        f.write(tag)
    

def _make_bs(bs_url, homeTeam, awayTeam):
    bs = pd.DataFrame(columns=['game_id', 'teamName','playerName', 'MP', 
                           'FG', 'FGA', 'FG%', '3P', '3PA', '3P%', 'FT', 'FTA', 'FT%', 'ORB',
                           'DRB', 'TRB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS', '+/-'])

    bs_table = pd.io.html.read_html(bs_url)
    
    away = True
    for table in bs_table:
        # It throws an error at the 2nd if statement without the 1st if statement
        if table.columns.get_level_values(0)[1] == 'Advanced Box Score Stats': continue
        if table['Basic Box Score Stats'][-1:]['MP'].isna().max(): continue
        if int(table['Basic Box Score Stats']['MP'][-1:].max()) >= 240:
            teamStats = table['Basic Box Score Stats']
            teamStats['playerName'] = table['Unnamed: 0_level_0']
            teamStats['game_id'] = 1
            if away:
                teamStats['teamName'] = awayTeam
                away = False
            else:
                teamStats['teamName'] = homeTeam
            bs = pd.concat([bs, teamStats])

    lst = []
    j= 0
    for i, row in bs.iterrows():
        if row.playerName == 'Reserves':
            lst.append(0)
        elif row.playerName == 'Team Totals':
            lst.append(1)
        elif i == 0:
            lst.append(1)
        else:
            lst.append(lst[-1])
    bs['isStarter'] = lst

    #Cut values that do not include data on players
    bs = bs[(bs.playerName!='Reserves')&(bs.playerName!='Team Totals')]
    bs.drop(columns=['FG%', '3P%', 'FT%'], inplace=True)
    bs["shortName"] = [x[0][0] + ". " + x[1] if len(x)>=2 else x[0] for x in bs["playerName"].str.split(" ")]

    awayTeam_Minutes_table = pd.DataFrame(columns=['game_id', 'teamName','playerName'])
    homeTeam_Minutes_table = pd.DataFrame(columns=['game_id', 'teamName','playerName'])
    tmp = []
    tmp2 = []

    for i, table in enumerate(bs_table):
        # It throws an error at the 2nd if statement without the 1st if statement
        if table.columns.get_level_values(0)[1] == 'Advanced Box Score Stats': continue
        if (int(table['Basic Box Score Stats']['MP'][-1:].max()) == 60) | (int(table['Basic Box Score Stats']['MP'][-1:].max()) == 25):
            teamStats = table['Basic Box Score Stats']
            teamStats['playerName'] = table['Unnamed: 0_level_0']
            teamStats['game_id'] = 1

            if i < len(bs_table)/2:
                teamStats['teamName'] = awayTeam
                if awayTeam_Minutes_table.shape[0]==0:
                    awayTeam_Minutes_table = pd.concat([awayTeam_Minutes_table, teamStats])
                    awayTeam_Minutes_table.drop(awayTeam_Minutes_table.columns[4:], axis=1, inplace=True)
                else:
                    tmp.append(teamStats["MP"].values.tolist())
            else:
                teamStats['teamName'] = homeTeam
                if homeTeam_Minutes_table.shape[0]==0:
                    homeTeam_Minutes_table = pd.concat([homeTeam_Minutes_table, teamStats])
                    homeTeam_Minutes_table.drop(homeTeam_Minutes_table.columns[4:], axis=1, inplace=True)
                else:
                    tmp2.append(teamStats["MP"].values.tolist())

    for i, (tm, tm2) in enumerate(zip(tmp, tmp2)):
        awayTeam_Minutes_table.insert(awayTeam_Minutes_table.shape[-1], str(i+2) + "QMP", tm)
        homeTeam_Minutes_table.insert(homeTeam_Minutes_table.shape[-1], str(i+2) + "QMP", tm2)
        
    awayTeam_Minutes_table = awayTeam_Minutes_table.rename(columns={"MP": "1QMP"})
    homeTeam_Minutes_table = homeTeam_Minutes_table.rename(columns={"MP": "1QMP"})
    
    awayTeam_Minutes_table = awayTeam_Minutes_table.replace(np.nan, "00:00")
    homeTeam_Minutes_table = homeTeam_Minutes_table.replace(np.nan, "00:00")

    for col in awayTeam_Minutes_table.columns[3:]:
        awayTeam_Minutes_table[col] = [int(x[0])*60 + int(x[1]) if len(x)==2 else "".join(x) for x in awayTeam_Minutes_table[col].str.split(":")]
        homeTeam_Minutes_table[col] = [int(x[0])*60 + int(x[1]) if len(x)==2 else "".join(x) for x in homeTeam_Minutes_table[col].str.split(":")]

    awayTeam_Minutes_table["shortName"] = [x[0][0] + ". " + x[1] if len(x)>=2 else x[0] for x in awayTeam_Minutes_table["playerName"].str.split(" ")]
    homeTeam_Minutes_table["shortName"] = [x[0][0] + ". " + x[1] if len(x)>=2 else x[0] for x in homeTeam_Minutes_table["playerName"].str.split(" ")]
    
    return bs, awayTeam_Minutes_table, homeTeam_Minutes_table


def _make_player5(df, hometable, awaytable):
    for j in range(2):
        for k in df.index:            
            try:                
                if (df.loc[k, "MemberChange"].all() == 1)&(df.loc[k, "Time_Span_0"]==1):
                    if (df.loc[k, "Technical FT"]==1)&(df.loc[k, "MemberChange_+5"]==1)&(df.loc[k, "MemberIn"]!=""):                        
                        In = df.loc[k, "MemberIn"].split(",")
                        Out = df.loc[k, "MemberOut"].split(",")
                        dic = {out: inn for out, inn in zip(Out, In)}
                        
                        if j==0:
                            dc = {k: v for k, v in dic.items() if (k in awaytable["shortName"].values) & (v in awaytable["shortName"].values)} 
                            df.loc[k, ["Technical FT", "awayTeam_player5"]] = df.loc[k, ["Technical FT", "awayTeam_player5"]].replace(dc, regex=True)
                        else:
                            dc = {k: v for k, v in dic.items() if (k in hometable["shortName"].values) & (v in hometable["shortName"].values)}
                            df.loc[k, ["Technical FT", "homeTeam_player5"]] = df.loc[k, ["Technical FT", "homeTeam_player5"]].replace(dc, regex=True)
                    
                    elif (df.loc[k, "Foul after FT"]==1)&(df.loc[k, "MemberIn"]!=""):
                        In = df.loc[k, "MemberIn"].split(",")
                        Out = df.loc[k, "MemberOut"].split(",")
                        dic = {out: inn for out, inn in zip(Out, In)}
                        
                        if j==0:
                            dc = {k: v for k, v in dic.items() if (k in awaytable["shortName"].values) & (v in awaytable["shortName"].values)} 
                            df.loc[k, ["Foul after FT", "awayTeam_player5"]] = df.loc[k, ["Foul after FT", "awayTeam_player5"]].replace(dc, regex=True)
                        else:
                            dc = {k: v for k, v in dic.items() if (k in hometable["shortName"].values) & (v in hometable["shortName"].values)}
                            df.loc[k, ["Foul after FT", "homeTeam_player5"]] = df.loc[k, ["Foul after FT", "homeTeam_player5"]].replace(dc, regex=True)
                            
                        df.loc[k+1, ["Foul after FT"]] = df.loc[k, ["Foul after FT"]] 
                    
                    elif ((df.loc[k, "TO"]==1)|(df.loc[k, "TimeOut"]==1))&(df.loc[k, "MemberIn"]!=""):
                        In = df.loc[k, "MemberIn"].split(",")
                        Out = df.loc[k, "MemberOut"].split(",")
                        dic = {out: inn for out, inn in zip(Out, In)}
                        
                        if j==0:
                            dc = {k: v for k, v in dic.items() if (k in awaytable["shortName"].values) & (v in awaytable["shortName"].values)} 
                            df.loc[k:df.index.max(), "awayTeam_player5"] = df.loc[k:df.index.max(), "awayTeam_player5"].replace(dc, regex=True)
                        else:
                            dc = {k: v for k, v in dic.items() if (k in hometable["shortName"].values) & (v in hometable["shortName"].values)}
                            df.loc[k:df.index.max(), "homeTeam_player5"] = df.loc[k:df.index.max(), "homeTeam_player5"].replace(dc, regex=True)
                            
                        df.loc[k, ["MemberIn", "MemberOut"]] = ""
                        df.loc[k, "MemberChange"] = 0
                        
                    df.loc[k+1, ["MemberIn", "MemberOut"]] += "," + df.loc[k, ["MemberIn", "MemberOut"]]
                    df.loc[k+1, "MemberChange"] = df.loc[k, "MemberChange"]

                else:
                    if df.loc[k, "MemberIn"]=="":
                        pass
                    else:                            
                        In = df.loc[k, "MemberIn"].split(",")
                        Out = df.loc[k, "MemberOut"].split(",")
                        dic = {out: inn for out, inn in zip(Out, In)}
                                                    
                        if j==0:
                            dc = {k: v for k, v in dic.items() if (k in awaytable["shortName"].values) & (v in awaytable["shortName"].values)} 
                            df.loc[k:df.index.max(), "awayTeam_player5"] = df.loc[k:df.index.max(), "awayTeam_player5"].replace(dc, regex=True)
                        else:
                            dc = {k: v for k, v in dic.items() if (k in hometable["shortName"].values) & (v in hometable["shortName"].values)}                                
                            df.loc[k:df.index.max(), "homeTeam_player5"] = df.loc[k:df.index.max(), "homeTeam_player5"].replace(dc, regex=True)
            except KeyError:
                pass
    
    return df


def _make_lineups(df,awayTeam_Minutes_table, homeTeam_Minutes_table):
    homes = {} 
    aways = {}

    for i in range(1, 1+len(df.period.unique())):
        if i == 1:
            homes[i] = df.loc[0, "homeTeam_player5"]
            aways[i] = df.loc[0, "awayTeam_player5"]
        
        else:
            aaa = df[df["period"]==i]
            
            for j in range(2):
                ccc = aaa[(aaa["MemberChange"]==1)&(aaa["MemberChange_H"]==j)]
                starters = []
                memberin = []
                memberout = []

                for l in ccc.index:
                    memberin.append(ccc.loc[l, "MemberIn"])
                    memberout.append(ccc.loc[l, "MemberOut"])

                    if ccc.loc[l, "MemberOut"] not in memberin:
                        starters.append(ccc.loc[l, "MemberOut"])

                if len(set(starters))<5:                
                    if (j==0) & (i<5):
                        starters.extend(awayTeam_Minutes_table[awayTeam_Minutes_table[str(i) + "QMP"]==720]["shortName"].tolist())
                    elif (j==0) & (i>=5):
                        starters.extend(awayTeam_Minutes_table[awayTeam_Minutes_table[str(i) + "QMP"]==300]["shortName"].tolist())
                    elif (j==1) & (i<5):
                        starters.extend(homeTeam_Minutes_table[homeTeam_Minutes_table[str(i) + "QMP"]==720]["shortName"].tolist())
                    elif (j==1) & (i>=5):
                        starters.extend(homeTeam_Minutes_table[homeTeam_Minutes_table[str(i) + "QMP"]==300]["shortName"].tolist())
                        
                if len(set(starters))==5:
                    if j == 0:
                        aways[i] = ",".join(starters)
                    else:
                        homes[i] = ",".join(starters)
                else:
                    if j == 0:
                        aways[i] = df.loc[0, "awayTeam_player5"]
                    else:
                        homes[i] = df.loc[0, "homeTeam_player5"]

    tmp = pd.DataFrame(columns=df.columns)

    for i in range(1, 1+len(df.period.unique())):
        df.loc[df["period"]==i, "homeTeam_player5"] = homes[i]
        df.loc[df["period"]==i, "awayTeam_player5"] = aways[i]
        
        aaa = df[df["period"]==i]
        bbb = _make_player5(aaa, hometable=homeTeam_Minutes_table, awaytable=awayTeam_Minutes_table)
        tmp = pd.concat([tmp, bbb])

    return tmp



def _set(string):
    return ",".join(set(sorted(string.split(","))))



def _calc_plusminus(df, players, ishome=1):
    columns = 'homeTeam_player5' if ishome == 1 else 'awayTeam_player5'
    new_columns = "LineUps"
    
    df[new_columns] = [_set(x) for x in df[columns]]
    df[new_columns] = df[new_columns].replace(" ", "", regex=True)
    
    df["point_home"] = df["point_home"].replace(np.nan, 0)
    df["point_home"] = df["point_home"].replace("+", "")
    df["point_home"] = df["point_home"].astype(int)
    df["point_away"] = df["point_away"].replace(np.nan, 0)
    df["point_away"] = df["point_away"].replace("+", "")
    df["point_away"] = df["point_away"].astype(int)
    df["Time_Span"] = df["Time_Span"].astype(int)
    
    tmp = df.pivot_table(index=[new_columns], values=["point_home", "point_away", "Time_Span"], aggfunc="sum").reset_index()
    tmp["Plus_Minus"] = tmp["point_home"] - tmp["point_away"]
    
    if ishome == 0:
        tmp["Plus_Minus"] = tmp["Plus_Minus"] * -1
        
    for player, nickname in players.items():        
        tmp[nickname] = np.where(tmp[new_columns].str.contains(player), 1, 0)    
    
    # for col in tmp.columns[5:]:
    #     print(col + " : " + str(tmp[tmp[col]==1]["Plus_Minus"].sum()))
        
    tmp["nicknames"] = tmp[new_columns].replace(players, regex=True)
    tmp["text"] = tmp["nicknames"].replace(",", "-", regex=True)
    
    return tmp



def _lineups_graph(df, ishome=1):
    if ishome==1:
        team = df["homeTeam_abb"].all()
        column = "homeTeam_player5"
    else:
        team = df["awayTeam_abb"].all()
        column = "awayTeam_player5"
    
    players = _players_dict(team)
    time_list = [x*720 for x in range(len(df["period"].unique())+1)]
    
    temp = df[(df["MemberChange"]==1)|(df["periodTime"]==0)]
    temp[column + "_shift"] = temp[column].shift(-1)
    temp["MemberChange_Flag"] = np.where(temp[column]==temp[column + "_shift"], 0, 1)

    temp2 = temp[temp["MemberChange_Flag"]==1][["Time", column]].reset_index(drop=True)
    temp2 = temp2.merge(df[["Time", "homePoints", "awayPoints"]], on="Time")
    temp2["Time"] = [2880 - x for x in temp2["Time"]]
    temp2 = temp2.drop_duplicates(subset=["Time", column], keep="last")
    
    temp3 = temp2.sort_values("Time").reset_index(drop=True)
    temp4 = temp3.fillna(method="bfill", axis=0)
    
    temp4["TimeDiff"] = abs(temp4["Time"].diff().fillna(temp4["Time"][0]))
    temp4["LineUps"] = [_set(x) for x in temp4[column]]
    
    temp4["LineUps"] = temp4["LineUps"].replace(" ", "", regex=True)
    temp4["LineUps"] = temp4["LineUps"].replace(players, regex=True)
    
    if ishome==1:
        temp4["PlusMinus"] = temp4["homePoints"] - temp4["awayPoints"]
    else:
        temp4["PlusMinus"] = temp4["awayPoints"] - temp4["homePoints"]

    temp4["PlusMinus"] = temp4["PlusMinus"].diff().fillna(temp4["PlusMinus"][0])
    temp4["LeftTime"] = [max(temp4["Time"]) - x for x in temp4["Time"]]
    temp4["period"] = [int(x//720.1 + 1) for x in temp4["Time"]]
    temp4["Leftperiod"] = [max(temp4["period"]) - x for x in temp4["period"]]

    temp4["GameTime_"] = [str(int(x + y)) + "-" + str(x) for x, y in zip(temp4["LeftTime"], temp4["TimeDiff"])]

    temp4["Start"] = [str((int(x[0]) - y*720)//60) + ":" + str((int(x[0]) - y*720)%60)
                      for x, y in zip(temp4["GameTime_"].str.split("-"), temp4["Leftperiod"])]
    temp4["End"] = [str((int(x[1]) - y*720)//60) + ":" + str((int(x[1]) - y*720)%60)
                      for x, y in zip(temp4["GameTime_"].str.split("-"), temp4["Leftperiod"])]

    temp4["Start"] = [datetime.strptime(x, "%M:%S").strftime("%M:%S") for x in temp4["Start"]]
    temp4["End"] = [datetime.strptime(x, "%M:%S").strftime("%M:%S") for x in temp4["End"]]

    temp4["GameTime"] = [x + "-" + y for x, y in zip(temp4["Start"],temp4["End"])]

    temp4.insert(0, "Period", temp4["period"])
    temp4.insert(2, "PlayTime(s)", temp4["TimeDiff"].astype(int))
    temp4["Time"] = temp4["GameTime"]
    temp4[column] = temp4["LineUps"]
    temp4["PlusMinus"] = temp4["PlusMinus"].astype(int)

    temp4.drop(["TimeDiff", "LineUps", "LeftTime", "period", "Leftperiod", "GameTime_", "Start", "End", "GameTime"], axis=1, inplace=True)
    temp4 = temp4.rename(columns={column: "LineUps"})
    viz_df = temp4[["PlayTime(s)", "LineUps", "PlusMinus"]].set_index("LineUps")
    
    fig = _make_lineup_graph(viz_df, time_list, team)
    
    return fig, temp4


def _make_lineup_graph(df, time_list, team):
    n_rows, n_cols = len(df), 1
    positions = np.arange(n_cols)
    offsets = np.zeros(n_cols, dtype=df.values.dtype)
    
    res = df.assign(count=0).groupby(['LineUps'])['count'].count().reset_index()
    colors = plt.get_cmap("tab10")(np.linspace(0, 1, len(res))).tolist()
    res["colors"] = colors
    
    df = df.merge(res[["LineUps", "colors"]], on="LineUps", how="left").set_index("LineUps")
    df["PlusMinus"] = [str(x) if x < 0 else "+" + str(x) for x in df["PlusMinus"].astype(int)]

    fig, ax = plt.subplots(figsize=(15,1.5))
    ax.set_yticks(positions)
    ax.set_yticklabels([team])
    ax.set_xticks(time_list)
    xticklabels = [str(x) + "Q" for x in range(1, len(time_list))]
    xticklabels.append("End")
    ax.set_xticklabels(xticklabels)

    for i in range(len(df.index)):
        # 棒グラフを描画する。
        bar = ax.barh(positions, df.iloc[i, 0], left=offsets, color=df["colors"][i])
        offsets += df.iloc[i, 0]
        istext = 0

        # 棒グラフのラベルを描画する。
        for rect in bar:
            cx = rect.get_x() + rect.get_width() / 2
            cy = rect.get_y() + rect.get_height() / 2

            if (rect.get_width()>=100)&(istext==0):
                label = df.index[i].replace(",", "\n") 
                ax.text(cx, cy, label , color="k", ha="center", va="center", size=10)
                istext += 1
            else:
                istext -=1
                
            plusminus = df.iloc[i, 1]
            ax.text(cx, cy+0.5, plusminus , color="k", ha="center", va="center", size=10)    

            
    return fig



def _game_point_transition(df):
    df["PointDiff"] = (df["homePoints"] - df["awayPoints"]).astype(int)
    df["Point-Point"] = [str(x) + "-" + str(y) for x,y in zip(df["homePoints"], df["awayPoints"])]
    df["pTime"] = [str(x//60) + ":" + str(x%60).zfill(2) for x in df["periodTime"]]
    df["labelTime"] = [str(x) + "Q - " + y for x, y in zip(df["period"], df["pTime"])]
    
    tmp = df[["Time", "PointDiff", "Point-Point", "pTime", "labelTime"]]
    tmp["Time"] = [max(tmp["Time"]) - x for x in tmp["Time"]]
    
    
    fig = _make_transition_graph(tmp)
    
    return fig, tmp

def map_color(value):
    if value > 0:
        return 'blue'
    elif value < 0:
        return 'red'
    else:
        return 'black'  # 0の場合は黒


def _make_transition_graph(df):

    fig = go.Figure()
    
    # 各データポイントの色をマッピング
    colors = [map_color(val) for val in df["PointDiff"]]
    
    label = df["labelTime"] + "<br>" + df["Point-Point"]
    
    fig.add_trace(go.Scatter(x=df["Time"], y=df["PointDiff"], fill='tozeroy', hoverinfo="text", text=label,marker=dict(color=colors)))

    fig.update_layout(
        title="Point Difference Over Time",
        xaxis=dict(
            title="Time",
            tickvals=[0, 720, 1440, 2160, 2880],
            ticktext=["1Q", "2Q", "3Q", "4Q", "End"]
        ),
        yaxis=dict(title="Point Difference"),
        width=800,
        height=400
    )

    # fig.show()
    
    return fig

def _game_point_transition(df):
    df["PointDiff"] = (df["homePoints"] - df["awayPoints"]).astype(int)
    df["Point-Point"] = [str(x) + "-" + str(y) for x,y in zip(df["homePoints"], df["awayPoints"])]
    df["pTime"] = [str(x//60) + ":" + str(x%60).zfill(2) for x in df["periodTime"]]
    df["labelTime"] = [str(x) + "Q - " + y for x, y in zip(df["period"], df["pTime"])]
    
    tmp = df[["Time", "PointDiff", "Point-Point", "pTime", "labelTime"]]
    tmp["Time"] = [max(tmp["Time"]) - x for x in tmp["Time"]]
    
    
    fig = _make_transition_graph(tmp)
    
    return fig, tmp

def map_color(value):
    if value > 0:
        return 'blue'
    elif value < 0:
        return 'red'
    else:
        return 'black'  # 0の場合は黒


def _make_transition_graph(df):

    fig = go.Figure()
    
    # 各データポイントの色をマッピング
    colors = [map_color(val) for val in df["PointDiff"]]
    
    label = df["labelTime"] + "<br>" + df["Point-Point"]
    
    fig.add_trace(go.Scatter(x=df["Time"], y=df["PointDiff"], fill='tozeroy', hoverinfo="text", text=label,marker=dict(color=colors)))

    fig.update_layout(
        title="Point Difference Over Time",
        xaxis=dict(
            title="Time",
            tickvals=[0, 720, 1440, 2160, 2880],
            ticktext=["1Q", "2Q", "3Q", "4Q", "End"]
        ),
        yaxis=dict(title="Point Difference"),
        width=800,
        height=400
    )

    # fig.show()
    
    return fig



def main():
    st.set_page_config(
        page_title="GameSummary & LineUp PlusMinus",
        page_icon="🧊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    st.title("GameSummary & LineUp PlusMinus")
    
    global date
    global ishome
    
#     parser = argparse.ArgumentParser()
#     parser.add_argument('-d', '--date', type=str, default=False, help='ユーザー名を入力してください')
#     args = parser.parse_args()
    
    
#     if args.date == False:
#         date = (datetime.today() - timedelta(2)).strftime("%Y-%m-%d")
#     else:
#         date = args.date
    
    games = pd.read_csv("data/games2023-2024.csv")
    
    today = (datetime.today() - timedelta(2)).strftime("%Y-%m-%d")
    
    date_list = sorted(games[games["datetime"]<=today].datetime.unique(), reverse=True)
    
    date = st.sidebar.selectbox(
        "選択してください",
        date_list
    )
    
    # print(date)
        
    # teams = {"GSW": "#DubNation", "BRK": "#NetsWorld", "DEN": "#MileHighBasketball", "MIN": "#RaisedByWolves", "ATL": "#TrueToAtlanta", "DET": "#Pistons",
    #          "BOS": "#BleedGreen", "CLE": "#LetEmKnow", "POR": "#RipCity", "MIA": "#HeatCulture", "DAL": "#MFFL", "LAL": "#LakeShow", "MIL": "#FearTheDeer",
    #          "MEM": "#BigMemphis", "LAC": "#ClipperNation", "PHO": "#WeAreTheValley", "OKC": "#ThunderUp", "SAC": "#SacramentoProud", "NYK": "#NewYorkForever", 
    #          "PHI": "#BrotherlyLove"}
    # # teams = {"GSW": "#DubNation", "BRK": "#NetsWorld", "DEN": "#MileHighBasketball", "POR": "#RipCity"}
    # # teams = {"CLE": "#LetEmKnow"}
    # teams = {"GSW": "#DubNation", "MIA": "#HeatCulture"}
    
    # for team, tag in teams.items():
    
    
    # games = pd.read_csv("data/games2023-2024.csv")
    matchup = games[games["datetime"]==date].reset_index(drop=True)
    matchup["Date-MatchUp"] = matchup["datetime"] + " " + matchup["MatchUp"]
    matchup_list = matchup["Date-MatchUp"].tolist()
    
    game = st.sidebar.selectbox(
        "選択してください",
        matchup_list
    )
    
    select_game = matchup[matchup["Date-MatchUp"]==game]["MatchUp"].iloc[-1]
    
    game_id, pbp_url, bs_url = _get_games(select_game, date)
        
    if type(games)==pd.core.frame.DataFrame:
        # if matchup[:3] == team:
        #     ishome = 0
        # elif matchup[-3:] == team:
        #     ishome = 1
        
        df = _pbp_scrape(pbp_url)
        df["game_id"] = game_id
        df = df.merge(games[["awayTeam", "homeTeam", "game_id", "datetime"]], on="game_id")        
        df = _pbp_cleaning(df)
        
        homeTeam = df["homeTeam"].iloc[-1]
        awayTeam = df["awayTeam"].iloc[-1]
        
        bs, awayTeam_Minutes_table, homeTeam_Minutes_table = _make_bs(bs_url, homeTeam=homeTeam, awayTeam=awayTeam)
        
        df["homeTeam_player5"] = ",".join(bs[(bs["isStarter"]==1)&(bs["teamName"]==homeTeam)]["shortName"].values.tolist())
        df["awayTeam_player5"] = ",".join(bs[(bs["isStarter"]==1)&(bs["teamName"]==awayTeam)]["shortName"].values.tolist())
        
        df = _make_lineups(df, awayTeam_Minutes_table, homeTeam_Minutes_table)
        
        # plusminus_table = _calc_plusminus(df, players, ishome=ishome)
        
        # _make_textfile(df, team, matchup, tag)
        
        df.drop(['ShotType', 'ShotClass',
                'ShotScore', 'eventTeam_abb', 'Assister', 'Shooter', 'ShotResult', 'play_id',
                'left_period', 'Time_shift', 'Time_Span', 'Time_Span_0',
                'MemberChange_shift_1', 'MemberChange_shift_2',
                'MemberChange_shift_3', 'MemberChange_shift_4', 'MemberChange_shift_5',
                'MemberChange_+5', 'MemberChange_H', 'MemberChangeEvent', 'MemberIn',
                'MemberOut', 'delay of game', 'Technical foul', 'DOGorTECH',
                'Technical FT', 'event', 'event_shift+1', 'event_shift-1',
                'LFoul after DRB', 'LFoul after DRB_shift', 'Foul after FT', 'FT',
                'FT_shift+1', 'FT_shift-1', 'FT_shift+-1', 'TO', 'TimeOut'], axis=1, inplace=True)
            
        # teamdir = "./TeamPBPdata/" + team
        
        
        
        # if os.path.exists(teamdir):
        #     pass
        # else:
        #     os.mkdir(teamdir)
        
        # df.to_csv("./TeamPBPdata/" + team + "/" + date + " " + matchup + " " + "pbp.csv", index=False)
        # awayTeam_Minutes_table.to_csv("./TeamPBPdata/" + team + "/" + date + " " + matchup + " " + "awayTeam_Minutes_table.csv", index=False)
        # homeTeam_Minutes_table.to_csv("./TeamPBPdata/" + team + "/" + date + " " + matchup + " " + "homeTeam_Minutes_table.csv", index=False)
        # bs.to_csv("./TeamPBPdata/" + team + "/" + date + " " + matchup + " " + "boxscore.csv", index=False)
        
        # df.to_csv("./TeamPBPdata/" + team + "/" + date + " " + matchup + " " + "pbp.csv", index=False)
        # awayTeam_Minutes_table.to_csv("./TeamPBPdata/" + team + "/" + date + " " + matchup + " " + "awayTeam_Minutes_table.csv", index=False)
        # homeTeam_Minutes_table.to_csv("./TeamPBPdata/" + team + "/" + date + " " + matchup + " " + "homeTeam_Minutes_table.csv", index=False)
        # bs.to_csv("./TeamPBPdata/" + team + "/" + date + " " + matchup + " " + "boxscore.csv", index=False)
        
        # time.sleep(1)
        
    else:
        pass
        

    
    
    
    selectgame = matchup[matchup['Date-MatchUp']==game]
    selectteam = matchup[matchup['Date-MatchUp']==game]["awayTeam_abb"].iloc[-1]
    select_matchup = selectgame['Date-MatchUp'].iloc[-1]
    
    # print(date)
    # print(os.getcwd())
    
    # pbpfile = "./TeamPBPdata/" + selectteam + "/" + select_matchup + " pbp.csv"
    
    # print(pbpfile)    
    
    # pbp0 = pd.read_csv(pbpfile)
    fig1, df1 = _lineups_graph(df=df, ishome=1)
    st.pyplot(fig1)
    fig2, df2 = _game_point_transition(df=df)
    st.plotly_chart(fig2, use_container_width=True)
    fig3, df3 = _lineups_graph(df=df, ishome=0)
    st.pyplot(fig3)
    
    st.header(selectgame["homeTeam"].iloc[-1])
    st.dataframe(df1)

    st.header(selectgame["awayTeam"].iloc[-1])
    st.dataframe(df3)
    
    
if __name__ == "__main__":
    main()
