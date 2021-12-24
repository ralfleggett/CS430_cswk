import re
import requests
import time

from bs4 import BeautifulSoup, NavigableString
from datetime import datetime
from tqdm import tqdm

class HLTV():

    def __init__(self, base_url, timeout=0.5):
        self.base_url = "https://" + base_url
        self.timeout = timeout
        self.last_request = None

    def _soup_from_url(self, url):
        """
        Returns soup object for the given url
        """
        # Apply timeout if needed
        if self.last_request is not None:
            time_diff = time.time() - self.last_request
            if time_diff < self.timeout:
                time.sleep(self.timeout - time_diff)

        url.replace(" ", "-")   # Replace whitespace with dash

        # If we get rate limited, wait 2mins then retry
        while True:
            response = requests.get(url)
            self.last_request = time.time()

            soup = BeautifulSoup(response.text, "html.parser")

            if "Access denied" in soup.find("title").string:
                print("Rate limited, waiting 2 minutes...")
                time.sleep(120)
            else:
                break

        return soup

    def get_event_teams(self, event_id, event_name):
        """
        Returns a dictionary of {(team_name: team_id)} for the event in 
        the url
        """
        url = f"{self.base_url}/events/{event_id}/{event_name}"
        soup = self._soup_from_url(url)

        teams_html = soup.find("div", {"class": "group"})
        teams_html = teams_html.find_all("div", {"class": "group-name"})

        team_dict = {}
        for team in teams_html:
            name = team.div.find("div", {"class": "text-ellipsis"}).string
            id = re.split("/", team.a["href"])[2]
            team_dict[id] = {"name": name}

        return team_dict

    def get_event_team_players(self, team_id, team_name, event_id):
        """
        Returns dictionary {(player_name: player_id)} for the team url
        for the event ID
        """
        url = f"{self.base_url}/stats/teams/{team_id}/{team_name}?event={event_id}"
        soup = self._soup_from_url(url)

        players_html = soup.find("div", {"class": "contentCol"})
        players_html = players_html.find("div", {"class": "reset-grid"})
        players_html = players_html.find_all("div", {"class": "teammate-info"})

        players_dict = {}
        for player in players_html:
            name = player.a.div.string
            id = re.split("/", player.a["href"])[3]
            players_dict[id] = {"name": name}
        
        return players_dict

    def get_map_ids(self, player_ids, team_id, opponent_ids, 
        latest_date=None, min_players=5):
        """
        Params:
            player_ids:     list of ints. The 5 player ids that form team
            team_id:        int. The id of the team the 5 players play for
            opponent_ids:   list of ints. Team ids to get map ids for
            latest_date:    date. Ignore maps (strictly) after this date
            min_players:    int. How many of the player_ids to require to 
                            include the map
        Returns:
            dictionary {(map_id: [team_id, opponent_id])}
        """
        url = f"{self.base_url}/stats/lineup/matches?minLineupMatch={min_players}"
        for id in player_ids:
            url += f"&lineup={id}"
        soup = self._soup_from_url(url)

        maps_html = soup.find("table", {"class": "stats-table"}).tbody
        maps_html = maps_html.find_all("tr")

        map_ids = {}
        for map in maps_html:
            # Check date of map
            date_td = map.td
            date = datetime.strptime(date_td.a.string, "%d/%m/%y").date()
            if latest_date is not None and date > latest_date:
                continue
            
            # Get team IDs n.b. strings after an html tag count as the next #
            # sibling, so double the .next_sibling count to account for the 
            # new lines in the html document
            team1_td = date_td.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling.next_sibling
            team1_id = re.split("/", team1_td.a["href"])[3]
            team2_id = re.split("/", team1_td.next_sibling.next_sibling.a["href"])[3]

            # Append if team ids are what we're looking for
            if team1_id == team_id and team2_id in opponent_ids:
                map_id = re.split("/", date_td.a["href"])[4]
                map_ids[map_id] = [team1_id, team2_id]

        return map_ids

    def get_match_info(self, map_ids, team_dict, use_tqdm=True):
        """
        Params:
            map_ids:   dictionary of {(map_id: {})} to fetch matches for
            team_dict: dictionary of {(team_id: {name, players})}
            use_tqdm:  boolean: whether to use tqdm or not
        Returns:
            dictionary 
            {
                (match_id: {
                    team1_id:        int
                    team2_id:        int
                    format:          {bo1, bo3, bo5}
                    LAN:             boolean
                    score:           (int, int)
                    map_ids:         [map_id]
                })
            }
            dictionary 
            {(map_id: team_id of team that picked map, or None if decider)}
            dictionary 
            {
                (event_id: {
                    event_name,
                    event_matches
                })
            }
        """
        match_ids = {}
        map_picks = {}
        event_ids = {}

        # Dictionary of map ids that we have already found the matches for
        # Faster than checking map webpage
        encountered_map_ids = {}

        items = tqdm(map_ids.items()) if use_tqdm else map_ids.items()
        for map_id, (team1_id, team2_id) in items:
            team1_name = team_dict[team1_id]['name']
            team2_name = team_dict[team2_id]['name']

            if map_id not in encountered_map_ids:

                # Get map url
                map_url = (
                    f"{self.base_url}/stats/matches/mapstatsid/{map_id}/"
                    f"{team1_name}-vs-{team2_name}"
                )
                map_soup = self._soup_from_url(map_url)

                # Find match id
                match_html = map_soup.find("div", {"class": "colCon"})
                match_html = match_html.find("div", {"class": "match-info-box-con"})
                match_html = match_html.find("a", {"class": "match-page-link"})
                match_id = re.split("/", match_html["href"])[2]

                # Get info for match
                match_dict, map_dict, event_id, event_name = self._get_match_info(match_id, team1_name, team2_name)
                match_ids.update(match_dict)
                map_picks.update(map_dict)

                # Add to events dict
                if event_id not in event_ids:
                    event_ids[event_id] = {
                        "event_name": event_name,
                        "match_ids":  [match_id]
                    }
                else:
                    event_ids[event_id]["match_ids"].append(match_id)

                # Update encountered_map_ids
                for id in match_dict[match_id]["map_ids"]:
                    encountered_map_ids[id] = None

        return match_ids, map_picks, event_ids

    def _get_match_info(self, match_id, team1_name, team2_name):
        """
        Retrieves dictionary of match info
        """
        # Get match url
        match_url = (
            f"{self.base_url}/matches/{match_id}/"
            f"{team1_name}-vs-{team2_name}"
        )
        match_soup = self._soup_from_url(match_url)

        # Gather the info required
        match_html = match_soup.find("div", {"class": "match-page"})
        team1_div = match_html.div.div
        team1_id = re.split("/", team1_div.div.a["href"])[2]
        team1_score = team1_div.div.a.next_sibling.next_sibling.string
        event_div = team1_div.next_sibling.next_sibling
        event_a = event_div.find("div", {"class": "event"}).a
        event_id = re.split("/", event_a["href"])[2]
        event_name = event_a.string
        team2_div = event_div.next_sibling.next_sibling
        team2_id = re.split("/", team2_div.div.a["href"])[2]
        team2_score = team2_div.div.a.next_sibling.next_sibling.string

        format_div = match_html.find("div", {"class": "maps"}).div.div
        format_series = format_div.div.string.split()[2]
        format_lan = "Online" not in format_div.div.string

        # Fix score if Bo1. Note this doesn't work with tie games, but none 
        # in the dataset
        if format_series == "1":
            if int(team1_score) > int(team2_score):
                team1_score = "1"
                team2_score = "0"
            else:
                team1_score = "0"
                team2_score = "1"

        map_id_list = []
        map_pick_dict = {}
        map_div = format_div.parent.find("div", {"class": "flexbox-column"})
        for map in map_div.contents:
            if isinstance(map, NavigableString):
                continue
            if "optional" in map.div["class"]:
                continue
            # Check if default map (i.e. one team has a map advantage)
            if map.div.div.div.string == "Default":
                continue

            results_div = map.div.next_sibling.next_sibling
            map_stat_link = results_div.div.next_sibling.next_sibling.div.a
            map_id = re.split("/", map_stat_link["href"])[4]
            map_id_list.append(map_id)

            if "pick" in results_div.div["class"]:
                map_pick_dict[map_id] = team1_id
            elif "pick" in results_div.div.next_sibling.next_sibling.next_sibling.next_sibling["class"]:
                map_pick_dict[map_id] = team2_id
            else:
                map_pick_dict[map_id] = None

        match_dict = {
            match_id: {
                "team1_id":    team1_id,
                "team2_id":    team2_id,
                "format":      f"Bo{format_series}",
                "LAN":         format_lan,
                "score":       (team1_score, team2_score),
                "map_ids":     map_id_list
            }
        }

        return match_dict, map_pick_dict, event_id, event_name

    def get_map_info(self, teams_dict, matches_dict, map_picks_dict, 
        use_tqdm=True):
        """
        Params:
            teams_dict:     dictionary returned from self.get_major_teams()
            matches_dict:   dictionary returned from self.get_match_info()
            map_picks_dict: dictionary returned from self.get_match_info()
            use_tqdm:       boolean. Whether to use tqdm
        Returns:
            dictionary
            {
                (map_id: {
                    date:              string (datetime)
                    map_name:          string
                    team1_id:          int
                    team2_id:          int
                    map_picked_by:     int. id of team
                    ct_start_team:     int. id of team
                    score:             (int, int). (team1, team2)
                    first_half_score:  (int, int). (team1, team2)
                    second_half_score: (int, int). (team1, team2)
                    overtime_score:    (int, int). (team1, team2)
                    team_rating:       (int, int). (team1, team2)
                    first_kills:       (int, int). (team1, team2)
                    clutches:          (int, int). (team1, team2)
                    rounds:            [{round_winner, round_type, team1_buy, 
                                         team2_buy, team1_buy_type, 
                                         team2_buy_type}] 
                                       list of dicts for each round
                    team1_players:     [int]. list of player ids
                    team2_players:     [int]. list of player ids
                })
            }
            list [invalid_map_ids] list of map_ids that were not mr16 format
        """
        def im_src_to_win_type(im_src):
            if im_src == "t_win.svg" or im_src == "ct_win.svg":
                return "elimination"
            elif im_src == "bomb_defused.svg":
                return "defuse"
            elif im_src == "bomb_exploded.svg":
                return "bomb"
            elif im_src == "stopwatch.svg":
                return "timeout"

        def get_econ(td):
            equip_val = td["title"][17:]
            if int(equip_val) > 20_000:
                return "full_buy", equip_val
            elif int(equip_val) > 10_000:
                return "semi_buy", equip_val
            elif int(equip_val) > 5_000:
                return "semi_eco", equip_val
            else:
                return "eco", equip_val

        map_info_dict = {}
        invalid_map_ids = []

        match_keys = tqdm(matches_dict, unit="matches") if use_tqdm else matches_dict
        for match in match_keys:
            team1_id = matches_dict[match]["team1_id"]
            team2_id = matches_dict[match]["team2_id"]
            team1_name = teams_dict[team1_id]["name"]
            team2_name = teams_dict[team2_id]["name"]

            for map_id in matches_dict[match]["map_ids"]:
                # Get map url
                url = (
                    f"{self.base_url}/stats/matches/mapstatsid/{map_id}/"
                    f"{team1_name}-vs-{team2_name}"
                )
                soup = self._soup_from_url(url).find("div", {"class": "stats-match"})

                summary_html = soup.find("div", {"class": "wide-grid"}).div.div

                map_date = summary_html.div.div.span.string
                map_name = re.sub(r"[\n\t\s]*", "", summary_html.div.div.next_sibling)

                # Check team ids are in same order as on match page
                map_team_1_id = summary_html.div.find("div", {"class": "team-left"})
                map_team_1_id = re.split("/", map_team_1_id.a["href"])[3]
                map_team_2_id = summary_html.div.find("div", {"class": "team-right"})
                map_team_2_id = re.split("/", map_team_2_id.a["href"])[3]
                if map_team_1_id != team1_id:
                    print(
                        f"Mismatched team ids: {team1_id} != {map_team_1_id}"
                        f"{team2_id} != {map_team_2_id}"
                    )

                info_rows = summary_html.find_all("div", {"class": "match-info-row"})

                # Scores
                scores_spans = info_rows[0].find("div", {"class": "right"}).find_all("span")
                team1_score = scores_spans[0].string
                team2_score = scores_spans[1].string
                team1_first_half_score = scores_spans[2].string
                team2_first_half_score = scores_spans[3].string
                ct_start_team = map_team_1_id if "ct-color" in scores_spans[2]["class"] else map_team_2_id
                team1_second_half_score = scores_spans[4].string
                team2_second_half_score = scores_spans[5].string
                team1_overtime_score = "0"
                team2_overtime_score = "0"
                # Check game was mr16 and not something funky
                if int(team1_score) < 16 and int(team2_score) < 16:
                    invalid_map_ids.append(map_id)
                    continue
                # Check for overtime
                if int(team1_score) > 16 or int(team2_score) > 16:
                    overtime_str = re.sub(r"[\n\t\s()]*", "", scores_spans[5].next_sibling)
                    team1_overtime_score, team2_overtime_score = re.split(":", overtime_str)

                team_ratings = info_rows[1].find("div", {"class": "right"}).string
                team_ratings = [team_ratings.split()[i] for i in [0, 2]]

                first_kills = info_rows[2].find("div", {"class": "right"}).string
                first_kills = [first_kills.split()[i] for i in [0, 2]]

                clutches = info_rows[3].find("div", {"class": "right"}).string
                clutches = [clutches.split()[i] for i in [0, 2]]

                # Players
                stats_tables = soup.find_all("table", {"class": "stats-table"})
                team1_players_html = stats_tables[0].find_all("td", {"class": "st-player"})
                team1_players = [re.split("/", p.a["href"])[3] for p in team1_players_html]
                team2_players_html = stats_tables[1].find_all("td", {"class": "st-player"})
                team2_players = [re.split("/", p.a["href"])[3] for p in team2_players_html]

                # Round winner and type
                # Get url for economy history
                econ_url = (
                    f"{self.base_url}/stats/matches/economy/mapstatsid/"
                    f"{map_id}/{team1_name}-vs-{team2_name}"
                )
                econ_soup = self._soup_from_url(econ_url)
                econ_soup = econ_soup.find_all("table", {"class": "equipment-categories"})
                econ_exists = False
                if len(econ_soup) == 2:
                    first_half_econ = econ_soup[0].find_all("tr")
                    team1_econ = first_half_econ[0].find_all("td", {"class": "equipment-category-td"})
                    team2_econ = first_half_econ[1].find_all("td", {"class": "equipment-category-td"})
                    second_half_econ = econ_soup[1].find_all("tr")
                    team1_econ.extend(second_half_econ[0].find_all("td", {"class": "equipment-category-td"}))
                    team2_econ.extend(second_half_econ[1].find_all("td", {"class": "equipment-category-td"}))
                    econ_exists = True

                rounds = []
                rounds_html = soup.find("div", {"class": "round-history-con"})
                rounds_html = rounds_html.find_all("div", {"class": "round-history-team-row"})
                team1_rounds_html = rounds_html[0].find_all("img", {"class": "round-history-outcome"})
                team2_rounds_html = rounds_html[1].find_all("img", {"class": "round-history-outcome"})
                for (im1, im2, econ1, econ2) in zip(team1_rounds_html, team2_rounds_html, team1_econ, team2_econ):
                    im1_type = re.split("/", im1["src"])[4]
                    im2_type = re.split("/", im2["src"])[4]
                    if im1_type != "emptyHistory.svg":
                        win_type = im_src_to_win_type(im1_type)
                        win_team = map_team_1_id
                    elif im2_type != "emptyHistory.svg":
                        win_type = im_src_to_win_type(im2_type)
                        win_team = map_team_2_id
                    else:
                        # Game finished, rest or scoreboard is empty
                        break
                    if econ_exists:
                        t1_econ_type, t1_econ = get_econ(econ1)
                        t2_econ_type, t2_econ = get_econ(econ2)
                        rounds.append({
                            "round_winner": win_team, 
                            "round_type": win_type,
                            "team1_buy": t1_econ,
                            "team2_buy": t2_econ,
                            "team1_buy_type": t1_econ_type,
                            "team2_buy_type": t2_econ_type
                        })
                    else:
                        rounds.append({
                            "round_winner": win_team, 
                            "round_type": win_type
                        })

                # Add to dict
                map_info_dict[map_id] = {
                    "date":              map_date,
                    "map_name":          map_name,
                    "team1_id":          map_team_1_id,
                    "team2_id":          map_team_2_id,
                    "map_picked_by":     map_picks_dict[map_id],
                    "ct_start_team":     ct_start_team,
                    "score":             (team1_score, team2_score),
                    "first_half_score":  (team1_first_half_score, team2_first_half_score),
                    "second_half_score": (team1_second_half_score, team2_second_half_score),
                    "overtime_score":    (team1_overtime_score, team2_overtime_score),
                    "team_rating":       team_ratings,
                    "first_kills":       first_kills,
                    "clutches":          clutches,
                    "rounds":            rounds,
                    "team1_players":     team1_players,
                    "team2_players":     team2_players
                }

        return map_info_dict, invalid_map_ids

    def get_map_player_info(self, map_dict, player_dict, team_dict, 
        use_tqdm=True):
        """
        Params:
            map_dict:
            player_dict:
            team_dict:
            use_tqdm:       boolean. Whether to use tqdm
        Returns:
            dictionary
            {
                ((map_id, player_id): {
                    kills:          int
                    headshots:      int
                    deaths:         int
                    assists:        int
                    flash_assists:  int
                    KAST:           float. Percentage
                    ADR:            float
                    first_kills:    int
                    first_deaths:   int
                    rating:         float
                })
            }
            player_dict updated with new players
            teams_dict  updated with new players
        """
        def get_overview_stats(tr, map_id, team_id, player_dict, team_dict):
            # Get info
            tds = tr.find_all("td")
            player_id = re.split("/", tds[0].div.a["href"])[3]
            player_name = tds[0].div.a.string
            kills = tds[1].get_text().split()[0]
            headshots = re.sub(r"[()]*", "", tds[1].get_text().split()[1])
            assists = tds[2].get_text().split()[0]
            flash_assists = re.sub(r"[()]*", "", tds[2].get_text().split()[1])
            deaths = tds[3].string
            kast = tds[4].string[:-1]
            adr = tds[6].string
            first_kills = tds[7]["title"].split()[0]
            first_deaths = tds[7]["title"].split()[3]
            rating = tds[8].string

            # Check player in player_dict
            if player_id not in player_dict:
                print(f"{player_name} ({player_id}) not in team {team_dict[team_id]['name']} ({team_id})")
                player_dict[player_id] = {"name": player_name}
                team_dict[team_id]["players"].append(player_id)

            stats_dict = {(map_id, player_id): {
                "kills": kills,
                "headshots": headshots,
                "assists": assists,
                "flash_assists": flash_assists,
                "deaths": deaths,
                "kast": kast,
                "adr": adr,
                "first_kills": first_kills,
                "first_deaths": first_deaths,
                "rating": rating
            }}

            return stats_dict, player_dict, team_dict

        player_map_dict = {}

        items = tqdm(map_dict, unit="maps") if use_tqdm else map_dict
        for map in items:
            stats_dict = {} # Update smaller dict before adding to main

            team1_id = map_dict[map]["team1_id"]
            team2_id = map_dict[map]["team2_id"]
            team1_name = team_dict[team1_id]["name"]
            team2_name = team_dict[team2_id]["name"]

            # Get the good soup
            overview_url = (
                f"{self.base_url}/stats/matches/mapstatsid/{map}/"
                f"{team1_name}-vs-{team2_name}"
            )
            overview_soup = self._soup_from_url(overview_url)
            overview_soup = overview_soup.find("div", {"class": "stats-match"})
            ### CAN'T FETCH :(
            # performance_url = (
            #     f"{self.base_url}/stats/matches/performance/mapstatsid/{map}/"
            #     f"{team1_name}-vs-{team2_name}"
            # )
            # performance_soup = self._soup_from_url(performance_url)

            # Player stats from overview page
            stats_html = overview_soup.find_all("table", {"class": "stats-table"})
            team1_stats_html = stats_html[0].tbody.find_all("tr")
            team2_stats_html = stats_html[1].tbody.find_all("tr")
            for tr in team1_stats_html:
                stats, player_dict, team_dict = get_overview_stats(
                    tr, map, team1_id, player_dict, team_dict)
                stats_dict.update(stats)
            for tr in team2_stats_html:
                stats, player_dict, team_dict = get_overview_stats(
                    tr, map, team2_id, player_dict, team_dict)
                stats_dict.update(stats)

            # Impact stat from performance page
            # impact_html = performance_soup.find("div", {"class": "player-overview"})
            # impact_html = impact_html.find_all("div", {"class": "highlighted-player"})
            # for player in impact_html:
            #     player_id = re.split("/", player.div.div.span.a["href"])[2]
            #     impact = player.find("div", {"class": "facts"}).div
            #     impact = ast.literal_eval(impact["data-fusionchart-config"])
            #     impact = impact["data"][3]["value"]

            player_map_dict.update(stats_dict)

        return player_map_dict, player_dict, team_dict