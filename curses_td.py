#!/usr/bin/env python3

import copy
import curses
import time


MAX_ROWS, MAX_COLS = 25, 25
CELL_WIDTH = 3

CREEP_IMAGE = ' @ '
TOWER_IMAGE_1 = '***'
TOWER_IMAGE_2 = ':|:'
TOWER_IMAGE_3 = 'o-o'

FIElD_IMAGE = {'.': '. .', 'w': ' # ', 's': 'o> ', 'e': ' >o',
               'tc': TOWER_IMAGE_1, 'tm': TOWER_IMAGE_2, 'ts': TOWER_IMAGE_3}

TIME_DELAY = 100
CREEP_STATS = [{'hp': 50, 'count': 10, 'reward': 5},
               {'hp': 100, 'count': 10, 'reward': 5},
               {'hp': 300, 'count': 15, 'reward': 10},
               {'hp': 500, 'count': 20, 'reward': 10},
               {'hp': 10000, 'count': 1, 'reward': 100}]

START_GOLD = 100

TOWERS = {'c': {'damage': 5, 'speed': 20, 'range': 1, 'image': TOWER_IMAGE_1},
          'm': {'damage': 1, 'speed': 20, 'range': 5, 'image': TOWER_IMAGE_2},
          's': {'damage': 100, 'speed': 1, 'range': 10, 'image': TOWER_IMAGE_3}}

PRICES = {'c': 10, 'm':20, 's': 200}

HELP_INFO = "c - build chainsaw tower, m - build minigun tower, s - build sniper tower\n"\
            "space - send creeps now, costs: c - 5, m - 20, s - 200"

STATUS_LINE = "Gold: %s\t Round: %s\t Boss hp: %s\t Lifes: %s\t Kills: %s"

CREEP_INFO = 'Time before creep wave: %s. Creeps hp: %s,  number: %s'

ERROR_ROW = 26
CREEP_ROW = 27
STATUS_LINE_ROW = 28
HELP_INFO_ROW = 29

TIME_BETWEEN_WAVES = 60

FPS = 60

LIFES = 20


class ExitGame(Exception):
    pass


def is_number(string):
    try:
        _ = int(string)
        return True
    except:
        return False


class GameField():

    """ Class designed to load map from file and find path for creeps. """

    def __init__(self, field=None):
        self.field = field
        self.start_row = None
        self.start_col = None
        self.end_row = None
        self.end_col = None

    def load(self, filename):
        """ Load map from file. """
        with open(filename) as f:
            self.field = [line.split() for line in f]

    def find_cell(self, cell_value):
        """ Find coordinates of cell with given value. """
        for row in range(len(self.field)):
            for col in range(len(self.field[row])):
                if self.field[row][col] == cell_value:
                    return (row, col)

    def check_path(self, row, col):
        """ Check if any move is possible from cell with given row and col. """
        path = False
        if is_number(self.route[row][col]):
            value = int(self.route[row][col])
            if row > 0 and self.route[row-1][col] in ('.', 'e'):
                self.route[row-1][col] = value + 1
                path = True
            if row < len(self.route) - 1 and self.route[row+1][col] in ('.', 'e'):
                self.route[row+1][col] = value + 1
                path = True
            if col > 0 and self.route[row][col-1] in ('.', 'e'):
                self.route[row][col-1] = value + 1
                path = True
            if col < len(self.route[row]) - 1 and self.route[row][col+1] in ('.', 'e'):
                self.route[row][col+1] = value + 1
                path = True
        return path

    def build_route(self):
        """ Find route from start cell to end cell. """
        try:
            self.start_row, self.start_col = self.find_cell('s')
        except:
            raise Exception('Map is corrupted, can not find start point.')
        try:
            self.end_row, self.end_col = self.find_cell('e')
        except:
            raise Exception('Map is corrupted, can not find end point.')

        self.route = copy.deepcopy(self.field)
        self.route[self.start_row][self.start_col] = 0
        while True:
            path = False
            for row in range(len(self.route)):
                for col in range(len(self.route[row])):
                    path = True if self.check_path(row, col) else path
            if is_number(self.route[self.end_row][self.end_col]):
                break
            if not path:
                raise Exception('Bad map: can not build route from start to end.')
                break
        self.build_optimal_route()

    def find_next_cell(self, row, col):
        """ Find next cell in route from cell with given row and col. """
        value = int(self.route[row][col])
        if row > 0 and self.route[row-1][col] == value - 1:
            return row-1, col
        if row < len(self.route) - 1 and self.route[row+1][col] == value - 1:
            return row+1, col
        if col > 0 and self.route[row][col-1] == value - 1:
            return row, col-1
        if col < len(self.route[row]) - 1 and self.route[row][col+1] == value - 1:
            return row, col+1
        return row, col

    def build_optimal_route(self):
        """ Find the shortest route and remember it for creeps moving. """
        self.creep_path = []
        self.optimal_route = copy.deepcopy(self.field)
        row, col = self.end_row, self.end_col
        while True:
            self.optimal_route[row][col] = self.route[row][col]
            self.creep_path.append((row, col))
            if row == self.start_row and col == self.start_col:
                break
            row, col = self.find_next_cell(row, col)
        self.creep_path = self.creep_path[::-1]

