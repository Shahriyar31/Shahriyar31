import re
import os
import sys
import ast
from enum import Enum
from datetime import datetime
from urllib.parse import urlencode

import chess
import chess.pgn
import yaml
from github import Github

class Action(Enum):
    UNKNOWN = 0
    MOVE = 1
    NEW_GAME = 2

def update_top_moves(user):
    """Adds the given user to the top moves file"""
    with open('data/top_moves.txt', 'r') as file:
        contents = file.read()
        dictionary = ast.literal_eval(contents)

    if user not in dictionary:
        dictionary[user] = 1 # First move
    else:
        dictionary[user] += 1

    with open('data/top_moves.txt', 'w') as file:
        file.write(str(dictionary))

def update_last_moves(line):
    """Adds the given line to the last moves file"""
    with open('data/last_moves.txt', 'r+') as last_moves:
        content = last_moves.read()
        last_moves.seek(0, 0)
        last_moves.write(line.rstrip('\r\n') + '\n' + content)

def replace_text_between(original_text, marker, replacement_text):
    """Replace text between `marker['begin']` and `marker['end']` with `replacement`"""
    delimiter_a = marker['begin']
    delimiter_b = marker['end']

    if original_text.find(delimiter_a) == -1 or original_text.find(delimiter_b) == -1:
        return original_text

    leading_text = original_text.split(delimiter_a)[0]
    trailing_text = original_text.split(delimiter_b)[1]

    return leading_text + delimiter_a + replacement_text + delimiter_b + trailing_text

def parse_issue(title):
    """Parse issue title and return a tuple with (action, <move>)"""
    if title.lower() == 'chess: start new game':
        return (Action.NEW_GAME, None)

    if 'chess: move' in title.lower():
        match_obj = re.match('Chess: Move ([A-H][1-8]) to ([A-H][1-8])', title, re.I)
        if match_obj:
            source = match_obj.group(1)
            dest   = match_obj.group(2)
            return (Action.MOVE, (source + dest).lower())

    return (Action.UNKNOWN, None)

def create_link(text, link):
    return f"[{text}]({link})"

def create_issue_link(source, dest_list, settings):
    issue_link = settings['issues']['link'].format(
        repo=os.environ["GITHUB_REPOSITORY"],
        params=urlencode(settings['issues']['move'], safe="{}"))

    ret = [create_link(dest, issue_link.format(source=source, dest=dest)) for dest in sorted(dest_list)]
    return ", ".join(ret)

def generate_top_moves(settings):
    with open("data/top_moves.txt", 'r') as file:
        dictionary = ast.literal_eval(file.read())

    markdown = "\n"
    markdown += "| Total moves |  User  |\n"
    markdown += "| :---------: | :----- |\n"

    max_entries = settings['misc']['max_top_moves']
    for key,val in sorted(dictionary.items(), key=lambda x: x[1], reverse=True)[:max_entries]:
        markdown += "| {} | {} |\n".format(val, create_link(key, "https://github.com/" + key[1:]))

    return markdown + "\n"

def generate_last_moves(settings):
    markdown = "\n"
    markdown += "| Move | Author |\n"
    markdown += "| :--: | :----- |\n"

    counter = 0

    with open("data/last_moves.txt", 'r') as file:
        for line in file.readlines():
            if not line.strip():
                continue
            parts = line.rstrip().split(':')

            if not ":" in line:
                continue

            if counter >= settings['misc']['max_last_moves']:
                break

            counter += 1

            match_obj = re.search('([A-H][1-8])([A-H][1-8])', line, re.I)
            if match_obj is not None:
                source = match_obj.group(1).upper()
                dest   = match_obj.group(2).upper()
                markdown += "| `" + source + "` to `" + dest + "` | " + create_link(parts[1], "https://github.com/" + parts[1].lstrip()[1:]) + " |\n"
            else:
                markdown += "| `" + parts[0] + "` | " + create_link(parts[1], "https://github.com/" + parts[1].lstrip()[1:]) + " |\n"

    return markdown + "\n"

def generate_moves_list(board, settings):
    # Create dictionary and fill it
    from collections import defaultdict
    moves_dict = defaultdict(set)

    for move in board.legal_moves:
        source = chess.SQUARE_NAMES[move.from_square].upper()
        dest   = chess.SQUARE_NAMES[move.to_square].upper()
        moves_dict[source].add(dest)

    # Write everything in Markdown format
    markdown = ""

    if board.is_game_over():
        issue_link = settings['issues']['link'].format(
            repo=os.environ["GITHUB_REPOSITORY"],
            params=urlencode(settings['issues']['new_game']))
        return "**GAME IS OVER!** " + create_link("Click here", issue_link) + " to start a new game :D\n"

    if board.is_check():
        markdown += "**CHECK!** Choose your move wisely!\n\n"

    markdown += "|  FROM  | TO (Just click a link!) |\n"
    markdown += "| :----: | :---------------------- |\n"

    for source,dest in sorted(moves_dict.items()):
        markdown += "| **" + source + "** | " + create_issue_link(source, dest, settings) + " |\n"

    return markdown

