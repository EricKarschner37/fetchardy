#!/opt/venv/bin/python
import requests
from bs4 import BeautifulSoup
from ddtrace import tracer
from flask import Flask, request
import csv
import sys
import os
import json
import re

class GameNotFoundException(Exception):
    pass

def get_game(game_id):
    url = f"https://www.j-archive.com/showgame.php?game_id={game_id}"
    html = requests.get(url).text
    soup = BeautifulSoup(html, 'html.parser')
    if f'ERROR: No game {game_id} in database' in html:
        raise GameNotFoundException()

    rounds = []

    rounds_unparsed = soup.find_all('div', id=re.compile('.*jeopardy_round'))
    for r in rounds_unparsed:
        default_round = r.select_one('table.round')
        title = r.select_one('h2').text
        if default_round:
            smallest_clue_value = int(r.select_one('td.clue_value').text[1:])
            rounds.append(pull_default_from_table(default_round, name=title, round_multiplier=smallest_clue_value // 100))
        final_round = r.select_one('table.final_round')
        if final_round:
            rounds.append(pull_final_from_table(final_round, name=title))

    return {'rounds': rounds}

def get_default_max_wager_for_round(round_name):
    if round_name == 'Jeopardy! Round':
        return 1000
    if round_name == 'Double Jeopardy! Round':
        return 2000
    if round_name == 'Final Jeopardy' or round_name == 'Triple Jeopardy! Round':
        return 3000
    return 1000

# j-archive formats media urls as
# `https://www.j-archive.com/media/<filename>`
MEDIA_URL_PREFIX = 'https://www.j-archive.com/media/'
def get_filename_from_media_url(url):
    return url[len(MEDIA_URL_PREFIX):]

def pull_default_from_table(table, name, round_multiplier=2):
    categories = [{'category': td.text, 'clues': []} for td in table.select("td.category_name")]

    clue_rows = table.find_all("tr", recursive=False)[1:] # The first row is categories
    for row_i, tr in enumerate(clue_rows):
        clueEls = tr.select("td.clue")
        for i, td in enumerate(clueEls):
            cost = 100 * (row_i + 1) * round_multiplier
            clueEl =td.select_one("td.clue_text") 
            responseEl = td.select_one("em.correct_response")
            clue = "This clue was missing"
            response = "This response was missing"
            if clueEl:
                clue = clueEl.text or "This clue was missing"
            if responseEl:
                response = responseEl.text or "This response was missing"
            is_daily_double = td.select_one("td.clue_value_daily_double") is not None
            media_url = None

            mediaEl = clueEl.select_one("a") if clueEl else None
            if mediaEl:
                href = mediaEl['href']
                media_data = requests.get(href).content
                media_filename = get_filename_from_media_url(href)
                with open(f'media/{media_filename}', 'wb') as f:
                    f.write(media_data)
                media_url = f'https://jeopardy.karschner.studio/media/{media_filename}'

            result = {'clue': clue, 'response': response, 'cost': cost, 'is_daily_double': is_daily_double}
            if media_url:
                result['media_url'] = media_url
            categories[i]['clues'].append(result)
    return {'categories': categories, 'name': name, 'round_type': 'DefaultRound', 'default_max_wager': get_default_max_wager_for_round(name)}

def pull_final_from_table(table, name):
    category = table.select_one('td.category_name').text
    clue = table.select_one("td#clue_FJ").text
    response = table.select_one('em.correct_response').text
    return {'category': category, 'clue': clue, 'response': response, 'round_type': 'FinalRound', 'name': 'Final Jeopardy', 'default_max_wager': get_default_max_wager_for_round('Final Jeopardy')}

@tracer.wrap()
def download_game(game_id):
    games_root = os.environ.get('J_GAME_ROOT') or 'games'
    payload = get_game(game_id)
    out_filename = f'{games_root}/{game_id}.json'
    with open(out_filename, 'w') as out_file:
        json.dump(payload, out_file)
    print(f'finished downloading: {game_id}')

GAME_FILE_EXTENSION = '.json'

def get_latest_game_id():
    games_root = os.environ.get('J_GAME_ROOT') or 'games'
    game_ids = [int(filename[:-len(GAME_FILE_EXTENSION)]) for filename in os.listdir(games_root)]
    if len(game_ids) == 0:
        return 0
    return max(game_ids)

def get_missing_games(count):
    latest_game_id = get_latest_game_id()
    for i in range(count):
        try:
            download_game(latest_game_id + 1 + i)
        except:
            print("All up to date")
            return

PORT = 80

app = Flask(__name__)

@app.route("/<game_id>")
def start(game_id):
    print('test')
    download_game(game_id)
    return game_id

@app.route('/')
def hello():
    return 'Hello World!'

USAGE_MESSAGE = 'Usage: python fetchardy.py (get-latest | get) [number-of-games | game_id]]'

if __name__ == '__main__':
    if len(sys.argv) == 1:
        sys.exit(USAGE_MESSAGE)
    command = sys.argv[1]
    if command == 'get-latest':
        count = 10
        if len(sys.argv) > 2:
            count_arg = sys.argv[2]
            try:
                count = int(count_arg)
            except:
                sys.exit(USAGE_MESSAGE)
        get_missing_games(count)
    else:
        if len(sys.argv) == 2:
            sys.exit(USAGE_MESSAGE)
        download_game(sys.argv[2])
