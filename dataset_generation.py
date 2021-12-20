import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import re

from datetime import datetime

from main import read_json

def round_prediction_generator(event_dict, match_dict, map_dict, team_dict):
    """
    Create train and test sets of
    (map, ct_team_name, t_team_name, ct_buy, t_buy, round_type, round_winner)
    round_winner == 0 if ct win else 1
    """
    test_maps = [map_id for match_id in event_dict["4866"]["match_ids"] for map_id in match_dict[match_id]["map_ids"]]
    train_maps = [map_id for map_id in map_dict if map_id not in test_maps]

    train_dict = _round_prediction_generator(train_maps, map_dict, team_dict)
    test_dict = _round_prediction_generator(test_maps, map_dict, team_dict)

    columns = ["map", "ct_team_name", "t_team_name", "ct_buy", "t_buy", "round_type", "round_winner"]
    train = pd.DataFrame.from_dict(train_dict, orient="index", columns=columns)
    test = pd.DataFrame.from_dict(test_dict, orient="index", columns=columns)

    train.to_csv("round_prediction_train.csv", index=False)
    test.to_csv("round_prediction_test.csv", index=False)

def _round_prediction_generator(map_ids, map_dict, team_dict):
    output = {}
    for id in map_ids:
        if id == "113205":
            # map without econ stats
            continue
        for i, round in enumerate(map_dict[id]["rounds"]):
            row = []
            row.append(map_dict[id]["map_name"])
            t1_id = map_dict[id]["team1_id"]
            t2_id = map_dict[id]["team2_id"]
            ct_start_team = map_dict[id]["ct_start_team"]
            if i < 15:
                ct_team = t1_id if ct_start_team == t1_id else t2_id
                t_team = t2_id if ct_start_team == t1_id else t1_id
            else:
                ct_team = t2_id if ct_start_team == t1_id else t1_id
                t_team = t1_id if ct_start_team == t1_id else t2_id
            row.append(team_dict[ct_team]["name"].replace(" ", "_"))
            row.append(team_dict[t_team]["name"].replace(" ", "_"))
            t1_buy = round["team1_buy"]
            t2_buy = round["team2_buy"]
            row.append(t1_buy if ct_team == t1_id else t2_buy)
            row.append(t2_buy if ct_team == t1_id else t1_buy)
            row.append(round["round_type"])
            row.append(0 if round["round_winner"] == ct_team else 1)
            output[f"{id}-round-{i}"] = row
    return output

def main():
    team_dict = read_json("team.json")
    player_dict = read_json("player.json")
    event_dict = read_json("event.json")
    match_dict = read_json("match.json")
    map_dict = read_json("map.json")
    map_player_dict = read_json("map_player.json", is_tuple_key=True)

    # round_prediction_generator(event_dict, match_dict, map_dict, team_dict)

    # Print stuff so we get the .arff nominal attribute specifications right
    # print(set([map_dict[map]["map_name"] for map in map_dict]))
    # print([team_dict[team]["name"] for team in team_dict])
    # print(set([round["round_type"] for map in map_dict for round in map_dict[map]["rounds"]]))

if __name__ == "__main__":
    main()