class Cursor():

    """ Class designed to represent cursor which user can manipulate with. """

    def __init__(self, col, row, max_rows, max_cols):
        self.col = col
        self.row = row
        self.max_rows = max_rows
        self.max_cols = max_cols

    def move_up(self):
        if self.row > 0:
            self.row -= 1

    def move_down(self):
        if self.row < self.max_rows - 1:
            self.row += 1

    def move_left(self):
        if self.col > 0:
            self.col -= 1

    def move_right(self):
        if self.col < self.max_cols -1:
            self.col += 1

    def draw(self, stdscr):
        stdscr.addstr(self.row, self.col * CELL_WIDTH, '(')
        stdscr.addstr(self.row, (self.col+1) * CELL_WIDTH-1, ')')


class Creep():

    """ Class represents creep, which is moving from start to end point. """

    def __init__(self, start_row, start_col, hp, speed=1):
        self.row = start_row
        self.col = start_col
        self.hp = hp
        self.speed = speed

    def move(self, next_row, next_col):
        self.row = next_row
        self.col = next_col

    def draw(self, stdscr):
        stdscr.addstr(self.row, self.col * CELL_WIDTH, CREEP_IMAGE)

    def get_damage(self, damage):
        """ Receive damage from towers. """
        self.hp -= damage
        if self.hp < 0:
            self.hp == 0


class Tower():

    """ Class represents tower which can be built by player to destroy creeps. """

    def __init__(self, tower_type, row, col):
        self.range = TOWERS[tower_type]['range']
        self.damage = TOWERS[tower_type]['damage']
        self.speed = TOWERS[tower_type]['speed']
        self.image = TOWERS[tower_type]['image']
        self.target = None
        self.row = row
        self.col = col
        self.speed_points = FPS

    def find_target(self, creeps):
        """ Find first creep in tower's area of damage. """
        self.target = None
        for creep in creeps:
            if (abs(creep.row - self.row) <= self.range and
                abs(creep.col - self.col) <= self.range):
                self.target = creep

    def attack(self, creeps):
        """ Attack creep if it is possible. """
        self.find_target(creeps)
        if self.target:
            if self.speed_points >= FPS:
                self.target.get_damage(self.damage)
                self.speed_points = 0
            else:
                self.speed_points += self.speed

    def upgrade(self):
        """ Upgrade tower stats. """
        pass

    def draw(self, stdscr):
        stdscr.addstr(self.row, self.col * CELL_WIDTH, self.image)