def board_to_markdown(board):
    board_list = [[item for item in line.split(' ')] for line in str(board).split('\n')]
    markdown = ""

    # Direct CDN links for the chess pieces so no local images are needed
    images = {
        "r": "https://raw.githubusercontent.com/marcizhu/readme-chess/master/img/black/rook.svg",
        "n": "https://raw.githubusercontent.com/marcizhu/readme-chess/master/img/black/knight.svg",
        "b": "https://raw.githubusercontent.com/marcizhu/readme-chess/master/img/black/bishop.svg",
        "q": "https://raw.githubusercontent.com/marcizhu/readme-chess/master/img/black/queen.svg",
        "k": "https://raw.githubusercontent.com/marcizhu/readme-chess/master/img/black/king.svg",
        "p": "https://raw.githubusercontent.com/marcizhu/readme-chess/master/img/black/pawn.svg",

        "R": "https://raw.githubusercontent.com/marcizhu/readme-chess/master/img/white/rook.svg",
        "N": "https://raw.githubusercontent.com/marcizhu/readme-chess/master/img/white/knight.svg",
        "B": "https://raw.githubusercontent.com/marcizhu/readme-chess/master/img/white/bishop.svg",
        "Q": "https://raw.githubusercontent.com/marcizhu/readme-chess/master/img/white/queen.svg",
        "K": "https://raw.githubusercontent.com/marcizhu/readme-chess/master/img/white/king.svg",
        "P": "https://raw.githubusercontent.com/marcizhu/readme-chess/master/img/white/pawn.svg",

        ".": "https://raw.githubusercontent.com/marcizhu/readme-chess/master/img/blank.png"
    }

    # Write header in Markdown format
    if board.turn == chess.BLACK:
        markdown += "|   | H | G | F | E | D | C | B | A |   |\n"
    else:
        markdown += "|   | A | B | C | D | E | F | G | H |   |\n"
    markdown += "|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|\n"

    # Get Rows
    rows = range(1, 9)
    if board.turn == chess.BLACK:
        rows = reversed(rows)

    # Write board
    for row in rows:
        markdown += "| **" + str(9 - row) + "** | "
        columns = board_list[row - 1]
        if board.turn == chess.BLACK:
            columns = reversed(columns)

        for elem in columns:
            markdown += '<img src="{}" width=50px> | '.format(images.get(elem, "???"))

        markdown += "**" + str(9 - row) + "** |\n"

    # Write footer in Markdown format
    if board.turn == chess.BLACK:
        markdown += "|   | **H** | **G** | **F** | **E** | **D** | **C** | **B** | **A** |   |\n"
    else:
        markdown += "|   | **A** | **B** | **C** | **D** | **E** | **F** | **G** | **H** |   |\n"

    return markdown

