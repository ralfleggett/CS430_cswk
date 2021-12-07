import json
import time

from HLTV import HLTV

MAJOR_EVENT_ID = 4866

def write_dict(dict_to_write, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(dict_to_write, f, ensure_ascii=False, indent=4)

def get_major_teams(hltv):
    return hltv.get_event_teams(MAJOR_EVENT_ID, "pgl-major-stockholm-2021")

def get_major_players(hltv, team_dict):
    players = {}
    for team_name, team_id in team_dict.items():
        print(team_name, team_id)
        player_dict = hltv.get_event_team_players(team_id, team_name, MAJOR_EVENT_ID)
        players.update(player_dict)
        for player_name, player_id in player_dict.items():
            print(player_name, player_id)
        print("--------------")
    return players

def main():
    hltv = HLTV("hltv.org")
    team_dict = get_major_teams(hltv)
    player_dict = get_major_players(hltv, team_dict)

    write_dict(team_dict, "teams.json")
    write_dict(player_dict, "players.json")
    

if __name__ == "__main__":
    main()