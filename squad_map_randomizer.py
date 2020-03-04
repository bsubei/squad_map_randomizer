#! /usr/bin/env python3

# Copyright (C) 2019 Basheer Subei
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.
#
# A script that generates a randomized Squad Map Rotation according to a certain pattern.
#

import argparse
import collections
import copy
import datetime
from discord_webhook import DiscordWebhook
import json
import logging
import os
import pathlib
import random
from urllib import request
import yaml

# The number of skirmish maps to add to beginning of map rotation.
NUM_STARTING_SKIRMISH_MAPS = 2
# The number of times to repeat the AAS/RAAS/Invasion pattern.
NUM_REPEATING_PATTERN = 5
# A layer will be discarded if a layer with the same map was last played this many layers ago.
NUM_MIN_LAYERS_BEFORE_DUPLICATE_MAP = 3

# The path to the current directory as a pathlib.Path object.
CURRENT_DIR = pathlib.Path(os.path.dirname(__file__))
# Use the current working directory for MapRotation file and the default name.
DEFAULT_MAP_ROTATION_FILEPATH = CURRENT_DIR / pathlib.Path('MapRotation.cfg')
# The path to the configs directory.
CONFIG_DIR = CURRENT_DIR / pathlib.Path('configs')
# The path to the example configs directory.
EXAMPLES_CONFIG_DIR = CONFIG_DIR / pathlib.Path('examples')
# The default filepath to get the rotation config from.
DEFAULT_CONFIG_FILEPATH = CONFIG_DIR / pathlib.Path('default_config.yml')
# The default URL to use to fetch the Squad map layers.
DEFAULT_LAYERS_URL = 'https://raw.githubusercontent.com/bsubei/squad_map_layers/master/layers.json'


class InvalidConfigException(Exception):
    """ Exception raised when a config is invalid. """
    pass


def parse_cli():
    """ Parses sys.argv (commandline args) and returns a parser with the arguments. """
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output-filepath', default=DEFAULT_MAP_ROTATION_FILEPATH, type=pathlib.Path,
                        help=f'Filepath to write out map rotation to. Defaults to {DEFAULT_MAP_ROTATION_FILEPATH}')
    parser.add_argument('-c', '--config-filepath', default=DEFAULT_CONFIG_FILEPATH, type=pathlib.Path,
                        help=f'Filepath to read rotation config from. Defaults to {DEFAULT_CONFIG_FILEPATH}.')
    parser.add_argument('--discord-webhook-url', required=False,
                        help=('The URL to the Discord webhook if you want to post the latest rotation to a Discord'
                              ' channel.'))
    # Expect either an input filepath or URL.
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        '--input-filepath', help='Filepath of JSON file to use for map layers.')
    input_group.add_argument('--input-url', default=DEFAULT_LAYERS_URL,
                             help=(f'URL to JSON file to use for map layers. Defaults to {DEFAULT_LAYERS_URL} if'
                                   ' --input-filepath is not provided.'))
    return parser.parse_args()


def get_json_layers(input_filepath, input_url):
    """
    Return the JSON object represented by the given filepath or URL (in the args) as a list of dicts. See
    https://github.com/bsubei/squad_map_layers for an example layers JSON file.
    """
    # Parse the filepath as JSON if it's provided.
    if input_filepath:
        # Just read the JSON file from a filepath and
        with open(input_filepath, 'rb') as f:
            all_layers = json.load(f)
    # Otherwise, fetch the JSON file from the URL and parse it into a list of dicts.
    elif input_url:
        text = request.urlopen(input_url).read().decode('utf-8')
        all_layers = json.loads(text)
    else:
        raise ValueError('Sanity check failed! No input args provided!')

    # Filter out all the bugged layers and return that.
    return list(filter(lambda m: not m['bugged'], all_layers))


def get_random_skirmish_layer(input_filepath, input_url):
    """ Return one random skirmish layer as a string from either the given filepath or URL to the JSON layers file. """
    layers = get_json_layers(input_filepath, input_url)
    remaining_skirmish_layers = list(
        filter(lambda m: m['gamemode'] == 'Skirmish', layers))
    return get_layers([random.choice(remaining_skirmish_layers)])[0]


def get_nonduplicate_map(available_layers, chosen_rotation, min_layers_before_duplicate_map):
    """
    Given the available layers to choose from, the current chosen_rotation, and the number of layers to check behind
    for a duplicate map, randomly chooses and returns a layer that follows the global filter rules (see README.md).

    :param available_layers:  A list of available layers to choose from (as dicts derived from the JSON object).
    :param chosen_rotation:  The list of currently chosen layers.
    :param min_layers_before_duplicate_map:  The number of maps before a duplicate map is allowed.
    :return: A randomly chosen layer that follows the global filter rules.
    """
    # Clamp min_layers_before_duplicate map so it doesn't go out of bounds.
    min_layers_before_duplicate_map = max(
        1, min(len(chosen_rotation), min_layers_before_duplicate_map))

    # Attempt to get a valid layer that doesn't break the global duplicate rules (don't duplicate same exact layer, and
    # layers with the same map must not be consecutive). If we can't, print an error and return the best choice we can.
    layers_to_avoid_duplicating = chosen_rotation[-min_layers_before_duplicate_map:]
    for _ in range(100):
        candidate_layer = random.choice(available_layers)
        if candidate_layer['map'] not in [layer['map'] for layer in layers_to_avoid_duplicating]:
            # If the layers follows the rules, add it to the chosen rotation.
            return candidate_layer
        else:
            # Otherwise, try again.
            previous_layers_string = ', '.join(
                [layer['layer'] for layer in layers_to_avoid_duplicating])
            logging.debug('Discarding chosen layer {} because it has the same map as the previous layers {}.'.format(
                candidate_layer['layer'], previous_layers_string))

    # If we still can't find a valid layer, return the best we can after printing an error.
    logging.error(f'Could not get a valid map without duplicates! Choosing {candidate_layer["layer"]} anyways!')
    return candidate_layer


