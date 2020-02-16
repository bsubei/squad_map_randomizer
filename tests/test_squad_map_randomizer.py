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

import pytest
from unittest import mock

import squad_map_randomizer


class TestSquadMapRandomizer:
    """ Test class (uses pytest) for the SquadMapRandomizer script. """

    MOCK_RCON_CLIENT = mock.MagicMock()

    @pytest.fixture
    def example_layers(self):
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
        # TODO pull this layers from the GitHub repo
        return [{
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
        }]

    @pytest.fixture
    def example_config(self):
        """ The fixture function to return an example config. """
        return {
                'seeding': [
                        {'gamemode': 'Skirmish'},
                        {'gamemode': 'Skirmish'}],
                'pattern_repeats': 5,
                'pattern': [
                        {'gamemode': ['AAS', 'RAAS'], 'map_size': 'small'},
                        {'gamemode': ['AAS', 'RAAS'], 'map_size': 'medium'},
                        {'gamemode': ['AAS', 'RAAS'], 'map_size': 'medium'},
                        {'gamemode': ['AAS', 'RAAS'], 'map_size': 'large', 'helicopters': True}
                    ]
                }

    def test_is_config_valid(self, example_config, example_layers):
        """ Tests that the example config successfully validates. """

        # Valid config test cases:

        # Test that a valid example config (which is also the default config) does not raise.
        squad_map_randomizer.validate_config(example_config, example_layers)

        # Test a valid config with the bare minimum information (just one map with no filters applied).
        # NOTE(bsubei): a config without 'seeding' and 'pattern_repeats' is still valid (they have defaults).
        squad_map_randomizer.validate_config({'pattern': ['any']}, example_layers)

        # Test a valid config with the a seeding config.
        squad_map_randomizer.validate_config({'pattern': ['any'], 'seeding': ['any']}, example_layers)

        # Test a valid config with pattern_repeats as a large integer.
        squad_map_randomizer.validate_config({'pattern': ['any'], 'pattern_repeats': 10000}, example_layers)

        # Test that a config with map name is valid.
        squad_map_randomizer.validate_config(
            {'pattern': [
                {'map': 'unimportant'},
                {'map': ['multiple', 'possible', 'map names']},
                {'map': 'not used really'},
            ]}, example_layers)

        # Test that the 'team' filter field is special and maps to either 'team1' or 'team2' names and is valid.
        squad_map_randomizer.validate_config(
            {'pattern': [
                {'team': ['US', 'GB']},
                {'map': 'unimportant'},
                {'map': 'not used really'},
            ]}, example_layers)

        # Invalid config test cases:

        # Test that an invalid layers also makes the config "invalid".
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config({'pattern': ['any']}, 'not a list')
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config({'pattern': ['any']}, [])
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config({'pattern': ['any']}, ['not all elements are dict', {'a': 1}])

        # Test that a missing or incorrect 'pattern' field makes it invalid.
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {
                    'intentionally_wrong_field_name': [
                        {'gamemode': ['AAS', 'RAAS'], 'map_size': 'small'}, ],
                    'seeding': [
                        {'gamemode': ['AAS', 'RAAS'], 'map_size': 'small'}, ],
                }, example_layers)
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'pattern': 'supposed to be a list here'}, example_layers)
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'pattern': []}, example_layers)
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'pattern': ['blargh', 'random', 'stuff']}, example_layers)
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'pattern': [123, 456]}, example_layers)

        # Test that an incorrect 'seeding' field makes it invalid.
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'seeding': 'blargh',
                    'pattern': ['any']}, example_layers)
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'seeding': [],
                    'pattern': ['any']}, example_layers)
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'seeding': ['blargh', 'does not exist'],
                    'pattern': ['any']}, example_layers)
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'seeding': [42, 77, 0],
                    'pattern': ['any']}, example_layers)

        # Test that an incorrect 'pattern_repeats' field makes it invalid.
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'pattern': ['any'], 'pattern_repeats': 'supposed to be a number'}, example_layers)
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'pattern': ['any'], 'pattern_repeats': 0}, example_layers)
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'pattern': ['any'], 'pattern_repeats': -100}, example_layers)

        # Test that a non-existing filter field name in 'seeding' is invalid.
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'seeding': [{'gamemode': 'blabla', 'THIS_DOES_NOT_EXIST': 'INVALID CONFIG HALP'}],
                    'pattern': ['any']}, example_layers)

        # Test that a config with a non-existing filter field name in 'pattern' is invalid.
        with pytest.raises(squad_map_randomizer.InvalidConfigException):
            squad_map_randomizer.validate_config(
                {'pattern': [
                    {'map': 'unimportant', 'THIS_DOES_NOT_EXIST': 'INVALID CONFIG'},
                    {'map': ['multiple', 'possible', 'map names']},
                    {'map': 'not used really'},
                ]}, example_layers)

    def test_parse_config(self, example_config, example_layers):
        """ Tests that we can call parse_config correctly. """
        # We expect the example config above to exactly match the one parsed from configs/example_config.yml.
        EXAMPLE_CONFIG_PATH = 'configs/example_config.yml'
        with mock.patch('squad_map_randomizer.validate_config'):
            assert squad_map_randomizer.parse_config(EXAMPLE_CONFIG_PATH, example_layers) == example_config
