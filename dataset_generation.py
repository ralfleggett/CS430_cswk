import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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

    columns = ["map", "ct_team_name", "t_team_name", "ct_buy", "t_buy", "round_winner"]
    train = pd.DataFrame.from_dict(train_dict, orient="index", columns=columns)
    test = pd.DataFrame.from_dict(test_dict, orient="index", columns=columns)

    train.to_csv("round_prediction_no_round_type_train.csv", index=False)
    test.to_csv("round_prediction_no_round_type_test.csv", index=False)

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
            # row.append(round["round_type"])
            row.append(0 if round["round_winner"] == ct_team else 1)
            output[f"{id}-round-{i}"] = row
    return output

def rating_prediction_generator(event_dict, match_dict, map_dict, map_player_dict, player_dict):
    test_maps = [map_id for match_id in event_dict["4866"]["match_ids"] for map_id in match_dict[match_id]["map_ids"]]
    train_maps = [map_id for map_id in map_dict if map_id not in test_maps]

    train_dict = _rating_prediction_generator(train_maps, map_player_dict, player_dict)
    test_dict = _rating_prediction_generator(test_maps, map_player_dict, player_dict)

    columns = ["map_id", "player_id", "player_name", "kills", "headshots", 
        "assists", "flash_assists", "deaths", "kast", "adr", "first_kills", 
        "first_deaths", "rating"]
    train = pd.DataFrame.from_dict(train_dict, orient="index", columns=columns)
    test = pd.DataFrame.from_dict(test_dict, orient="index", columns=columns)

    train.to_csv("map_player_train.csv", index=False)
    test.to_csv("map_player_test.csv", index=False)

def _rating_prediction_generator(map_ids, map_player_dict, player_dict):
    output = {}
    for (map, player), mp_dict in map_player_dict.items():
        if map not in map_ids:
            continue
        row = []
        row.append(map)
        row.append(player)
        row.append(player_dict[player]["name"])
        row.extend(list(mp_dict.values()))
        output[f"{map}, {player}"] = row
    return output

def map_prediction_simple_generator(event_dict, match_dict, map_dict, team_dict):
    test_maps = [map_id for match_id in event_dict["4866"]["match_ids"] for map_id in match_dict[match_id]["map_ids"]]
    train_maps = [map_id for map_id in map_dict if map_id not in test_maps]

    train_dict = _map_prediction_simple_generator(train_maps, map_dict, team_dict)
    test_dict = _map_prediction_simple_generator(test_maps, map_dict, team_dict)

    columns = ["map_name", "map_picked_by_team1", "team1_started_ct", 
        "team1_name", "team1_rating", "team1_first_kill_win", "team1_clutches", 
        "team1_buy_vs_buy", "team1_buy_vs_eco", "team1_eco_vs_buy", "team1_eco_vs_eco", 
        "team2_name", "team2_rating", "team2_first_kill_win", "team2_clutches", 
        "team2_buy_vs_buy", "team2_buy_vs_eco", "team2_eco_vs_buy", "team2_eco_vs_eco",
        "map_winner"]
    train = pd.DataFrame.from_dict(train_dict, orient="index", columns=columns)
    test = pd.DataFrame.from_dict(test_dict, orient="index", columns=columns)

    train.to_csv("map_prediction_train.csv", index=False)
    test.to_csv("map_prediction_test.csv", index=False)

