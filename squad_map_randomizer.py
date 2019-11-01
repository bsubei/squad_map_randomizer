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
from discord_webhook import DiscordWebhook
import json
import random

# Use the current working directory for MapRotation file and the default name.
DEFAULT_MAP_ROTATION_FILEPATH = 'MapRotation.cfg'
# Use the cwd for the input JSON file containing all the map/layer data.
DEFAULT_JSON_INPUT_FILEPATH = 'layers.json'
# The number of skirmish maps to add to beginning of map rotation.
NUM_STARTING_SKIRMISH_MAPS = 2
# The number of times to repeat the AAS/RAAS/Invasion pattern.
NUM_REPEATING_PATTERN = 5


def parse_cli():
    """ Parses sys.argv (commandline args) and returns a parser with the arguments. """
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output-filepath', default=DEFAULT_MAP_ROTATION_FILEPATH,
                        help='Filepath to write out map rotation to.')
    parser.add_argument('-i', '--input-filepath', default=DEFAULT_JSON_INPUT_FILEPATH,
                        help='Filepath of JSON file to use for map layers.')
    parser.add_argument('--discord-webhook-url', required=False,
                        help=('The URL to the Discord webhook if you want to post the latest rotation to a Discord'
                              ' channel.'))
    return parser.parse_args()


def parse_json_layers(input_filepath):
    """ Return the JSON object represented by the given input_filepath as a list of dicts."""
    with open(input_filepath, 'rb') as f:
        return json.load(f)


def get_valid_layer(available_layers, chosen_rotation, valid_condition):
    """
    Given the available layers to choose from, the current chosen_rotation, and a valid condition lambda, randomly
    chooses and returns a layer if it satisfies the valid condition.

    :param available_layers:  A list of available layers to choose from (as JSON objects).
    :param chosen_rotation:  The list of currently chosen layers (only used to print debug messages).
    :param valid_condition:  A lambda that takes in the candidate layer and returns whether it is valid or not.
    :return: A randomly chosen layer that satisfies the condition.
    """
    # Attempt to get a valid layer that doesn't break the rules. Throw an exception if you can't.
    for _ in range(100):
        candidate_layer = random.choice(available_layers)
        # If the layers follows the rules, add it to the chosen rotation.
        if valid_condition(candidate_layer):
            return candidate_layer
        else:
            print('Discarding chosen layer {} because it has the same map as the previous layers {} and {}.'.format(
                    candidate_layer['layer'], chosen_rotation[-1]['layer'], chosen_rotation[-2]['layer']))
    raise ValueError('Could not get a valid layer! Aborting!')


