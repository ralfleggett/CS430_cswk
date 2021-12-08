import re
import requests
import time

from bs4 import BeautifulSoup
from datetime import datetime

class HLTV():

    def __init__(self, base_url, timeout=3):
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

        response = requests.get(url)
        self.last_request = time.time()

        return BeautifulSoup(response.text, "html.parser")

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
            dictionary {(map_id: [team_id, opponent_id]
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

