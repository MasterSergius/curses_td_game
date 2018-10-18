#!/usr/bin/env python3

import copy
import curses
import random
import sys
import time


MAX_ROWS, MAX_COLS = 25, 25
CELL_WIDTH = 3

# colors
RED = 1
GREEN = 2
BLUE = 3
YELLOW = 4
WHITE = 5

CREEP_IMAGE = (' @ ', ' & ')
TOWER_IMAGE_1 = ('***', ' **', '** ')
TOWER_IMAGE_2 = (':|:', ':-:', '.|.')
TOWER_IMAGE_3 = ('o-o', '0-0', 'o=o')
TOWER_IMAGE_4 = ('>O<', '=O=', '>*<')

FIELD_IMAGE = {'.': ' . ', 'w': ' + ', 's': 'o> ', 'e': ' >o', 'b': ' # '}
FIELD_COLOR = {'.': WHITE, 'w': YELLOW, 's': RED, 'e': RED, 'b': BLUE}

TIME_DELAY = 100

START_GOLD = 50

TOWERS = {'c': {'damage': 6, 'speed': 6, 'range': 1, 'images': TOWER_IMAGE_1},
          'm': {'damage': 7, 'speed': 7, 'range': 6, 'images': TOWER_IMAGE_2},
          's': {'damage': 100, 'speed': 1, 'range': 10, 'images': TOWER_IMAGE_3,
                'special': 5},
          'i': {'damage': 1, 'speed': 1, 'range': 3, 'images': TOWER_IMAGE_4,
                'special': 1}}

PRICES = {'c': 5, 'm': 20, 's': 50, 'i': 100}
UPGRADE_STATS = {'c': {'damage': 1, 'speed': 1},
                 'm': {'damage': 3, 'speed': 3},
                 's': {'damage': 200, 'range': 1, 'special': 1},
                 'i': {'damage': 1, 'speed': 1, 'special': 2}}

TOWER_UPGRADE_PRICE_MULTIPLIER = 2
TOWER_DESTROY_PRICE_PERCENTAGE = 90
CRIT_MULTIPLIER = 20
TOWER_MAX_LEVEL = 10

HELP_INFO = "c - chainsaw tower, m - minigun tower, s - sniper tower, i - ice tower\n"\
            "u - upgrade tower, d - destroy tower, space - send creeps now\n"\
            "tower costs: chainsaw - %s, minigun - %s, sniper - %s, ice - %s" \
            % (PRICES['c'], PRICES['m'], PRICES['s'], PRICES['i'])

STATUS_LINE = "Gold: %s  Round: %s/%s  Boss hp: %s  Lifes: %s  Kills: %s"

CREEP_INFO = 'Time before creep wave: %s. Creeps hp: %s,  sent creeps: %s/%s'

ERROR_ROW = 26
CREEP_ROW = 27
STATUS_LINE_ROW = 28
HELP_INFO_ROW = 30

OBJECT_INFO_ROW = 5
OBJECT_INFO_COL = 80

TIME_BETWEEN_WAVES = 60

FPS = 60
ATTACK_SPEED_POINTS = 60
MOVE_SPEED_POINTS = 60

LIFES = 20