def get_map_rotation(all_layers):
    """
    Given all the map layers as a list of dicts, return the chosen map rotation based on the following rules:

    General pattern:
    2x Random Skirmish Layers
    Repeat the pattern 5x {
        1x AAS or RAAS layer
        1x AAS or RAAS layer that must have Helicopters
        1x Invasion layer
    }

    Other rules:

    - Remove bugged layers.
    - Layers cannot be repeated in the entire rotation (without replacement policy when sampling).
    - A map cannot be repeated in the above pattern (even if a different layer).
    - A map cannot be played consecutively at the edge of the pattern (e.g. Basrah Invasion then Basrah AAS).

    Notes:
     - There are 23 AAS layers.
     - There are 50 RAAS layers.
     - There are 34 Invasion layers.
     - There are 30 TC layers.
     - Had to correct "Kamdesh TC v1" to "Kamdesh TC v2".
    """
    # First, filter out all the bugged layers.
    nonbugged_layers = list(filter(lambda m: not m['bugged'], all_layers))

    # Now, organize all the layers by their gamemode and whether they have helicopters.
    # NOTE: since we use a "without replacement" policy when randomly sampling, these remaining_*_layers lists will have
    # elements removed as the rotation is built out.
    remaining_skirmish_layers = list(filter(lambda m: m['gamemode'] == 'Skirmish', nonbugged_layers))
    remaining_aas_raas_layers = list(filter(lambda m: m['gamemode'] in ('AAS', 'RAAS'), nonbugged_layers))
    remaining_aas_raas_heli_layers = list(filter(lambda m: m['helicopters'], remaining_aas_raas_layers))
    remaining_invasion_layers = list(filter(lambda m: m['gamemode'] == 'Invasion', nonbugged_layers))

    # The chosen rotation will be stored here (as a list of these dicts).
    chosen_rotation = []

    # First map (Skirmish) gets chosen no matter what. Remove it from the pool of remaining layers (using without
    # replacement policy).
    chosen_layer = random.choice(remaining_skirmish_layers)
    chosen_rotation.append(chosen_layer)
    remaining_skirmish_layers.remove(chosen_layer)

    # The remaining skirmish maps have to be validated.
    for _ in range(1, NUM_STARTING_SKIRMISH_MAPS):
        chosen_layer = get_valid_layer(
                            remaining_skirmish_layers,
                            chosen_rotation,
                            lambda candidate: candidate['map'] != chosen_rotation[-1]['map'])
        chosen_rotation.append(chosen_layer)
        # Remove it from the pool since we used it (using without replacement policy).
        remaining_skirmish_layers.remove(chosen_layer)

    # Repeat the pattern five times.
    for _ in range(NUM_REPEATING_PATTERN):
        # 1x AAS or RAAS layer
        # NOTE: Chosen layer is valid only if these two conditions are true:
        # 1- Adding this layer does not cause two consecutive layers to have the same map.
        # 2- This layer's map is not in the current pattern (automatically guaranteed).
        chosen_layer = get_valid_layer(
                            remaining_aas_raas_layers,
                            chosen_rotation,
                            lambda candidate: candidate['map'] != chosen_rotation[-1]['map'])
        chosen_rotation.append(chosen_layer)
        # Remove it from the pool since we used it (using without replacement policy).
        remaining_aas_raas_layers.remove(chosen_rotation[-1])
        # Don't forget to remove this from the heli subset if needed.
        if chosen_rotation[-1] in remaining_aas_raas_heli_layers:
            remaining_aas_raas_heli_layers.remove(chosen_rotation[-1])

        # 1x AAS or RAAS layer that must have Helicopters
        # NOTE: Chosen layer is valid only if these two conditions are true:
        # 1- Adding this layer does not cause two consecutive layers to have the same map.
        # 2- This layer's map is not in the current pattern (guaranteed by above condition).
        chosen_layer = get_valid_layer(
                            remaining_aas_raas_heli_layers,
                            chosen_rotation,
                            lambda candidate: candidate['map'] != chosen_rotation[-1]['map'])
        chosen_rotation.append(chosen_layer)
        # Remove it from the pool since we used it (using without replacement policy).
        remaining_aas_raas_heli_layers.remove(chosen_layer)
        # Don't forget to remove this from the superset if needed.
        if chosen_layer in remaining_aas_raas_heli_layers:
            remaining_aas_raas_layers.remove(chosen_layer)

        # 1x Invasion layer
        # NOTE: Chosen layer is valid only if these two conditions are true:
        # 1- Adding this layer does not cause two consecutive layers to have the same map.
        # 2- This layer's map is not in the current pattern (must be checked explicitly).
        chosen_layer = get_valid_layer(
                remaining_invasion_layers,
                chosen_rotation,
                lambda candidate: candidate['map'] not in (chosen_rotation[-1]['map'], chosen_rotation[-2]['map']))
        chosen_rotation.append(chosen_layer)
        # Remove it from the pool since we used it (using without replacement policy).
        remaining_invasion_layers.remove(chosen_layer)

    # TODO also check that the last layer does not have the same map as the first Skirmish layer.

    return chosen_rotation


def get_layers_string(map_rotation):
    """ Returns all the layers from the given map rotation as a string with newlines. """
    return '\n'.join([layer['layer'] for layer in map_rotation])


def write_rotation(map_rotation, output_filepath):
    """ Writes out given map rotation (list of dicts) to the given output filepath as a map rotation. """
    with open(output_filepath, 'w') as f:
        f.write(get_layers_string(map_rotation))


def send_rotation_to_discord(map_rotation, discord_webhook_url):
    """ Sends the map rotation as a message to the discord channel for the given webhook URL. """
    if discord_webhook_url:
        webhook = DiscordWebhook(url=discord_webhook_url, content=get_layers_string(map_rotation))
        webhook.execute()


def main():
    """ Run the script and write out a map rotation. """
    args = parse_cli()
    layers = parse_json_layers(args.input_filepath)
    chosen_map_rotation = get_map_rotation(layers)
    write_rotation(chosen_map_rotation, args.output_filepath)
    send_rotation_to_discord(chosen_map_rotation, args.discord_webhook_url)


if __name__ == '__main__':
    main()