def _map_prediction_simple_generator(map_ids, map_dict, team_dict):
    output = {}
    for map in map_dict:
        if map not in map_ids or "team1_buy" not in map_dict[map]["rounds"][0]:
            continue
        round_categories = [0, 0, 0, 0]
        for round in map_dict[map]["rounds"]:
            t1_buy = round["team1_buy_type"] == "full_buy" or round["team1_buy_type"] == "semi_buy"
            t2_buy = round["team2_buy_type"] == "full_buy" or round["team2_buy_type"] == "semi_buy"
            if t1_buy and not t2_buy:
                round_categories[0] += 1
            elif not t1_buy and t2_buy:
                round_categories[1] += 1
            elif t1_buy and t2_buy:
                round_categories[2] += 1
            elif not t1_buy and not t2_buy:
                round_categories[3] += 1
        total_rounds = float(len(map_dict[map]["rounds"]))
        row = []
        row.append(map_dict[map]["map_name"])
        row.append(map_dict[map]["map_picked_by"] == map_dict[map][f"team1_id"])
        row.append(map_dict[map]["ct_start_team"] == map_dict[map][f"team1_id"])
        for i in range(2):
            row.append(team_dict[map_dict[map][f"team{i+1}_id"]]["name"].replace(" ", "_"))
            row.append(float(map_dict[map]["team_rating"][i]))
            fks = map_dict[map]["first_kills"]
            row.append(float(fks[i]) / (int(fks[0]) + int(fks[1])))
            row.append(int(map_dict[map]["clutches"][i]))
            row.append(round_categories[2] / total_rounds)
            row.append(round_categories[i] / total_rounds)
            row.append(round_categories[(i+1) % 2] / total_rounds)
            row.append(round_categories[3] / total_rounds)
        row.append(0 if int(map_dict[map]["score"][0]) > int(map_dict[map]["score"][1]) else 1)
        output[map] = row
    return output

def map_prediction_generator(event_dict, match_dict, map_dict, team_dict):
    test_maps = [map_id for match_id in event_dict["4866"]["match_ids"] for map_id in match_dict[match_id]["map_ids"]]
    train_maps = [map_id for map_id in map_dict if map_id not in test_maps]
    test_maps = chrono_order_maps(test_maps, map_dict)
    train_maps = chrono_order_maps(train_maps, map_dict)

    tracking_dict = {}
    for team in team_dict:
        team_tracking_dict = {
            "counter": 0,
            "sum_rating": 0.,
            "wins": 0.,
            "sum_round_diff": 0,
            "sum_opponent_rating": 0.,
            "sum_fk_success": 0.,
            "sum_fk_diff": 0
        }
        for m in ["Inferno", "Overpass", "Vertigo", "Dust2", "Mirage", "Nuke", "Train", "Ancient"]:
            team_tracking_dict.update({
                m: {
                    "counter": 0,
                    "sum_rating": 0.,
                    "wins": 0.,
                    "sum_round_diff": 0,
                    "sum_opponent_rating": 0.,
                    "sum_fk_success": 0.,
                    "sum_fk_diff": 0
                }
            })
        tracking_dict[team_dict[team]["name"].replace(" ", "_")] = team_tracking_dict

    train_dict, tracking_dict = _map_prediction_generator(train_maps, tracking_dict, map_dict, team_dict)
    test_dict, _ = _map_prediction_generator(test_maps, tracking_dict, map_dict, team_dict)

    cols = [
        "map_name", "picked_by_t1", "t1_starts_ct",
        "t1_name", "t1_counter", "t1_av_rating", "t1_win_proportion", "t1_av_round_diff",
        "t1_av_opponent_rating", "t1_av_fk_success", "t1_av_fk_diff",
        "t1_map_counter", "t1_map_av_rating", "t1_map_win_proportion", "t1_map_av_round_diff",
        "t1_map_av_opponent_rating", "t1_map_av_fk_success", "t1_map_av_fk_diff",
        "t2_name", "t2_counter", "t2_av_rating", "t2_win_proportion", "t2_av_round_diff",
        "t2_av_opponent_rating", "t2_av_fk_success", "t2_av_fk_diff",
        "t2_map_counter", "t2_map_av_rating", "t2_map_win_proportion", "t2_map_av_round_diff",
        "t2_map_av_opponent_rating", "t2_map_av_fk_success", "t2_map_av_fk_diff",
        "winner"
    ]

    train = pd.DataFrame.from_dict(train_dict, orient="index", columns=cols)
    test = pd.DataFrame.from_dict(test_dict, orient="index", columns=cols)

    train.to_csv("map_prediction_train.csv", index=False)
    test.to_csv("map_prediction_test.csv", index=False)
    