MAX_ROUNDS = 50
BOSS_ROUND = 10
CREEP_COUNT = 30
START_CREEP_HP = 100
START_CREEP_REWARD = 1
START_CREEP_SPEED = 2
CREEP_SPEED_UPGRADE = 0.1
CREEP_HP_LEVEL_MULTIPLIER = 100
BOSS_HP_MULTIPLY = 50
BOSS_REWARD_MULTIPLY = 30
BOSS_LIFES = 5
CREEP_REWARD_UPGRADE = 1


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

    def __init__(self, start_row, start_col, hp, reward, speed=1, boss=False):
        self.row = start_row
        self.col = start_col
        self.hp = hp
        self.reward = reward
        self.boss = boss
        self.speed = speed
        self.original_speed = speed
        self.move_points = 0
        self.image_set = CREEP_IMAGE
        self.image = 0

    def move(self, next_row, next_col):
        if self.move_points >= MOVE_SPEED_POINTS:
            self.row = next_row
            self.col = next_col
            self.move_points = 0
            self.image = 0
        else:
            self.move_points += self.speed

    def _next_image(self):
        """ Cycle over images to simulate animation. """
        self.image += 1
        if self.image >= len(self.image_set):
            self.image = 0

    def draw(self, stdscr):
        stdscr.addstr(self.row, self.col * CELL_WIDTH, self.image_set[self.image],
                      curses.color_pair(RED))

    def get_damage(self, damage):
        """ Receive damage from towers. """
        self.hp -= damage
        self._next_image()
        if self.hp < 0:
            self.hp == 0

    def slow_effect(self, slow_points):
        self.speed = self.original_speed - slow_points
        if self.speed < 1:
            self.speed = 1

    def clear_effects(self):
        self.speed = self.original_speed


class Tower():

    """ Class represents tower which can be built by player to destroy creeps. """

    def __init__(self, tower_type, row, col):
        self.tower_type = tower_type
        self.range = TOWERS[tower_type]['range']
        self.damage = TOWERS[tower_type]['damage']
        self.speed = TOWERS[tower_type]['speed']
        self.image_set = TOWERS[tower_type]['images']
        self.image = 0
        self.target = None
        self.row = row
        self.col = col
        self.speed_points = FPS
        self.price = PRICES[tower_type]
        self.level = 1

    def _next_image(self):
        """ Cycle over images to simulate animation. """
        self.image += 1
        if self.image >= len(self.image_set):
            self.image = 0

    def find_target(self, creeps):
        """ Find first creep in tower's area of damage. """
        self.target = None
        for creep in creeps:
            if (abs(creep.row - self.row) <= self.range and
                abs(creep.col - self.col) <= self.range):
                self.target = creep
                break

    def attack(self, creeps):
        """ Attack creep if it is possible. """
        self.find_target(creeps)
        if self.target:
            while self.speed_points >= ATTACK_SPEED_POINTS:
                self.target.get_damage(self.damage)
                self.speed_points -= ATTACK_SPEED_POINTS
            else:
                self.speed_points += self.speed
            self._next_image()
        else:
            self.image = 0

    def upgrade(self):
        """ Upgrade tower stats. """
        if 'damage' in UPGRADE_STATS[self.tower_type]:
            self.damage += UPGRADE_STATS[self.tower_type]['damage'] * self.level
        if 'speed' in UPGRADE_STATS[self.tower_type]:
            self.speed += UPGRADE_STATS[self.tower_type]['speed'] * self.level
        self.range += UPGRADE_STATS[self.tower_type].get('range', 0)
        self.price += self.level * PRICES[self.tower_type] * TOWER_UPGRADE_PRICE_MULTIPLIER
        self.level += 1

    def draw(self, stdscr):
        stdscr.addstr(self.row, self.col * CELL_WIDTH,
                      self.image_set[self.image], curses.color_pair(GREEN))

    def get_special(self):
        return 'no specials'


class TowerChainsaw(Tower):
    """ Chainsaw tower damage multiple creeps at once. """

    def find_target(self, creeps):
        self.target = []
        for creep in creeps:
            if (abs(creep.row - self.row) <= self.range and
                abs(creep.col - self.col) <= self.range):
                self.target.append(creep)

    def attack(self, creeps):
        self.find_target(creeps)
        if self.target:
            while self.speed_points >= ATTACK_SPEED_POINTS:
                for target in self.target:
                    target.get_damage(self.damage)
                self.speed_points -= ATTACK_SPEED_POINTS
            else:
                self.speed_points += self.speed
            self._next_image()
        else:
            self.image = 0

    def get_special(self):
        return 'damage all in range'


class TowerMinigun(Tower):
    """ Minigun tower. No specials. """

    pass


