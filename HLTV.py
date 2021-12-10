import re
import requests
import time

from bs4 import BeautifulSoup, NavigableString
from datetime import datetime
from tqdm import tqdm

class HLTV():

    def __init__(self, base_url, timeout=0.25):
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
