import collections
import json

from datetime import date
from re import match
from tqdm import tqdm

from HLTV import HLTV

MAJOR_EVENT_ID = 4866
MAJOR_END_DATE = date(2021, 11, 7)

def write_dict(dict_to_write, filename):
    """
    Writes a dictionary to the filename
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(dict_to_write, f, ensure_ascii=False, indent=4)

def read_json(filename):
    """
    Reads a json file into a dictionary
    """
    with open(filename) as handle:
        dictdump = json.loads(handle.read())
    return dictdump

def get_major_teams(hltv):
    """
    Queries HLTV for teams that played in final 16 of the 2021 PGL major
    """
    return hltv.get_event_teams(MAJOR_EVENT_ID, "pgl-major-stockholm-2021")

def get_major_players(hltv, team_dict):
    """ 
    Queries HLTV for players in teams in team_dict 
    """
    players = {}
    for team_id, team_name in tqdm(team_dict.items(), unit="team"):
        player_dict = hltv.get_event_team_players(team_id, team_name, MAJOR_EVENT_ID)
        team_dict[team_id].update({"players": [id for id in player_dict]})
        players.update(player_dict)
    return players

def get_map_ids(hltv, team_dict, latest_date=None, min_players=5):
    """
    Gets all map ids between teams in team_dict where the players in the 
    map were exactly the players specified in team_dict. Ignores maps
    after latest_date if not None
    Returns:
        dictionary {map_id: [team1_id, team2_id]}
    """
    team_ids = list(team_dict.keys())
    map_ids = {}            # IDs that have appeared at least once
    confirmed_map_ids = {}  # IDs which have appeared for both teams

    for team in tqdm(team_dict, unit="team"):
        ids = hltv.get_map_ids(
            team_dict[team]["players"], 
            team, 
            team_ids,
            latest_date=latest_date,
            min_players=min_players)
        for id in ids:
            if id not in map_ids:
                map_ids.update({id: ids[id]})
            else:
                confirmed_map_ids.update({id: ids[id]})

    return confirmed_map_ids

def main():
    hltv = HLTV("hltv.org")

    # team_dict = get_major_teams(hltv)
    # player_dict = get_major_players(hltv, team_dict)
    # map_ids = get_map_ids(hltv, team_dict, latest_date=MAJOR_END_DATE, min_players=4)
    # matches_dict, map_pick_dict, events_dict = hltv.get_match_ids(maps_dict, team_dict)
    # write_dict(team_dict, "teams.json")
    # write_dict(player_dict, "players.json")
    # write_dict(map_ids, "maps_4_players.json")
    # write_dict(matches_dict, "matches.json")
    # write_dict(map_pick_dict, "map_picks.json")
    # write_dict(events_dict, "events.json")

    team_dict = read_json("teams.json")
    player_dict = read_json("players.json")
    maps_dict = read_json("maps.json")
    matches_dict = read_json("matches.json")
    map_picks_dict = read_json("map_picks.json")
    events_dict = read_json("events.json")

    


  
if __name__ == "__main__":
    main()