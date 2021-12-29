# HLTV Scraper & Analytics

Coursework for CS430 Data Analytics. Please note that unlike in the report, "map" and "game" are often conflated in the code. This .json files are included, with the "map.json" being the "game" table in the report, and "map_player.json" being the "game_player" table in the report.

Games with min_players = 5: 330

Games with min_players = 4: 725

## HLTV.py
The main logic for scraping HLTV for the various data

## main.py
Implements the code that runs HLTV.py and saves the data into .json files

## analytics.py
Simple data analytics tasks for producing summary plots on the dataset

## dataset_generation.py
Functions for generating datasets for some of the more complex analytics tasks carried out in Weka

## round_prediction.py
Code for implementing and training a neural network for round prediction using Keras
