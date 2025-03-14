# -*- coding: utf-8 -*-

import time
from math import ceil, floor

from typing import Optional, Any

from mcdreforged.api.types import PluginServerInterface, PlayerCommandSource
from mcdreforged.api.command import *
from mcdreforged.api.decorator import new_thread
from mcdreforged.api.utils import Serializable

class Config(Serializable):
    short_command: bool = True
    spec: int = 1
    spec_other: int = 2

# Initialize global variables
config: Config
data: dict
minecraft_data_api: Optional[Any]
plugin_name: str = '§r[§9FreeCam§r] §r'

# Define default configuration
DEFAULT_CONFIG = {
    'spec': 1,
    'spec_other': 2
}

PLAYER_GAME_TYPE = {
    0: 'survival',
    1: 'creative',
    2: 'adventure',
    3: 'spectator'
}


# Define help message
HELP_MESSAGE = f'''
{plugin_name} 帮助文档

§6!!spec §7灵魂出窍
§6!!spec <player> §7让他人灵魂出窍

§fTips：§7!!spec 可以简写为 !s
'''


def on_load(server: PluginServerInterface, prev_module):
    global config, data, plugin_name ,minecraft_data_api
    config = server.load_config_simple(
        'config.json',
        default_config=DEFAULT_CONFIG,
        target_class=Config
    )
    # Load data from file
    data = server.load_config_simple(
        'data.json',
        default_config={'data': {}},
        echo_in_console=False
    )['data']

    # Get Minecraft Data API instance
    minecraft_data_api = server.get_plugin_instance('minecraft_data_api')

    @new_thread('Gamemode switch')
    def change_mode(src: PlayerCommandSource, ctx):
        if src.is_console:
            return src.reply('§c仅允许玩家使用')
        
        player = src.player if ctx == {} else ctx['player']
        online_players = minecraft_data_api.get_server_player_list()
        # server.logger.info(online_players.players)
        if player not in online_players.players:
            return src.reply(f'{plugin_name}§c未找到玩家 §e{player}')

        if player not in data.keys():
            start_free_cam(server, player)
        elif player in data.keys():
            use_time_min = ceil((time.time() - data[player]['time']) / 60)
            server.tell(player, f'{plugin_name}§a您出窍了§e{use_time_min}分钟')
            quit_free_cam(server, player)

    # Register help message
    server.register_help_message('!!spec help', f'{plugin_name} 插件帮助')

    # Define spec literals
    spec_literals = ['!!spec']
    if config.short_command:
        spec_literals.append('!s')

    # Register commands
    server.register_command(
        Literal(spec_literals)
        .requires(
            lambda src: src.has_permission(config.spec),
            lambda src, ctx: '你没有权限这么做'
            )
        .runs(change_mode)
        .then(
            Literal('help')
            .runs(lambda src: src.reply(HELP_MESSAGE))
        )
        .then(
            Text('player')
            .requires(
                lambda src, ctx: src.has_permission(config.spec_other),
                lambda src, ctx: '你没有权限这么做'
            )
            .runs(change_mode)
        )
    )

def save_data(server: PluginServerInterface):
    server.save_config_simple({'data': data}, 'data.json')

def start_free_cam(server, player):
    dim = minecraft_data_api.get_player_info(player, 'Dimension')
    pos = minecraft_data_api.get_player_info(player, 'Pos')
    game_type = minecraft_data_api.get_player_info(player, 'playerGameType')
    # game_mode = PLAYER_GAME_TYPE.get(game_type,'unknow')
    now_time = time.time()

    data[player] = {
        'dim': dim,
        'pos': pos,
        'game_type': game_type,
        'time': now_time
    }
    server.execute(f'gamemode spectator {player}')
    save_data(server)
    server.tell(player,f'{plugin_name}§a已灵魂出窍~')
    server.logger.info(f'{player} started free cam at {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_time))}')

def quit_free_cam(server, player):
    dim = data[player]['dim']
    pos = [str(x) for x in data[player]['pos']]
    game_type = data[player]['game_type']
    game_mode = PLAYER_GAME_TYPE[game_type]
    now_time = time.time()

    server.execute('execute in {} run tp {} {}'.format(dim, player, ' '.join(pos)))
    server.execute(f'gamemode {game_mode} {player}')
    del data[player]
    save_data(server)
    server.tell(player,f'{plugin_name} §a已回到肉体 {game_mode}')
    server.logger.info(f'{player} quit free cam at {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_time))}')


def on_player_joined(server: PluginServerInterface, player, info):
    if player in data.keys():
        start_free_cam(server, player)
