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
import asyncio
import datetime
import discord
import json
import logging
import random
from urllib import request

logging.basicConfig(
    filename='squad_map_randomizer.log', level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Use the current working directory for MapRotation file and the default name.
DEFAULT_MAP_ROTATION_FILEPATH = 'MapRotation.cfg'
# The number of skirmish maps to add to beginning of map rotation.
NUM_STARTING_SKIRMISH_MAPS = 2
# The number of times to repeat the AAS/RAAS/Invasion pattern.
NUM_REPEATING_PATTERN = 5
# A layer will be discarded if a layer with the same map was last played this many layers ago.
NUM_MIN_LAYERS_BEFORE_DUPLICATE_MAP = 3
# The description text to post in the Discord channel for map rotations.
CHANNEL_DESCRIPTION_TEXT = (
                    'The daily map rotation will be posted here. The rotation is always randomized and follows'
                    ' the following pattern:\n'
                    '```\n'
                    '2x Random Skirmish Layers\n'
                    'Repeat the pattern 5x {\n'
                    '    1x AAS or RAAS layer\n'
                    '    1x AAS or RAAS layer that must have Helicopters\n'
                    '    1x Invasion layer\n'
                    '}\n'
                    '```\n'
                    'Other rules:\n'
                    '- Layers cannot be repeated in the entire rotation (without replacement policy when sampling).\n'
                    '- A layer cannot be repeated if another layer of the same map was last played 3 maps ago.\n'
                    )


def parse_cli():
    """ Parses sys.argv (commandline args) and returns a parser with the arguments. """
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output-filepath', default=DEFAULT_MAP_ROTATION_FILEPATH,
                        help='Filepath to write out map rotation to.')
    parser.add_argument('--discord-channel-id', required=False,
                        help=('The ID of the Discord channel to post the rotation messages to.'))
    parser.add_argument('--discord-token', required=False,
                        help=('The token for the Discord bot authorized to post to your Discord guild/server.'))
    # Expect either an input filepath or URL, but not both.
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--input-filepath', help='Filepath of JSON file to use for map layers.')
    input_group.add_argument('--input-url', help='URL to JSON file to use for map layers.')
    return parser.parse_args()


def get_json_layers(input_filepath, input_url):
    """
    Return the JSON object represented by the given filepath or URL (in the args) as a list of dicts. See
    https://github.com/bsubei/squad_map_layers for an example layers JSON file.
    """
    # If the URL is defined, fetch the JSON file from there and parse it into a list of dicts.
    if input_url:
        text = request.urlopen(input_url).read().decode('utf-8')
        return json.loads(text)
    elif input_filepath:
        # Just read the JSON file from a filepath and
        with open(input_filepath, 'rb') as f:
            return json.load(f)
    else:
        raise ValueError('Sanity check failed! No input args provided!')


def get_valid_layer(available_layers, chosen_rotation, min_layers_before_duplicate_map):
    """
    Given the available layers to choose from, the current chosen_rotation, and the number of layers to check behind
    for a duplicate map, randomly chooses and returns a layer.

    :param available_layers:  A list of available layers to choose from (as dicts derived from the JSON object).
    :param chosen_rotation:  The list of currently chosen layers.
    :param min_layers_before_duplicate_map:  The number of maps before a duplicate map is allowed.
    :return: A randomly chosen layer that did not have the same map played recently.
    """
    # Throw warnings if given an incorrect index to check for duplicate maps and use a default of 1.
    if 1 > min_layers_before_duplicate_map < len(chosen_rotation):
        logging.error('min_layers_before_duplicate_map was invalid {} in get_valid_layer()!'.format(
                        min_layers_before_duplicate_map))
        min_layers_before_duplicate_map = 1

    # Attempt to get a valid layer that doesn't break the rules. Throw an exception if you can't.
    layers_to_avoid_duplicating = chosen_rotation[-min_layers_before_duplicate_map:]
    for _ in range(100):
        candidate_layer = random.choice(available_layers)
        if candidate_layer['map'] not in [layer['map'] for layer in layers_to_avoid_duplicating]:
            # If the layers follows the rules, add it to the chosen rotation.
            return candidate_layer
        else:
            # Otherwise, give a warning and continue attempting to get a valid layer.
            previous_layers_string = ', '.join(
                            [layer['layer'] for layer in layers_to_avoid_duplicating])
            logging.warning('Discarding chosen layer {} because it has the same map as the previous layers {}.'.format(
                            candidate_layer['layer'], previous_layers_string))
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
    - A layer cannot be repeated if another layer of the same map was last played NUM_MIN_LAYERS_BEFORE_DUPLICATE_MAP
      maps ago.
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
    for idx in range(1, NUM_STARTING_SKIRMISH_MAPS):
        chosen_layer = get_valid_layer(remaining_skirmish_layers, chosen_rotation, idx)
        chosen_rotation.append(chosen_layer)
        # Remove it from the pool since we used it (using without replacement policy).
        remaining_skirmish_layers.remove(chosen_layer)

    # Repeat the pattern five times.
    for _ in range(NUM_REPEATING_PATTERN):
        # 1x AAS or RAAS layer
        # NOTE: Chosen layer is valid only if these two conditions are true:
        # 1- Adding this layer does not cause two consecutive layers to have the same map.
        # 2- This layer's map is not in the current pattern (automatically guaranteed).
        chosen_layer = get_valid_layer(remaining_aas_raas_layers, chosen_rotation, NUM_MIN_LAYERS_BEFORE_DUPLICATE_MAP)
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
                            remaining_aas_raas_heli_layers, chosen_rotation, NUM_MIN_LAYERS_BEFORE_DUPLICATE_MAP)
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
        chosen_layer = get_valid_layer(remaining_invasion_layers, chosen_rotation, NUM_MIN_LAYERS_BEFORE_DUPLICATE_MAP)
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


def post_to_discord(discord_token, discord_channel_id, map_rotation):
    """ Makes the only message in a Discord channel contain the map rotation. """
    # Only post to Discord if both the token and channel id are given.
    if discord_token and discord_channel_id:
        # Assemble the new message to post.
        discord_message = '{}\nThe map rotation for {} is:\n```{}```'.format(
                                CHANNEL_DESCRIPTION_TEXT, datetime.date.today(), get_layers_string(map_rotation))
        # Set up the event loop (since the discord client must run asynchronously)
        loop = asyncio.get_event_loop()
        # Create a Discord client.
        client = discord.Client(loop=loop)

        @client.event
        async def on_ready():
            """
            Once the bot connects, removes all messages in Discord channel and posts the most recent map rotation as
            one message.
            """
            # Get handle to Discord channel with given ID.
            await asyncio.sleep(10)
            channel = client.get_channel(int(discord_channel_id))
            # Delete all old messages in channel.
            await channel.purge()
            # Post the new message.
            await channel.send(discord_message)
            # Finally, log out the client so this script doesn't sit here forever waiting for events.
            await client.logout()

        try:
            # Actually start up the client.
            loop.run_until_complete(client.start(discord_token))
        except Exception as e:
            # If you catch any exceptions (not including KeyboardInterrupt), just log them and move on.
            logging.error('Skipping posting to Discord due to failure: {}'.format(str(e)))


def main():
    """ Run the script and write out a map rotation. """
    args = parse_cli()
    layers = get_json_layers(args.input_filepath, args.input_url)
    chosen_map_rotation = get_map_rotation(layers)
    write_rotation(chosen_map_rotation, args.output_filepath)
    post_to_discord(args.discord_token, args.discord_channel_id, chosen_map_rotation)


if __name__ == '__main__':
    main()
