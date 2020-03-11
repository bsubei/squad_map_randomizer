#! /usr/bin/env python3

# Copyright (C) 2020 Basheer Subei
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
# A testing class to test the squad_map_randomizer script.
#

import os
import pytest
import random
from unittest import mock
import yaml

import squad_map_randomizer


# Below are helper predicates used in the filters.
def is_skirmish(layer):
    return layer['gamemode'] == 'Skirmish'


def is_aas(layer):
    return layer['gamemode'] == 'AAS'


def is_raas(layer):
    return layer['gamemode'] == 'RAAS'


def is_small_map(layer):
    return layer['map_size'] == 'small'


def is_medium_map(layer):
    return layer['map_size'] == 'medium'


def is_large_map(layer):
    return layer['map_size'] == 'large'


def is_helicopters(layer):
    return layer['helicopters']


# Below are helpers used in tests for valid map rotations (checking for duplicates).
def has_duplicate_layers(rotation):
    """ Given a map rotation (list of layers), return True if any of the layers are duplicates and False otherwise. """
    return len(set([layer['layer'] for layer in rotation])) < len(rotation)


def has_close_duplicate_maps(rotation, min_distance_duplicate):
    """
    Given a map rotation (list of layers), return True if any layers with the same map name are min_distance_duplicate
    close to each other. Return False otherwise.
    """
    # Check for duplicate map names that are too close together.
    for current_idx, current_layer in enumerate(rotation):
        # Get the distances from the current layer to the other layers with the same map name (only checking layers
        # after the current layer).
        distances = [i + 1 for i, other in enumerate(rotation[current_idx + 1:])
                     if current_layer['map'] == other['map']]
        # Make sure no duplicates are too close. If any are too close, return True.
        if any(distance <= min_distance_duplicate for distance in distances):
            return True
    # Return False since we did not find any duplicates that were too close.
    return False