class TowerSniper(Tower):
    """ Sniper tower. Have chance for critical shot. """

    def __init__(self, tower_type, row, col):
        super().__init__(tower_type, row, col)
        self.crit_chance = TOWERS[self.tower_type]['special']

    def attack(self, creeps):
        """ Attack creep if it is possible. """
        self.find_target(creeps)
        if self.target:
            while self.speed_points >= ATTACK_SPEED_POINTS:
                chance = random.randint(0, 100)
                damage = (self.damage * CRIT_MULTIPLIER
                          if chance <= self.crit_chance else self.damage)
                self.target.get_damage(damage)
                self.speed_points -= ATTACK_SPEED_POINTS
            else:
                self.speed_points += self.speed
            self._next_image()
        else:
            self.image = 0

    def upgrade(self):
        super().upgrade()
        self.crit_chance += UPGRADE_STATS[self.tower_type]['special']

    def get_special(self):
        return '%sx crit, %s%% chance' % (CRIT_MULTIPLIER, self.crit_chance)


class TowerIce(Tower):
    """ Ice tower. Slow multiple creeps. """

    def __init__(self, tower_type, row, col):
        super().__init__(tower_type, row, col)
        self.slow_points = TOWERS[self.tower_type]['special']

    def upgrade(self):
        super().upgrade()
        self.slow_points += UPGRADE_STATS[self.tower_type]['special']

    def find_target(self, creeps):
        self.target = []
        for creep in creeps:
            if (abs(creep.row - self.row) <= self.range and
                abs(creep.col - self.col) <= self.range):
                self.target.append(creep)

    def attack(self, creeps):
        self.find_target(creeps)
        if self.target:
            while self.speed_points >= ATTACK_SPEED_POINTS:
                for target in self.target:
                    target.get_damage(self.damage)
                    target.slow_effect(self.slow_points)
                self.speed_points -= ATTACK_SPEED_POINTS
            else:
                self.speed_points += self.speed
            self._next_image()
        else:
            self.image = 0

    def get_special(self):
        return 'slow in range, %s pts' % (self.slow_points,)


class TowerFactory():
    def __new__(self, tower_type, row, col):
        if tower_type == 'c':
            return TowerChainsaw(tower_type, row, col)
        elif tower_type == 'm':
            return TowerMinigun(tower_type, row, col)
        elif tower_type == 's':
            return TowerSniper(tower_type, row, col)
        elif tower_type == 'i':
            return TowerIce(tower_type, row, col)
        else:
            raise ValueError