def chrono_order_maps(map_ids, map_dict):
    # Chronologically order map_ids
    map_date_list = []
    for map in map_ids:
        dt = datetime.strptime(map_dict[map]["date"], "%Y-%m-%d %H:%M")
        map_date_list.append((map, dt))
    map_date_list.sort(key=lambda x: x[1])
    return [x[0] for x in map_date_list]

def _map_prediction_generator(map_ids, tracking_dict, map_dict, team_dict):
    output = {}
    for map in map_ids:
        map_name = map_dict[map]["map_name"]
        t1_name = team_dict[map_dict[map]["team1_id"]]["name"].replace(" ", "_")
        t2_name = team_dict[map_dict[map]["team2_id"]]["name"].replace(" ", "_")
        t1 = tracking_dict[t1_name]
        t2 = tracking_dict[t2_name]
        
        # Add to output
        with np.errstate(divide='ignore', invalid='ignore'):
            row = np.array([
                np.true_divide(t1["sum_rating"], float(t1["counter"])),
                np.true_divide(t1["wins"], float(t1["counter"])),
                np.true_divide(t1["sum_round_diff"], float(t1["counter"])),
                np.true_divide(t1["sum_opponent_rating"], float(t1["counter"])),
                np.true_divide(t1["sum_fk_success"], float(t1["counter"])),
                np.true_divide(t1["sum_fk_diff"], float(t1["counter"])),
                np.true_divide(t1[map_name]["sum_rating"], float(t1[map_name]["counter"])),
                np.true_divide(t1[map_name]["wins"], float(t1[map_name]["counter"])),
                np.true_divide(t1[map_name]["sum_round_diff"], float(t1[map_name]["counter"])),
                np.true_divide(t1[map_name]["sum_opponent_rating"], float(t1[map_name]["counter"])),
                np.true_divide(t1[map_name]["sum_fk_success"], float(t1[map_name]["counter"])),
                np.true_divide(t1[map_name]["sum_fk_diff"], float(t1[map_name]["counter"])),
                np.true_divide(t2["sum_rating"], float(t2["counter"])),
                np.true_divide(t2["wins"], float(t2["counter"])),
                np.true_divide(t2["sum_round_diff"], float(t2["counter"])),
                np.true_divide(t2["sum_opponent_rating"], float(t2["counter"])),
                np.true_divide(t2["sum_fk_success"], float(t2["counter"])),
                np.true_divide(t2["sum_fk_diff"], float(t2["counter"])),
                np.true_divide(t2[map_name]["sum_rating"], float(t2[map_name]["counter"])),
                np.true_divide(t2[map_name]["wins"], float(t2[map_name]["counter"])),
                np.true_divide(t2[map_name]["sum_round_diff"], float(t2[map_name]["counter"])),
                np.true_divide(t2[map_name]["sum_opponent_rating"], float(t2[map_name]["counter"])),
                np.true_divide(t2[map_name]["sum_fk_success"], float(t2[map_name]["counter"])),
                np.true_divide(t2[map_name]["sum_fk_diff"], float(t2[map_name]["counter"]))
            ])
            row[row == np.inf] = 0
            row = np.nan_to_num(row)
            row = row.tolist()
        row.insert(0, map_name)
        if map_dict[map]["map_picked_by"] == map_dict[map]["team1_id"]:
            picked_by = "t1"
        elif map_dict[map]["map_picked_by"] == map_dict[map]["team2_id"]:
            picked_by = "t2"
        else:
            picked_by = "decider"
        row.insert(1, picked_by)
        row.insert(2, map_dict[map]["ct_start_team"] == map_dict[map]["team1_id"])
        row.insert(3, t1_name)
        row.insert(4, t1["counter"])
        row.insert(11, t1[map_name]["counter"])
        row.insert(18, t2_name)
        row.insert(19, t2["counter"])
        row.insert(26, t2[map_name]["counter"])
        row.append("t1" if int(map_dict[map]["score"][0]) > int(map_dict[map]["score"][1]) else "t2")
        output[map] = row

        # Update tracking_dict
        score = (int(map_dict[map]["score"][0]), int(map_dict[map]["score"][1]))
        rating = (float(map_dict[map]["team_rating"][0]), float(map_dict[map]["team_rating"][1]))
        fk = (int(map_dict[map]["first_kills"][0]), int(map_dict[map]["first_kills"][1]))

        t1["counter"] += 1
        t1["sum_rating"] += rating[0]
        t1["wins"] += (1 if score[0] > score[1] else 0)
        t1["sum_round_diff"] += (score[0] - score[1])
        t1["sum_opponent_rating"] += rating[1]
        t1["sum_fk_success"] += (fk[0] / float(fk[0] + fk[1]))
        t1["sum_fk_diff"] += (fk[0] - fk[1])
        t1[map_name]["counter"] += 1
        t1[map_name]["sum_rating"] += rating[0]
        t1[map_name]["wins"] += (1 if score[0] > score[1] else 0)
        t1[map_name]["sum_round_diff"] += (score[0] - score[1])
        t1[map_name]["sum_opponent_rating"] += rating[1]
        t1[map_name]["sum_fk_success"] += (fk[0] / float(fk[0] + fk[1]))
        t1[map_name]["sum_fk_diff"] += (fk[0] - fk[1])
        t2["counter"] += 1
        t2["sum_rating"] += rating[1]
        t2["wins"] += (0 if score[0] > score[1] else 1)
        t2["sum_round_diff"] += (score[1] - score[0])
        t2["sum_opponent_rating"] += rating[0]
        t2["sum_fk_success"] += (fk[1] / float(fk[0] + fk[1]))
        t2["sum_fk_diff"] += (fk[1] - fk[0])
        t2[map_name]["counter"] += 1
        t2[map_name]["sum_rating"] += rating[1]
        t2[map_name]["wins"] += (0 if score[0] > score[1] else 1)
        t2[map_name]["sum_round_diff"] += (score[1] - score[0])
        t2[map_name]["sum_opponent_rating"] += rating[0]
        t2[map_name]["sum_fk_success"] += (fk[1] / float(fk[0] + fk[1]))
        t2[map_name]["sum_fk_diff"] += (fk[1] - fk[0])
    
    return output, tracking_dict

