## Summary
`squad_map_randomizer` is a script that generates random map rotations for Squad based on filters that you define in a config file.

Optional feature: posts a message containing the generated map rotation to a single Discord channel (requires Discord admin privileges).

## Config File
A map rotation is a sequence of maps consisting of starting maps followed by regular maps. You can specify the number of maps and the kinds of maps by using a config file, which uses a simple YAML format.

The config file specifies:
1. How many maps are in the map rotation.
2. What filters to use for deciding the maps.

### Example Config
For example, the following config describes a map rotation with one Skirmish starting map, and six regular maps that alternate between small, medium, and large in size (notice we only define three regular maps and specify to repeat them twice):

> starting\_maps:
>   - gamemode: Skirmish
> number\_of\_repeats: 2
> regular\_maps:
>   - map\_size: small
>   - map\_size: medium
>   - map\_size: large

Every time the script is run with this config, it will generate a map rotation with randomly chosen maps that follow the specified pattern, like this: skirmish map, small map, medium map, large map, small map, medium map, large map.

See the `configs/examples/` folder for more examples.

### Config Details
As seen in the example above, the config file has three top-level fields:

1. An optional `starting_maps` field to specify the filters used to generate the starting maps. Defaults to empty if unspecified. Not affected by `number_of_repeats`.
2. An optional `number_of_repeats` field to define how many times the rotation should repeat the `regular_maps` field. Defaults to 1 if unspecified.
3. A required `regular_maps` field to define the filters for the map rotation (repeated `number_of_repeats` times).

### Global Filters and Rules
Besides the filters defined in the config, the following rules are applied globally for all map choices:

1. A specific map cannot be repeated in the entire rotation (a without-replacement policy is used when randomly sampling). For example, if `Al Basrah AAS v1` is in the map rotation, then it will only appear once in the map rotation.
2. Distinct map choices with the same map name (e.g. `Belaya RAAS v1` and `Belaya RAAS v2`) can be repeated in the map rotation but they must be far apart by a certain (adjustable) amount. For example, `Belaya RAAS v1` and `Belaya RAAS v2` may both appear in the same map rotation as long as they are not consecutive.
3. All maps marked as bugged are not considered for the map rotation.

## Installation
Requires Python 3.6+ and `pip`. Install required dependencies using `pip3 install -r requirements.txt`.

## Usage

### Basic Usage
To produce a random map rotation using the default options, run: `python3 squad_map_randomizer.py`
This will generate a `MapRotation.cfg` file in the current working directory.

### Discord Message
In order to post the generated map rotation to Discord, follow these steps:
1. Create a webhook for the Discord channel (you must be an admin of that channel).
2. Provide the webhook URL using the `--discord-webhook-url` argument when running the script.
e.g. `python3 squad_map_randomizer.py --discord-webhook-url https://discordapp.com/api/webhooks/...`

### JSON layers file
The script uses a JSON file as input containing all the map layer info in a simple format (lists of dictionaries).  See `https://github.com/bsubei/squad_map_layers` for the default JSON file used with this script.

### Detailed Usage
Run `python3 squad_map_randomizer.py --help` for detailed usage.

## Automating with Crontab
See the `crontab.example` for an example on what to add to the crontab to run this script automatically (Linux). For Windows, please use `schtasks` to schedule this script to run.

## Running unit tests
You can run the unit tests with `python3 -m pytest` in the project root directory (add `-s` to enable `ipdb` support).

## License
The license is GPLv3. See LICENSE file.