class GameController():

    """ Class designed to control game flow, get user input, move creeps, etc. """

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.cursor = None

    def draw_field(self):
        """ Draw game field. """
        for row in range(self.field_rows):
            for col in range(self.field_cols):
                cell = self.field[row][col]
                self.stdscr.addstr(row, col * CELL_WIDTH,
                                   FIELD_IMAGE[cell],
                                   curses.color_pair(FIELD_COLOR[cell]))

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
        # used for initial creep info
        self.creep_hp = START_CREEP_HP
        self.level_round = 0
        self.creep_count = 0

    def setup_round(self, round_number):
        """ Prepare next wave of creeps. """
        self.level_round = round_number + 1
        self.boss_round = True if self.level_round % BOSS_ROUND == 0 else False

        if self.level_round == 1:
            self.creep_hp = START_CREEP_HP
            self.temp_creep_hp = START_CREEP_HP
            self.creep_reward = START_CREEP_REWARD
            self.temp_creep_reward = START_CREEP_REWARD
            self.creep_count = CREEP_COUNT
            self.creep_speed = START_CREEP_SPEED
        else:
            self.creep_hp = self.temp_creep_hp
            self.creep_reward = self.temp_creep_reward
            if self.boss_round:
                self.creep_count = 1
                self.temp_creep_hp = self.creep_hp
                self.creep_hp *= BOSS_HP_MULTIPLY
                self.creep_reward *= BOSS_REWARD_MULTIPLY
            else:
                self.creep_count = CREEP_COUNT
                self.creep_hp += (self.level_round - 1) * CREEP_HP_LEVEL_MULTIPLIER
                self.temp_creep_hp = self.creep_hp
                self.creep_reward += CREEP_REWARD_UPGRADE
                self.temp_creep_reward = self.creep_reward
                self.creep_speed += CREEP_SPEED_UPGRADE

    def spawn_creep(self):
        """ Spawn new creep with current level stats. """
        self.creeps.append(Creep(self.start_row, self.start_col, self.creep_hp,
                                 self.creep_reward, speed=self.creep_speed,
                                 boss=self.boss_round))
        if self.boss_round:
            self.boss = self.creeps[0]
        else:
            self.boss = None

    def move_creeps(self):
        """ Move all creeps to next cell in route. """
        temp_creeps = []
        for creep in self.creeps:
            cell_index = self.creep_path.index((creep.row, creep.col))
            if cell_index >= len(self.creep_path) - 1:
                if creep.boss:
                    self.lifes -= BOSS_LIFES
                else:
                    self.lifes -= 1
                if self.lifes <= 0:
                    raise ExitGame
            else:
                temp_creeps.append(creep)
                row, col = self.creep_path[cell_index + 1]
                creep.move(row, col)
                creep.draw(self.stdscr)
        self.creeps = temp_creeps

    def is_free_place_for_tower(self, row=None, col=None):
        """ Check if tower can be built in current cursor's place. """
        if not row and not col:
            row = self.cursor.row
            col = self.cursor.col
        for tower in self.towers:
            if tower.row == row and tower.col == col:
                return False
        return self.field[row][col] == 'w'

    def build_tower(self, tower):
        """ Build tower in current cursor's place. """
        if self.is_free_place_for_tower():
            if self.gold >= PRICES[tower]:
                self.towers.append(TowerFactory(tower, self.cursor.row, self.cursor.col))
                self.gold -= PRICES[tower]

    def destroy_tower(self):
        """ Destroy tower in current cursor's place. """
        new_tower_list = []
        for tower in self.towers:
            if tower.row == self.cursor.row and tower.col == self.cursor.col:
                self.gold += tower.price * TOWER_DESTROY_PRICE_PERCENTAGE // 100
            else:
                new_tower_list.append(tower)
        self.towers = new_tower_list

    def upgrade_tower(self):
        """ Upgrade tower in current cursor's place. """
        for tower in self.towers:
            if tower.row == self.cursor.row and tower.col == self.cursor.col:
                upgrade_price = tower.level * PRICES[tower.tower_type] * TOWER_UPGRADE_PRICE_MULTIPLIER
                if self.gold >= upgrade_price and tower.level < TOWER_MAX_LEVEL:
                    tower.upgrade()
                    self.gold -= upgrade_price
                break

    def action_per_time_tick(self, creep_count):
        """ Perform game actions per time tick. """
        for tower in self.towers:
            tower.attack(self.creeps)
        # remove dead creeps
        alive_creeps = []
        for creep in self.creeps:
            if creep.hp <= 0:
                self.kills += 1
                self.gold += creep.reward
            else:
                alive_creeps.append(creep)
        self.creeps = alive_creeps
        self.move_creeps()

    def show_object_under_cursor(self):
        tower_info_template = 'Tower\n\nDamage: %s\nRange: %s\nSpeed: %s\n'\
                              'Upgrade price: %s\nDestroy price: %s\n'\
                              'Special: %s\nLevel: %s/%s'
        for offset in range(len(tower_info_template.split('\n'))):
            self.stdscr.addstr(OBJECT_INFO_ROW + offset, OBJECT_INFO_COL, ' ' * 30)
            offset += 1
        for tower in self.towers:
            if tower.row == self.cursor.row and tower.col == self.cursor.col:
                obj_info = tower_info_template \
                           % (tower.damage, tower.range, tower.speed,
                              tower.level  * PRICES[tower.tower_type] * TOWER_UPGRADE_PRICE_MULTIPLIER,
                              tower.price * TOWER_DESTROY_PRICE_PERCENTAGE // 100,
                              tower.get_special(), tower.level, TOWER_MAX_LEVEL)
                offset = 0
                for line in obj_info.split('\n'):
                    self.stdscr.addstr(OBJECT_INFO_ROW + offset, OBJECT_INFO_COL, line)
                    offset += 1

    def is_start_free(self):
        for creep in self.creeps:
            if creep.row == self.start_row and creep.col == self.start_col:
                return False
        return True

    def main_loop(self):
        tick = 0
        sec = TIME_BETWEEN_WAVES
        timer = time.time()
        creep_count = 0
        spawn_on = False
        next_round = False
        send_wave_finish = True
        sent_creeps = 0
        last_round = False
        self.boss = None
        while True:
            if not self.pause:
                self.draw_field()
                for tower in self.towers:
                    tower.draw(self.stdscr)

                new_time = time.time()
                if last_round and creep_count == 0:
                    raise ExitGame

                if (new_time - timer) >= (1 / FPS):
                    timer = new_time
                    tick += 1
                    self.action_per_time_tick(creep_count)
                    creep_count = len(self.creeps)

                    if spawn_on:
                        if sent_creeps < self.creep_count:
                            if self.is_start_free():
                                self.spawn_creep()
                                sent_creeps += 1
                        else:
                            spawn_on = False
                            sent_creeps = 0
                            send_wave_finish = True

                    self.stdscr.addstr(CREEP_ROW, 0, ' ' * 100)
                    self.stdscr.addstr(CREEP_ROW, 0, CREEP_INFO % (sec,
                                                                   self.creep_hp,
                                                                   sent_creeps,
                                                                   self.creep_count))

                if tick == FPS:
                    for creep in self.creeps:
                        creep.clear_effects()
                    tick = 0
                    sec -= 1

                if (sec == 0 or next_round) and send_wave_finish:
                    if  self.level_round < MAX_ROUNDS:
                        self.setup_round(self.level_round)
                    else:
                        last_round = True
                    sec = TIME_BETWEEN_WAVES
                    spawn_on = True
                    next_round = False
                    send_wave_finish = False

                boss_hp = 0
                for creep in self.creeps:
                    creep.draw(self.stdscr)
                    if creep.boss:
                        boss_hp = creep.hp

                self.cursor.draw(self.stdscr)
                self.stdscr.addstr(HELP_INFO_ROW, 0, HELP_INFO)
                status = STATUS_LINE % (self.gold, self.level_round, MAX_ROUNDS,
                                        boss_hp, self.lifes, self.kills)
                self.stdscr.addstr(STATUS_LINE_ROW, 0, ' ' * 100)
                self.stdscr.addstr(STATUS_LINE_ROW, 0, status)
                self.show_object_under_cursor()
                self.stdscr.refresh()

            c = self.stdscr.getch()
            if c in (ord('q'), ord('Q')):
                raise ExitGame

            if c in (ord('p'), ord('P')):
                self.pause = not self.pause

            if not self.pause:
                if c == ord(' '):
                    next_round = True

                if c in (curses.KEY_UP, ord('k'), ord('K')):
                    self.cursor.move_up()
                if c in (curses.KEY_DOWN, ord('j'), ord('J')):
                    self.cursor.move_down()
                if c in (curses.KEY_LEFT, ord('h'), ord('H')):
                    self.cursor.move_left()
                if c in (curses.KEY_RIGHT, ord('l'), ord('L')):
                    self.cursor.move_right()

                if c in (ord('c'), ord('C'), ord('m'), ord('M'),
                         ord('s'), ord('S'), ord('i'), ord('I')):
                    self.build_tower(chr(c).lower())

                if c in (ord('d'), ord('D')):
                    self.destroy_tower()

                if c in (ord('u'), ord('U')):
                    self.upgrade_tower()

    def start_game(self):
        self.stdscr.nodelay(True)
        self.stdscr.clear()

        self.pause = False
        try:
            self.main_loop()
        except ExitGame:
            pass