def get_map_rotation(
        rotation_config,
        all_layers,
        num_min_layers_before_duplicate_map=NUM_MIN_LAYERS_BEFORE_DUPLICATE_MAP):
    """
    Given all the layers to choose from, return a map rotation according to the global filters and the filters defined
    in the given config.

    :param rotation_config: dict The config that describes how to choose the rotation.
    :param all_layers: list(dict) The list of layers to choose the rotation from.
    :param num_min_layers_before_duplicate_map: The allowed distance between layers with duplicate maps.
    """

    def upgrade_to_list(value):
        return value if isinstance(value, list) else [value]

    def apply_filter_config(remaining_layers, filter_config):
        """ From the remaining_layers, filter using the config and return the filtered layers.  """
        # Use filtered_layers as the result of filtering remaining_layers based on the config.
        filtered_layers = remaining_layers

        # NOTE(bsubei): multiple filter keys apply an "AND" operation. However, multiple values in one filter key apply
        # an "OR" operation.
        # e.g. given filter 1 is {'gamemode': ['AAS', 'RAAS']} and filter 2 is {'map_size': 'small'}, then the chosen
        # layer will be either AAS **or** RAAS **and** either way must be a small size map.

        # Skips filters if the special 'any' keyword is used.
        should_skip_filter = isinstance(
            filter_config, str) and filter_config.casefold() == 'any'
        if not should_skip_filter:
            for key, value in filter_config.items():
                # We upgrade key and value to lists if they weren't already so we can use "in" instead of "==".
                value = upgrade_to_list(value)
                key = upgrade_to_list(key)
                # The 'team' key is special and counts as either 'team1' or 'team2'.
                if 'team' in key:
                    key = ['team1', 'team2']
                # Apply the current filter again and again until filtered_layers passes all the filters "AND"ed
                # together.
                filtered_layers = [
                    layer for layer in filtered_layers for k in key if layer.get(k) in value]
        return filtered_layers

    def populate_chosen_rotation(chosen_rotation, remaining_layers, maps_config):
        """
        Populate the given chosen_rotation list from remaining_layers (using sample without replacement) by applying the
        maps_config filters.
        NOTE: this mutates both chosen_rotation and remaining_layers as they are passed by reference.
        """
        for idx, filter_config in enumerate(maps_config):
            filtered_layers = apply_filter_config(
                remaining_layers, filter_config)
            # If no layers pass the filters, print an error and move on.
            if not filtered_layers:
                logging.error(f'No maps to choose from after applying filter {filter_config}! Skipping this filter!')
                continue

            # After we've filtered layers according to the filter config, randomly choose a layer that follows the
            # global filter rules.
            chosen_layer = get_nonduplicate_map(
                filtered_layers, chosen_rotation, num_min_layers_before_duplicate_map)
            chosen_rotation.append(chosen_layer)
            # Remove it from the pool since we used it (using without replacement policy).
            remaining_layers.remove(chosen_layer)

    # Make a copy of the layers so we can sample from it without replacement.
    remaining_layers = copy.deepcopy(all_layers)

    # The chosen rotation will be stored here (as a list of layer dicts).
    chosen_rotation = []

    # Get the config section for starting_maps.
    starting_maps_config = rotation_config.get('starting_maps', [])

    # Fill up the chosen_rotation from remaining_layers by applying starting_maps_config.
    # NOTE(bsubei): both chosen_rotation and remaining_layers are passed by reference and mutated in the function.
    populate_chosen_rotation(
        chosen_rotation, remaining_layers, starting_maps_config)

    # Now do it again number_of_repeats times for regular_maps_config.
    number_of_repeats = rotation_config.get('number_of_repeats', 1)
    regular_maps_config = rotation_config.get('regular_maps')
    for _ in range(number_of_repeats):
        populate_chosen_rotation(
            chosen_rotation, remaining_layers, regular_maps_config)

    return chosen_rotation


def get_layers_string(map_rotation):
    """ Returns all the layers from the given map rotation as a string with newlines. """
    return '\n'.join([layer['layer'] for layer in map_rotation])


def get_layers(map_rotation):
    """ Returns all the layers from the given map rotation as a list of strings. """
    return [layer['layer'] for layer in map_rotation]


