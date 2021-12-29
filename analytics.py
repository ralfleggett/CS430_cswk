import matplotlib.pyplot as plt
import numpy as np

from datetime import datetime

from main import read_json

def get_matchup_frequencies(team_dict, map_dict):
    """
    Prints frequency of maps played between each team as a table
    """
    # Map team ids to array indicies
    team_to_idx = {}
    for i, team in enumerate(team_dict.keys()):
        team_to_idx[int(team)] = i
    
    # Create table
    freq = np.zeros((len(team_dict), len(team_dict)), dtype="uint8")
    for map in map_dict:
        id1 = int(map_dict[map]["team1_id"])
        id2 = int(map_dict[map]["team2_id"])
        idx1 = max(team_to_idx[id1], team_to_idx[id2])
        idx2 = min(team_to_idx[id1], team_to_idx[id2])
        assert idx1 != idx2 # Sanity check
        freq[idx1, idx2] += 1

    # Sanity check
    n = np.sum(freq)
    assert n == len(map_dict)

    # Print table
    teamnames = [team_dict[t]["name"] for t in team_dict]
    string = "      "
    for name in teamnames:
        string += f"{name[:5]:5} "
    print(string)
    for team in team_dict.keys():
        string = f"{team_dict[team]['name'][:5]:5}"
        for idx in range(team_to_idx[int(team)]):
            string += f"{freq[team_to_idx[int(team)], idx]:6}"
        print(string)

def get_team_freq(team_dict, map_dict):
    """
    Creates a bar chart of the number of maps in the dataset for each team
    """
    freq = {}
    for team in team_dict:
        freq[team] = 0

    for map in map_dict:
        freq[map_dict[map]["team1_id"]] += 1
        freq[map_dict[map]["team2_id"]] += 1

    fig = plt.figure(figsize=(12,12))
    ax = fig.add_subplot(111)
    ax.set_ylim([0, 180])
    bars = ax.bar([team_dict[t]["name"][:5] for t in freq], freq.values())
    for rect in bars:
        h = rect.get_height()
        ax.text(rect.get_x() + rect.get_width() / 2.0, h + 0.2, 
                f"{h}", ha="center", va="bottom")
    ax.set_title("Number of games in dataset for each team")
    ax.set_ylabel("Number of maps")
    ax.set_xlabel("Team")
    plt.show()

def get_team_map_freq(event_dict, match_dict, map_dict, team_dict, train_set_only=True):
    """
    Barchart for each team displaying frequency of each map.
    """
    freq = {}
    test_maps = [map_id for match_id in event_dict["4866"]["match_ids"] for map_id in match_dict[match_id]["map_ids"]]
    for team in team_dict:
        maps = {}
        for m in ["Inferno", "Overpass", "Vertigo", "Dust2", "Mirage", "Nuke", "Train", "Ancient"]:
            maps[m] = 0
        freq[team] = maps

    for map in map_dict:
        if train_set_only and map in test_maps:
            continue
        freq[map_dict[map]["team1_id"]][map_dict[map]["map_name"]] += 1
        freq[map_dict[map]["team2_id"]][map_dict[map]["map_name"]] += 1

    fig = plt.figure(figsize=(12,12))
    fig.tight_layout()
    for i, team in enumerate(freq):
        ax = fig.add_subplot(4, 4, i+1)
        plt.subplots_adjust(left=0.02, bottom=0.03, right=0.98, top = 0.97, hspace=.35, wspace = .1)
        ax.set_ylim([0, (35 if train_set_only else 40)])
        bars = ax.bar([k[:5] for k in freq[team]], freq[team].values())
        for rect in bars:
            h = rect.get_height()
            ax.text(rect.get_x() + rect.get_width() / 2.0, h + 0.2, 
                    f"{h}", ha="center", va="bottom")
        ax.set_title(team_dict[team]["name"])
    plt.show()

def get_map_freq(map_dict):
    """
    Bar chart of number of instances of each map
    """
    freq = {}
    for map in map_dict:
        name = map_dict[map]["map_name"]
        if name not in freq:
            freq[name] = 1
        else:
            freq[name] += 1

    plt.figure(figsize=(12,12))
    plt.bar(list(freq.keys()), freq.values())
    plt.title("Frequency of each map in dataset")
    plt.show()

def get_major_matchup_freq(team_dict, map_dict, match_dict, event_dict):
    """
    Find the frequency of each matchup in the major
    """
    matchups = {}
    major_maps = []
    for match in event_dict["4866"]["match_ids"]:
        t1 = match_dict[match]["team1_id"]
        t2 = match_dict[match]["team2_id"]
        matchups[(t1, t2)] = 0
        major_maps.extend(match_dict[match]["map_ids"])

    for map in map_dict:
        if map in major_maps:
            continue
        t1 = map_dict[map]["team1_id"]
        t2 = map_dict[map]["team2_id"]
        if (t1, t2) in matchups:
            matchups[(t1, t2)] += 1

    matchups_list = []
    for (t1, t2) in matchups:
        matchups_list.append((f"{team_dict[t1]['name'][:5]:5}", f"{team_dict[t2]['name'][:5]:5}", matchups[(t1, t2)]))

    matchups_list.sort(key=lambda x: x[2], reverse=True)
    for t1, t2, freq in matchups_list:
        print(f"{t1} vs {t2}: {freq}")