class MainMenu():

    """ Class responsible for Main Menu which appears on start. """

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.top_row = 10
        self.left_col = 20
        self.cursor_row = 0
        self.maps = [1, 2, 3, 4, 5]
        self.difficulties = ['Easy', 'Medium', 'Hard']
        self.selected_map = 0
        self.selected_difficulty = 0
        self.text_map_template = 'Select map: %s'
        self.text_difficulty_template = 'Select difficulty: %s'
        self.text_start = 'Start'
        self.text_exit = 'Exit'

    @property
    def text_map(self):
        return self.text_map_template % (self.maps[self.selected_map],)

    @property
    def text_difficulty(self):
        return self.text_difficulty_template % (self.difficulties[self.selected_difficulty],)

    def show_menu(self):
        self.stdscr.addstr(self.top_row, self.left_col,
                           self.text_map.center(30))
        self.stdscr.addstr(self.top_row+1, self.left_col,
                           self.text_difficulty.center(30))
        self.stdscr.addstr(self.top_row+2, self.left_col,
                           self.text_start.center(30))
        self.stdscr.addstr(self.top_row+3, self.left_col,
                           self.text_exit.center(30))

    def show_cursor(self):
        self.stdscr.addstr(self.top_row+self.cursor_row, self.left_col-1, '<',
                           curses.color_pair(GREEN))
        self.stdscr.addstr(self.top_row+self.cursor_row, self.left_col+30, '>',
                           curses.color_pair(GREEN))

    def hide_cursor(self):
        self.stdscr.addstr(self.top_row+self.cursor_row, self.left_col-1, ' ')
        self.stdscr.addstr(self.top_row+self.cursor_row, self.left_col+30, ' ')

    def move_cursor(self, direction):
        self.hide_cursor()
        self.cursor_row += direction
        # 4 menu items - [0..3]
        if self.cursor_row < 0:
            self.cursor_row = 3
        if self.cursor_row > 3:
            self.cursor_row = 0
        self.show_cursor()

    def scroll_item(self, direction):
        if self.cursor_row == 0:
            self.selected_map += direction
            if self.selected_map < 0:
                self.selected_map = len(self.maps) - 1
            if self.selected_map > len(self.maps) - 1:
                self.selected_map = 0

        if self.cursor_row == 1:
            self.selected_difficulty += direction
            if self.selected_difficulty < 0:
                self.selected_difficulty = len(self.difficulties) - 1
            if self.selected_difficulty > len(self.difficulties) - 1:
                self.selected_difficulty = 0

    def enter_menu(self):
        if self.cursor_row == 2:
            game = GameController(self.stdscr)
            game.setup_level(self.selected_map + 1)
            game.start_game()
        if self.cursor_row == 3:
            sys.exit(0)

    def main_loop(self):
        while True:
            self.show_menu()
            self.show_cursor()
            self.stdscr.refresh()

            c = self.stdscr.getch()
            if c in (curses.KEY_UP, ord('k'), ord('K')):
                self.move_cursor(-1)
            if c in (curses.KEY_DOWN, ord('j'), ord('J')):
                self.move_cursor(1)
            if c in (curses.KEY_LEFT, ord('h'), ord('H')):
                self.scroll_item(-1)
            if c in (curses.KEY_RIGHT, ord('l'), ord('L')):
                self.scroll_item(1)

            if c in (curses.KEY_ENTER, 10, 13):
                self.enter_menu()


def main(stdscr):
    # hide cursor by setting visibility to 0
    curses.curs_set(0)
    curses.start_color()
    curses.init_pair(WHITE, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(RED, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(GREEN, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(BLUE, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(YELLOW, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    menu = MainMenu(stdscr)
    menu.main_loop()


if __name__ == '__main__':
    curses.wrapper(main)
    print('The end')
    input('Press Enter to exit')