def write_rotation(map_rotation, output_filepath):
    """ Writes out given map rotation (list of dicts) to the given output filepath as a map rotation. """
    with open(output_filepath, 'w') as f:
        f.write(get_layers_string(map_rotation))


def send_rotation_to_discord(map_rotation, discord_webhook_url):
    """ Sends the map rotation as a message to the discord channel for the given webhook URL. """
    if discord_webhook_url:
        # Need to pretty up the discord message string first.
        discord_message = 'The map rotation for {} is:\n```{}```'.format(
            datetime.date.today(), get_layers_string(map_rotation))
        webhook = DiscordWebhook(
            url=discord_webhook_url, content=discord_message)
        webhook.execute()


def validate_helper(config, layers):
    """
    A helper function to validate that each filter in the given config is a valid field name for every map layer (with
    special exceptions for the keyword 'any' or the 'team' filter key. Raises InvalidExceptionConfig if config invalid.
    """

    # A helper conditional that returns whether a given key is 'team' and the layers have this key.
    def key_is_team(key):
        return (key == 'team' and
                all(layer.get('team1') is not None for layer in layers) and
                all(layer.get('team2') is not None for layer in layers))

    for filter_config in config:
        # In the special case of strings, only the keyword 'any' is valid.
        if isinstance(filter_config, str):
            if filter_config.casefold() == 'any':
                continue
            else:
                raise InvalidConfigException(f'Invalid values for config section: {filter_config}!')
        # Otherwise, only dict types are valid configs.
        if not isinstance(filter_config, collections.Mapping):
            raise InvalidConfigException(f'Given config {filter_config} has invalid type/structure!')

        # Make sure every key in the config exists in **all** the layers. Otherwise, the config is invalid.
        # NOTE(bsubei): this is validating the layers as much as the config (both must be fully compatible).
        # NOTE(bsubei): 'team' is a special key that we allow as long as 'team1' and 'team2' keys exist in layers.
        for key in filter_config.keys():
            if not key_is_team(key) and not all(layer.get(key) is not None for layer in layers):
                raise InvalidConfigException(f'Key {key} is not a valid key to filter by in {filter_config}!')
    # Only after checking that every filter config is not invalid can we be sure that it is valid (and we do nothing).


def validate_config(config, layers):
    """
    Raises InvalidConfigException if the given config is invalid. Uses the given layers to make sure the config is
    compatible.

    :param config: dict The config that describes how to choose the rotation. See README.md for expected format.
    :param layers: list(dict) The list of layers to check the config against.
    :raises InvalidConfigException: The exception raised if the config is invalid.
    """
    # Validate that the given layers is valid (we need to use its fields to ensure the config is valid).
    if (not isinstance(layers, list) or
            len(layers) < 1 or
            not all(isinstance(layer, collections.Mapping) for layer in layers)):
        raise InvalidConfigException(
            'The given layers to check the config against is invalid!')

    # NOTE(bsubei): the only field in the config that is necessary is 'regular_maps', and it must be a list with at
    # least one element.
    regular_maps_config = config.get('regular_maps')
    if regular_maps_config is None or not isinstance(regular_maps_config, list) or len(regular_maps_config) < 1:
        raise InvalidConfigException(
            'Missing or invalid "regular_maps" key in config!')

    # Unlike the regular_maps config, the starting_maps config is optional but if it exists, it must be valid.
    starting_maps_config = config.get('starting_maps', ['any'])
    if (starting_maps_config is not None and
            (not isinstance(starting_maps_config, list) or len(starting_maps_config) < 1)):
        raise InvalidConfigException(
            'Given "starting_maps" key is invalid! Should be a list!')

    # Check that 'number_of_repeats' is a valid number if it exists (and if it doesn't, a default of 1 should be valid).
    number_of_repeats = config.get('number_of_repeats', 1)
    if not isinstance(number_of_repeats, int) or number_of_repeats < 1:
        raise InvalidConfigException(
            'Invalid "number_of_repeats" value in config! Please use a positive integer.')

    # Validate the starting_maps section of the config.
    validate_helper(starting_maps_config, layers)
    # Validate the regular_maps section of the config.
    validate_helper(regular_maps_config, layers)


def parse_config(config_path, layers):
    """
    Returns a rotation config from the given config_path after validating against the given layers. Raises
    InvalidConfigException if config is invalid.

    :param config_path: str The path to the config file.
    :param layers: list(dict) The list of layers to check against.
    :raises InvalidConfigException: The exception raised if the config is invalid.
    """
    with open(config_path, 'r') as f:
        config = yaml.load(f)
    validate_config(config, layers)
    return config


def main():
    """ Run the script and write out a map rotation. """
    args = parse_cli()
    layers = get_json_layers(args.input_filepath, args.input_url)
    config = parse_config(args.config_filepath, layers)
    chosen_map_rotation = get_map_rotation(config, layers)
    write_rotation(chosen_map_rotation, args.output_filepath)
    send_rotation_to_discord(chosen_map_rotation, args.discord_webhook_url)


if __name__ == '__main__':
    main()