def get_map_biases(map_dict):
    """
    Calculates and displays the percentage of rounds won by the CTs for each
    map in the dataset
    """
    bias = {}
    total_rounds = 0

    for map in map_dict:
        name = map_dict[map]["map_name"]
        ct_idx = 0 if map_dict[map]["team1_id"] == map_dict[map]["ct_start_team"] else 1

        # Get scores
        first_half_score = map_dict[map]["first_half_score"]
        first_half_score = (int(first_half_score[0]), int(first_half_score[1]))
        second_half_score = map_dict[map]["second_half_score"]
        second_half_score = (int(second_half_score[0]), int(second_half_score[1]))
        overtime_score = map_dict[map]["overtime_score"]
        overtime_score = (int(overtime_score[0]), int(overtime_score[1]))

        # Add to sanity check total_rounds
        rounds = first_half_score[0] + first_half_score[1]
        rounds += second_half_score[0] + second_half_score[1]
        rounds += overtime_score[0] + overtime_score[1]
        total_rounds += rounds

        # Sum rounds for regulation
        ct_rounds = first_half_score[ct_idx] + second_half_score[(ct_idx + 1) % 2]
        t_rounds = first_half_score[(ct_idx + 1) % 2] + second_half_score[ct_idx]

        # Deal with overtime
        if overtime_score[0] != 0 or overtime_score[1] != 0:
            # Teams start as the same side they just played
            while overtime_score[0] >= 0 and overtime_score[1] >= 0:
                ct_idx = (ct_idx + 1) % 2
                ct_rounds += min(3, overtime_score[ct_idx])
                t_rounds += min(3, overtime_score[(ct_idx + 1) % 2])
                overtime_score = (overtime_score[0] - 3, overtime_score[1] - 3)
            # Add the winning round
            if overtime_score[ct_idx] > 0:
                ct_rounds += 1
            else:
                t_rounds += 1

        # Sanity check
        assert rounds == (ct_rounds + t_rounds)

        # Add to biases
        if name not in bias:
            bias[name] = (ct_rounds, t_rounds)
        else:
            bias[name] = (bias[name][0] + ct_rounds, bias[name][1] + t_rounds)

    # Calculate percentages and plot
    names = []
    ct_percs = []
    t_percs = []
    maps = list(bias.keys())
    maps.sort()
    for map in maps:
        ct_bias = 100 * bias[map][0] / (bias[map][0] + bias[map][1])
        names.append(map)
        ct_percs.append(ct_bias)
        t_percs.append(100 - ct_bias)
    
    xvals = np.arange(len(names))
    bar_width = 0.35
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.set_ylim([0, 60])
    bars1 = ax.bar(xvals, ct_percs, bar_width, color="#2c6ca2")
    bars2 = ax.bar(xvals + bar_width, t_percs, bar_width, color="#e0a639")

    ax.set_ylabel("Round win %")
    ax.set_xticks(xvals + 0.5 * bar_width)
    ax.set_xticklabels(names)
    ax.set_title("Round win percentage for CT / T per map in dataset")
    # Shrink current axis by 20%
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])

    # Put a legend to the right of the current axis
    ax.legend((bars1[0], bars2[0]), ("CT", "T"), loc='center left', bbox_to_anchor=(1, 0.5))

    def autolabel(rects):
        for rect in rects:
            h = rect.get_height()
            ax.text(rect.get_x() + rect.get_width() / 2.0, h + 0.2, 
                    f"{h:.1f}", ha="center", va="bottom")

    autolabel(bars1)
    autolabel(bars2)
    plt.show()

    # Sanity check
    bias_total_rounds = 0
    for map in bias:
        bias_total_rounds += bias[map][0] + bias[map][1]
    assert bias_total_rounds == total_rounds

def get_map_dates(map_dict):
    date_dict = {}
    for year in range(2019, 2022):
        for q in range(1, 5):
            date_dict[f"{year}Q{q}"] = 0

    for map in map_dict:
        dt = datetime.strptime(map_dict[map]["date"], "%Y-%m-%d %H:%M")
        year = dt.year
        month = dt.month
        if month > 9:
            quarter = 4
        elif month > 6:
            quarter = 3
        elif month > 3:
            quarter = 2
        else:
            quarter = 1
        date_dict[f"{year}Q{quarter}"] += 1

    xvals = list(date_dict.keys())
    xvals.reverse()
    yvals = list(date_dict.values())
    yvals.reverse()
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.set_ylim([0, 200])
    xticks = np.arange(len(xvals))
    bars = ax.bar(xticks, yvals)

    ax.set_ylabel("Number of maps")
    ax.set_xticks(xticks)
    ax.set_xticklabels(xvals)
    ax.set_xlabel("Date (year and quarter)")
    ax.set_title("Distribution of games in dataset by date")

    for rect in bars:
        h = rect.get_height()
        ax.text(rect.get_x() + rect.get_width() / 2.0, h + 0.2, 
                f"{h}", ha="center", va="bottom")

    plt.show()

def maps_without_econ_stats(map_dict):
    """ Print number of maps without round-by-round econ stats """
    i = 0
    for map in map_dict:
        if "team1_buy" not in map_dict[map]["rounds"][0]:
            i += 1
            print(map_dict[map]["date"])
            print(map)
    print(i)

def main():
    team_dict = read_json("team.json")
    player_dict = read_json("player.json")
    event_dict = read_json("event.json")
    match_dict = read_json("match.json")
    map_dict = read_json("map.json")
    map_player_dict = read_json("map_player.json", is_tuple_key=True)

    plt.rcParams.update({'font.size': 15})
    # maps_without_econ_stats(map_dict)
    # get_matchup_frequencies(team_dict, map_dict)
    get_team_freq(team_dict, map_dict)
    # get_map_freq(map_dict)
    # get_team_map_freq(event_dict, match_dict, map_dict, team_dict, train_set_only=False)
    # get_major_matchup_freq(team_dict, map_dict, match_dict, event_dict)
    # get_map_biases(map_dict)
    get_map_dates(map_dict)

if __name__ == "__main__":
    main()