def main():
    team_dict = read_json("team.json")
    player_dict = read_json("player.json")
    event_dict = read_json("event.json")
    match_dict = read_json("match.json")
    map_dict = read_json("map.json")
    map_player_dict = read_json("map_player.json", is_tuple_key=True)

    # round_prediction_generator(event_dict, match_dict, map_dict, team_dict)
    # rating_prediction_generator(event_dict, match_dict, map_dict, map_player_dict, player_dict)
    # map_prediction_simple_generator(event_dict, match_dict, map_dict, team_dict)
    map_prediction_generator(event_dict, match_dict, map_dict, team_dict)
    
    # ratings = np.array([float(map_player_dict[map]["rating"]) for map in map_player_dict])
    # mean = np.mean(ratings)
    # median = np.median(ratings)
    # max = np.max(ratings)
    # min = np.min(ratings)
    # std_dev = np.std(ratings)
    # print(f"Mean: {mean}, median: {median}, max: {max}, min: {min}, std_dev: {std_dev}")
    # plt.hist(ratings, bins=40)
    # plt.ylabel("Frequency")
    # plt.xlabel("Rating")
    # plt.title("Histogram of player ratings in dataset")
    # plt.show()


    # Print stuff so we get the .arff nominal attribute specifications right
    # print(set([map_dict[map]["map_name"] for map in map_dict]))
    # print([team_dict[team]["name"] for team in team_dict])
    # print(set([round["round_type"] for map in map_dict for round in map_dict[map]["rounds"]]))

if __name__ == "__main__":
    main()