def main(issue, issue_author, repo_owner):
    action = parse_issue(issue.title)
    gameboard = chess.Board()

    with open('data/settings.yaml', 'r') as settings_file:
        settings = yaml.load(settings_file, Loader=yaml.FullLoader)

    if action[0] == Action.NEW_GAME:
        if os.path.exists('games/current.pgn') and issue_author != repo_owner:
            issue.create_comment(settings['comments']['invalid_new_game'].format(author=issue_author))
            issue.edit(state='closed')
            return False, 'ERROR: A current game is in progress. Only the repo owner can start a new game'

        issue.create_comment(settings['comments']['successful_new_game'].format(author=issue_author))
        issue.edit(state='closed')

        with open('data/last_moves.txt', 'w') as last_moves:
            last_moves.write('Start game: ' + issue_author + '\n')

        # Create new game
        game = chess.pgn.Game()
        game.headers['Event'] = repo_owner + '\'s Online Open Chess Tournament'
        game.headers['Site'] = 'https://github.com/' + os.environ['GITHUB_REPOSITORY']
        game.headers['Date'] = datetime.now().strftime('%Y.%m.%d')
        game.headers['Round'] = '1'

    elif action[0] == Action.MOVE:
        if not os.path.exists('games/current.pgn'):
            return False, 'ERROR: There is no game in progress! Start a new game first'

        # Load game from "games/current.pgn"
        with open('games/current.pgn') as pgn_file:
            game = chess.pgn.read_game(pgn_file)
            gameboard = game.board()

        last_player = ""
        last_move = ""
        with open('data/last_moves.txt') as moves:
            line = moves.readline().strip()
            if line and ":" in line:
                last_player = line.split(':')[1].strip()
                last_move   = line.split(':')[0].strip()

        for move in game.mainline_moves():
            gameboard.push(move)

        if action[1][:2] == action[1][2:]:
            issue.create_comment(settings['comments']['invalid_move'].format(author=issue_author, move=action[1]))
            issue.edit(state='closed', labels=['Invalid'])
            return False, 'ERROR: Move is invalid!'

        # Try to move with promotion to queen
        if chess.Move.from_uci(action[1] + 'q') in gameboard.legal_moves:
            action = (action[0], action[1] + 'q')

        move = chess.Move.from_uci(action[1])

        # Check if player is moving twice in a row
        if last_player == issue_author and 'Start game' not in last_move:
            issue.create_comment(settings['comments']['consecutive_moves'].format(author=issue_author))
            issue.edit(state='closed', labels=['Invalid'])
            return False, 'ERROR: Two moves in a row!'

        # Check if move is valid
        if move not in gameboard.legal_moves:
            issue.create_comment(settings['comments']['invalid_move'].format(author=issue_author, move=action[1]))
            issue.edit(state='closed', labels=['Invalid'])
            return False, 'ERROR: Move is invalid!'

        # Check if board is valid
        if not gameboard.is_valid():
            issue.create_comment(settings['comments']['invalid_board'].format(author=issue_author))
            issue.edit(state='closed', labels=['Invalid'])
            return False, 'ERROR: Board is invalid!'

        issue_labels = ['⚔️ Capture!'] if gameboard.is_capture(move) else []
        issue_labels += ['White' if gameboard.turn == chess.WHITE else 'Black']

        issue.create_comment(settings['comments']['successful_move'].format(author=issue_author, move=action[1]))
        issue.edit(state='closed', labels=issue_labels)

        update_last_moves(action[1] + ': ' + issue_author)
        update_top_moves(issue_author)

        # Perform move
        gameboard.push(move)
        game.end().add_main_variation(move, comment=issue_author)
        game.headers['Result'] = gameboard.result()

    elif action[0] == Action.UNKNOWN:
        issue.create_comment(settings['comments']['unknown_command'].format(author=issue_author))
        issue.edit(state='closed', labels=['Invalid'])
        return False, 'ERROR: Unknown action'

    # Save game to "games/current.pgn"
    print(game, file=open('games/current.pgn', 'w'), end='\n\n')

    last_moves_rendered = generate_last_moves(settings)

    # If it is a game over, archive current game
    if gameboard.is_game_over():
        win_msg = {
            '1/2-1/2': 'It\'s a draw',
            '1-0': 'White wins',
            '0-1': 'Black wins'
        }

        with open('data/last_moves.txt', 'r') as last_moves_file:
            lines = last_moves_file.readlines()
            pattern = re.compile('.*: (@[a-z\\d](?:[a-z\\d]|-(?=[a-z\\d])){0,38})', flags=re.I)
            player_list = []
            for l in lines:
                m = re.match(pattern, l)
                if m:
                    player_list.append(m.group(1))
            player_list = list(set(player_list))

        if gameboard.result() == '1/2-1/2':
            issue.add_to_labels('👑 Draw!')
        else:
            issue.add_to_labels('👑 Winner!')

        issue.create_comment(settings['comments']['game_over'].format(
            outcome=win_msg.get(gameboard.result(), 'UNKNOWN'),
            players=', '.join(player_list),
            num_moves=len(lines)-1,
            num_players=len(player_list)))

        os.rename('games/current.pgn', datetime.now().strftime('games/game-%Y%m%d-%H%M%S.pgn'))
        # Reset files
        with open('data/last_moves.txt', 'w') as last_moves_file:
            last_moves_file.write('\n')

    with open('README.md', 'r') as file:
        readme = file.read()

    readme = replace_text_between(readme, settings['markers']['board'], board_to_markdown(gameboard))
    readme = replace_text_between(readme, settings['markers']['moves'], generate_moves_list(gameboard, settings))
    readme = replace_text_between(readme, settings['markers']['turn'], ('white' if gameboard.turn == chess.WHITE else 'black'))
    readme = replace_text_between(readme, settings['markers']['last_moves'], last_moves_rendered)
    readme = replace_text_between(readme, settings['markers']['top_moves'], generate_top_moves(settings))

    with open('README.md', 'w') as file:
        file.write(readme)

    return True, ''

if __name__ == '__main__':
    repo = Github(os.environ['GITHUB_TOKEN']).get_repo(os.environ['GITHUB_REPOSITORY'])
    issue = repo.get_issue(number=int(os.environ['ISSUE_NUMBER']))
    issue_author = '@' + issue.user.login
    repo_owner = '@' + os.environ['REPOSITORY_OWNER']

    ret, reason = main(issue, issue_author, repo_owner)
    if not ret:
        print(reason)
        sys.exit(1)
