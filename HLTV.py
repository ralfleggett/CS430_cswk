import re
import requests
import socket
import time

from bs4 import BeautifulSoup
from collections import OrderedDict
from datetime import datetime
from requests import Session

class HLTV():

    def __init__(self, base_url, timeout=3):
        self.base_url = "https://" + base_url
        self.timeout = timeout
        self.last_request = None

        # answers = socket.getaddrinfo(base_url, 443)
        # (family, type, proto, canonname, (address, port)) = answers[0]
        # self.address = address
        # print(self.address)

    def _soup_from_url(self, url):
        """
        Returns soup object for the given url
        """
        # s = Session()
        # headers = OrderedDict({
        #     'Accept-Encoding': 'gzip, deflate, br',
        #     'Host': 'www.hltv.org',
        #     'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36'
        # })
        # s.headers = headers
        # response = s.get(f"https://{self.address}{url}", headers=headers, verify=False).text

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
            team_dict[name] = id

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
            players_dict[name] = {"id": id, "team_id": team_id}
        
        return players_dict