class GameController():

    """ Class designed to control game flow, get user input, move creeps, etc. """

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.cursor = None

    def draw_field(self):
        """ Draw game field. """
        for row in range(self.field_rows):
            for col in range(self.field_cols):
                self.stdscr.addstr(row, col * CELL_WIDTH,
                                   FIElD_IMAGE[self.field[row][col]])

    def setup_level(self, level):
        """ Load appropriate map, nullify all stats. """
        map_name = 'map%s.txt' % (level,)
        gf = GameField()
        gf.load(map_name)
        gf.build_route()
        self.start_row = gf.start_row
        self.start_col = gf.start_col
        self.creep_path = gf.creep_path
        self.creeps = []
        self.field = gf.field
        self.route = gf.optimal_route
        self.field_rows = len(self.field)
        self.field_cols = len(self.field[0])
        self.cursor = Cursor(0, 0, self.field_rows, self.field_cols)
        self.lifes = LIFES
        self.towers = []
        self.gold = START_GOLD
        self.kills = 0

    def setup_round(self, round_number):
        """ Prepare next wave of creeps. """
        self.creep_hp = CREEP_STATS[round_number]['hp']
        self.creep_count = CREEP_STATS[round_number]['count']
        self.creep_reward = CREEP_STATS[round_number]['reward']
        self.level_round = round_number + 1
        self.boss = self.creep_hp if self.creep_count == 1 else 0
        self.boss_round = self.boss > 0

    def spawn_creep(self):
        """ Spawn new creep with current level stats. """
        self.creeps.append(Creep(self.start_row, self.start_col, self.creep_hp))

    def move_creeps(self):
        """ Move all creeps to next cell in route. """
        temp_creeps = []
        for creep in self.creeps:
            cell_index = self.creep_path.index((creep.row, creep.col))
            if cell_index >= len(self.creep_path) - 1:
                self.lifes -= 1
            else:
                temp_creeps.append(creep)
                row, col = self.creep_path[cell_index + 1]
                creep.move(row, col)
                creep.draw(self.stdscr)
        self.creeps = temp_creeps

    def build_tower(self, tower):
        """ Build tower in current cursor's place. """
        if self.field[self.cursor.row][self.cursor.col] == 'w':
            if self.gold >= PRICES[tower]:
                self.field[self.cursor.row][self.cursor.col] = 't%s' % (tower,)
                self.towers.append(Tower(tower, self.cursor.row, self.cursor.col))
                self.gold -= PRICES[tower]

    def action_per_time_tick(self, creep_count):
        """ Perform game actions per time tick. """
        for tower in self.towers:
            tower.attack(self.creeps)
        # remove dead creeps
        self.creeps = [creep for creep in self.creeps if creep.hp > 0]
        kills = creep_count - len(self.creeps)
        if kills > 0:
            self.gold += kills * self.creep_reward
            self.kills += kills

    def main_loop(self):
        tick = 0
        sec = TIME_BETWEEN_WAVES
        timer = time.time()
        creep_count = 0
        spawn_on = False
        next_round = False
        send_wave_finish = False
        sent_creeps = 0
        last_round = False
        while True:
            self.draw_field()
            new_time = time.time()
            if last_round and creep_count == 0:
                raise ExitGame

            if (new_time - timer) >= (1 / FPS):
                timer = new_time
                tick += 1
                self.action_per_time_tick(creep_count)
                creep_count = len(self.creeps)

            if tick == FPS:
                tick = 0
                sec -= 1
                self.stdscr.addstr(CREEP_ROW, 0, CREEP_INFO % (sec,
                                                               self.creep_hp,
                                                               self.creep_count))
                if spawn_on:
                    if sent_creeps < self.creep_count:
                        self.spawn_creep()
                        sent_creeps += 1
                    else:
                        spawn_on = False
                        sent_creeps = 0
                        send_wave_finish = True
                self.move_creeps()


            if sec == 0:
                sec = TIME_BETWEEN_WAVES
                spawn_on = True
                next_round = True

            if next_round and send_wave_finish:
                if self.level_round < len(CREEP_STATS):
                    self.setup_round(self.level_round)
                else:
                    last_round = True
                next_round = False
                send_wave_finish = False

            for creep in self.creeps:
                creep.draw(self.stdscr)

            if self.boss_round and len(self.creeps) > 0:
                self.boss = self.creeps[0].hp
            else:
                self.boss = 0
            self.cursor.draw(self.stdscr)
            self.stdscr.addstr(HELP_INFO_ROW, 0, HELP_INFO)
            status = STATUS_LINE % (self.gold, self.level_round,
                                    self.boss, self.lifes, self.kills)
            self.stdscr.addstr(STATUS_LINE_ROW, 0, status)
            self.stdscr.refresh()
            c = self.stdscr.getch()
            if c == ord('q'):
                raise ExitGame

            if c == ord(' '):
                sec = TIME_BETWEEN_WAVES
                spawn_on = True
                next_round = True

            if c in (curses.KEY_UP, ord('k'), ord('K')):
                self.cursor.move_up()
            if c in (curses.KEY_DOWN, ord('j'), ord('J')):
                self.cursor.move_down()
            if c in (curses.KEY_LEFT, ord('h'), ord('H')):
                self.cursor.move_left()
            if c in (curses.KEY_RIGHT, ord('l'), ord('L')):
                self.cursor.move_right()

            if c in (ord('c'), ord('m'), ord('s'), ord('C'), ord('M'), ord('S')):
                self.build_tower(chr(c).lower())

    def start_game(self):
        self.stdscr.nodelay(True)
        self.stdscr.clear()

        self.setup_level(1)
        self.setup_round(0)
        try:
            self.main_loop()
        except ExitGame:
            time.sleep(10)

def main(stdscr):
    # hide cursor by setting visibility to 0
    curses.curs_set(0)
    game = GameController(stdscr)
    game.start_game()


if __name__ == '__main__':
    curses.wrapper(main)
    print('The end')
    input('Press Enter to exit')