class TestSquadMapRandomizer:
    """ Test class (uses pytest) for the SquadMapRandomizer script. """

    MOCK_RCON_CLIENT = mock.MagicMock()

    @pytest.fixture(scope='module')
    def default_layers(self):
        """
        The fixture function to return a list of layers containing all valid fields (uses the real layers stored in the
        bsubei/squad_map_layers GitHub repository.
        Below is an example of a single layer (so we get a list of these):
        {
            "map": "Al Basrah",
            "layer": "Al Basrah AAS v1",
            "gamemode": "AAS",
            "version": "v1",
            "team1": "US",
            "team2": "INS",
            "helicopters": False,
            "night": False,
            "RAA_Lanes": False,
            "Invasion_Random": False,
            "bugged": False,
            "map_size": "medium",
        }
        """
        return squad_map_randomizer.get_json_layers(None, squad_map_randomizer.DEFAULT_LAYERS_URL)

    @pytest.fixture
    def default_config(self):
        """ The fixture function to return the default config. """
        return {
            'starting_maps': [
                {'gamemode': 'Skirmish'},
                {'gamemode': 'Skirmish'}],
            'number_of_repeats': 5,
            'regular_maps': [
                {'gamemode': ['AAS', 'RAAS'], 'map_size': 'small'},
                {'gamemode': ['AAS', 'RAAS'], 'map_size': 'medium'},
                {'gamemode': ['AAS', 'RAAS'], 'map_size': 'medium'},
                {'gamemode': ['AAS', 'RAAS'],
                 'map_size': 'large', 'helicopters': True}
            ]
        }

    # Run this test 100 times with a different random seed each time.
    @pytest.mark.parametrize('execution_number', range(100))
    def test_get_map_rotation_and_descriptions_default(self, default_config, default_layers, execution_number):
        """ Tests that we can call get_map_rotation_and_descriptions correctly on the default layers and config. """
        # Set the random seed so the results are deterministic across different pytest invocations so we can reproduce
        # test failures.
        random.seed(execution_number)

        # The default config will return 2 skirmish maps and 20 (R)AAS maps.
        rotation, descriptions = squad_map_randomizer.get_map_rotation_and_descriptions(
            default_config, default_layers)

        # Expect the correct number of maps (for each type as well).
        assert len(rotation) == 22
        num_skirmish_layers = sum([is_skirmish(layer) for layer in rotation])
        num_AAS_layers = sum([is_aas(layer) for layer in rotation])
        num_RAAS_layers = sum([is_raas(layer) for layer in rotation])
        num_AAS_or_RAAS_layers = sum(
            [is_aas(layer) or is_raas(layer) for layer in rotation])
        assert num_skirmish_layers == 2
        assert num_AAS_or_RAAS_layers == 20
        assert num_AAS_layers + num_RAAS_layers == num_AAS_or_RAAS_layers

        # Expect the correct number of repeated maps: 5 small AAS or RAAS maps, 10 medium AAS or RAAS maps, and 5 large
        # AAS or RAAS maps with helicopters.
        # NOTE(bsubei): you can see the "OR" relationship within a field ('gamemode') and the "AND" relationship across
        # different fields ('gamemode', 'map_size', and 'helicopters').
        assert sum([(is_aas(layer) or is_raas(layer))
                    and is_small_map(layer) for layer in rotation]) == 5
        assert sum([(is_aas(layer) or is_raas(layer))
                    and is_medium_map(layer) for layer in rotation]) == 10
        assert sum([
            (is_aas(layer) or is_raas(layer)) and
            is_large_map(layer) and
            is_helicopters(layer) for layer in rotation]) == 5

        # Expect all the descriptions to match the filter keys/values they used.
        EXPECTED_STARTING_MAP_DESCRIPTIONS = [['Skirmish'], ['Skirmish']]
        EXPECTED_REGULAR_MAP_DESCRIPTIONS = [
                        ['AAS', 'RAAS', 'small'],
                        ['AAS', 'RAAS', 'medium'],
                        ['AAS', 'RAAS', 'medium'],
                        ['AAS', 'RAAS', 'large', 'helicopters']] * 5
        assert descriptions[:2] == EXPECTED_STARTING_MAP_DESCRIPTIONS
        assert descriptions[2:] == EXPECTED_REGULAR_MAP_DESCRIPTIONS

    # Run this test 100 times with a different random seed each time.
    @pytest.mark.parametrize('execution_number', range(100))
    def test_get_map_rotation_and_descriptions_duplicates(self, default_layers, execution_number):
        """
        Tests that we can call get_map_rotation_and_descriptions correctly and not get duplicate maps too close to each
        other or duplicate layers at all.
        """
        # Set the random seed so the results are deterministic across different pytest invocations so we can reproduce
        # test failures.
        random.seed(execution_number)

        # Use a config where the rotation could have a lot of duplicate maps.
        config_with_potential_duplicates = {
            'number_of_repeats': 5,
            'regular_maps': [
                {'map': 'Al Basrah'},
                {'map': 'Belaya'},
                {'map': 'Chora'},
                {'map': 'Fool\'s Road'}]}

        rotation, descriptions = squad_map_randomizer.get_map_rotation_and_descriptions(
            config_with_potential_duplicates, default_layers)

        # Check that no two layers with the same map name are too close.
        assert not has_close_duplicate_maps(
            rotation, squad_map_randomizer.NUM_MIN_LAYERS_BEFORE_DUPLICATE_MAP)
        # Check that no two layers are duplicates.
        assert not has_duplicate_layers(rotation)
        # Expect all the descriptions to match the filter keys/values they used.
        EXPECTED_REGULAR_MAP_DESCRIPTIONS = [
                        ['Al Basrah'],
                        ['Belaya'],
                        ['Chora'],
                        ['Fool\'s Road']] * 5
        assert descriptions == EXPECTED_REGULAR_MAP_DESCRIPTIONS

        # Test that if we intentionally make it impossible to avoid duplicates, it prints an error but continues.
        impossible_config = {'number_of_repeats': 10,
                             'regular_maps': [{'map': 'Chora'}]}
        with mock.patch('squad_map_randomizer.logging.error') as mock_error:
            rotation, descriptions = squad_map_randomizer.get_map_rotation_and_descriptions(
                impossible_config, default_layers)
            assert mock_error.call_count == 9
            assert all('Could not get a valid map without duplicates!' in args[0][0]
                       for args in mock_error.call_args_list)
            assert descriptions == [['Chora']] * 10

        # It will have some duplicate map names that are too close, but never duplicate layers (sampling without
        # replacement).
        assert has_close_duplicate_maps(
            rotation, squad_map_randomizer.NUM_MIN_LAYERS_BEFORE_DUPLICATE_MAP)
        assert not has_duplicate_layers(rotation)

    def test_get_map_rotation_and_descriptions_any(self, default_layers):
        """ Tests that we can call get_map_rotation_and_descriptions correctly with a config with the 'any' keyword. """
        # Test case with a config containing the special 'any' keyword (signifying no filters for this layer).
        config_with_any = {'regular_maps':
                           ['any', {'gamemode': ['AAS', 'RAAS'], 'map_size': 'large', 'helicopters': True}, 'any']}
        rotation, descriptions = squad_map_randomizer.get_map_rotation_and_descriptions(
            config_with_any, default_layers)
        # Check that the rotation has three layers, the second of which has filters while the rest have no filters.
        assert len(rotation) == 3
        assert ((is_aas(rotation[1]) or is_raas(rotation[1])) and
                is_large_map(rotation[1]) and
                is_helicopters(rotation[1]))
        # Expect all the descriptions to match the filter keys/values they used.
        EXPECTED_REGULAR_MAP_DESCRIPTIONS = [
                        ['any'],
                        ['AAS', 'RAAS', 'large', 'helicopters'],
                        ['any']]
        assert descriptions == EXPECTED_REGULAR_MAP_DESCRIPTIONS

    def test_get_map_rotation_and_descriptions_team(self, default_layers):
        """ Tests that we can call get_map_rotation_and_descriptions correctly with a config with the 'team' filter. """
        # Test that the 'team' filter is special and is accepted as a filter.
        config_with_team = {'number_of_repeats': 5, 'regular_maps': [
            {'team': ['INS', 'RU']},
            {'team': ['US']}]}
        rotation, descriptions = squad_map_randomizer.get_map_rotation_and_descriptions(
            config_with_team, default_layers)

        # Check that every other map starting from the first has either INS or RU in either team.
        for layer in rotation[::2]:
            assert 'INS' in [layer['team1'], layer['team2']
                             ] or 'RU' in [layer['team1'], layer['team2']]
        # Check that every other map starting from the second has US in either team.
        for layer in rotation[1::2]:
            assert 'US' in [layer['team1'], layer['team2']]

        # Expect all the descriptions to match the filter keys/values they used.
        EXPECTED_REGULAR_MAP_DESCRIPTIONS = [['INS', 'RU'], ['US']] * 5
        assert descriptions == EXPECTED_REGULAR_MAP_DESCRIPTIONS

    def test_get_map_rotation_and_descriptions_examples(self, default_layers):
        """ Tests that we can call get_map_rotation_and_descriptions correctly on all the example configs. """
        # Test that all example configs can be parsed without problems, and result in non-empty rotations.
        for path in os.scandir(squad_map_randomizer.EXAMPLES_CONFIG_DIR):
            config = squad_map_randomizer.parse_config(path, default_layers)
            rotation, descriptions = squad_map_randomizer.get_map_rotation_and_descriptions(
                config, default_layers)
            assert len(rotation) > 0

    def test_get_map_rotation_and_descriptions_invalid_filter(self, default_layers):
        """ Tests that we expect errors when get_map_rotation_and_descriptions is called on config filters. """
        # Test that incorrect filters (no layers meet the conditions) prints an error but continues.
        config_with_team = {'number_of_repeats': 5, 'regular_maps': [
            {'team': ['misspelled_name']},
            {'team': ['US']}]}
        with mock.patch('squad_map_randomizer.logging.error') as mock_error:
            rotation, descriptions = squad_map_randomizer.get_map_rotation_and_descriptions(
                config_with_team, default_layers)
            # Check that only 5 errors are printed.
            assert mock_error.call_count == 5
            assert all('No maps to choose from after applying filter' in args[0][0]
                       for args in mock_error.call_args_list)
            # The other filter works correctly so we end up with 5 maps in the rotation.
            assert len(rotation) == 5
            assert all(layer['team1'] == 'US' or layer['team2']
                       == 'US' for layer in rotation)
            # Expect all the descriptions to match the filter keys/values they used.
            EXPECTED_REGULAR_MAP_DESCRIPTIONS = [['US']] * 5
            assert descriptions == EXPECTED_REGULAR_MAP_DESCRIPTIONS

    def test_is_config_valid_examples(self, default_layers):
        """ Tests that all the example configs successfully validate. """
        # Test that all example configs validate successfully.
        for path in os.scandir(squad_map_randomizer.EXAMPLES_CONFIG_DIR):
            with open(path, 'r') as f:
                squad_map_randomizer.validate_config(
                    yaml.load(f), default_layers)

    def test_is_config_valid(self, default_config, default_layers):
        """ Tests that all sorts of configs successfully validate. """

        # Valid config test cases:

        # Test that a valid default config (which is also the default config) does not raise.
        squad_map_randomizer.validate_config(default_config, default_layers)

        # Test a valid config with the bare minimum information (just one map with no filters applied).
        # NOTE(bsubei): a config without 'starting_maps' and 'number_of_repeats' is still valid (they have defaults).
        squad_map_randomizer.validate_config(
            {'regular_maps': ['any']}, default_layers)

        # Test a valid config with the a starting_maps config.
        squad_map_randomizer.validate_config(
            {'regular_maps': ['any'], 'starting_maps': ['any']}, default_layers)

        # Test a valid config with number_of_repeats as a large integer.
        squad_map_randomizer.validate_config(
            {'regular_maps': ['any'], 'number_of_repeats': 10000}, default_layers)

        # Test that a config with map name is valid.
        squad_map_randomizer.validate_config(
            {'regular_maps': [
                {'map': 'unimportant'},
                {'map': ['multiple', 'possible', 'map names']},
                {'map': 'not used really'},
            ]}, default_layers)

        # Test that the 'team' filter field is special and maps to either 'team1' or 'team2' names and is valid.
        squad_map_randomizer.validate_config(
            {'regular_maps': [
                {'team': ['US', 'GB']},
                {'map': 'unimportant'},
                {'map': 'not used really'},
            ]}, default_layers)

        # Invalid config test cases:

        # Test that an invalid layers also makes the config "invalid".
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'regular_maps': ['any']}, 'not a list')
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config({'regular_maps': ['any']}, [])
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config({'regular_maps': ['any']}, [
                                                 'not all elements are dict', {'a': 1}])

        # Test that a missing or incorrect 'regular_maps' field makes it invalid.
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {
                    'intentionally_wrong_field_name': [
                        {'gamemode': ['AAS', 'RAAS'], 'map_size': 'small'}, ],
                    'starting_maps': [
                        {'gamemode': ['AAS', 'RAAS'], 'map_size': 'small'}, ],
                }, default_layers)
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'regular_maps': 'supposed to be a list here'}, default_layers)
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'regular_maps': []}, default_layers)
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'regular_maps': ['blargh', 'random', 'stuff']}, default_layers)
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'regular_maps': [123, 456]}, default_layers)

        # Test that an incorrect 'starting_maps' field makes it invalid.
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'starting_maps': 'blargh',
                    'regular_maps': ['any']}, default_layers)
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'starting_maps': [],
                    'regular_maps': ['any']}, default_layers)
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'starting_maps': ['blargh', 'does not exist'],
                    'regular_maps': ['any']}, default_layers)
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'starting_maps': [42, 77, 0],
                    'regular_maps': ['any']}, default_layers)

        # Test that an incorrect 'number_of_repeats' field makes it invalid.
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'regular_maps': ['any'], 'number_of_repeats': 'supposed to be a number'}, default_layers)
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'regular_maps': ['any'], 'number_of_repeats': 0}, default_layers)
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'regular_maps': ['any'], 'number_of_repeats': -100}, default_layers)

        # Test that a non-existing filter field name in 'starting_maps' is invalid.
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'starting_maps': [{'gamemode': 'blabla', 'THIS_DOES_NOT_EXIST': 'INVALID CONFIG HALP'}],
                    'regular_maps': ['any']}, default_layers)

        # Test that a config with a non-existing filter field name in 'regular_maps' is invalid.
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'regular_maps': [
                    {'map': 'unimportant', 'THIS_DOES_NOT_EXIST': 'INVALID CONFIG'},
                    {'map': ['multiple', 'possible', 'map names']},
                    {'map': 'not used really'},
                ]}, default_layers)

    def test_parse_config(self, default_config, default_layers):
        """ Tests that we can call parse_config correctly. """
        # We expect the default config above to exactly match the one parsed from configs/default_config.yml.
        with mock.patch('squad_map_randomizer.validate_config'):
            assert squad_map_randomizer.parse_config(
                squad_map_randomizer.DEFAULT_CONFIG_FILEPATH, default_layers) == default_config
