# Summary
A script that generates a random map rotation for Squad using a certain pattern. Takes in all the available layers and generates an output `MapRotation.cfg` to be used by your Squad server (needs a restart, see crontab/schtasks to automate this). Optionally sends a Discord message with the map rotation (using a webhook).

# Pattern
    2x Random Skirmish Layers
    Repeat the pattern 5x {
        1x AAS or RAAS layer
        1x AAS or RAAS layer that must have Helicopters
        1x Invasion layer
    }
    
    Layers cannot be repeated in the entire rotation (without replacement policy when sampling).
    A layer cannot be repeated if another layer of the same map was last played three (adjustable) maps ago.  


# Installation
You will need Python 3.6+ installed. Then install required dependencies using `pip3 install -r requirements.txt`. In order to use the `--discord-webhook-url` argument, you need to add a webhook to one of your Discord channels and use the webhook URL for the argument.

# Usage
Run `python3 squad_map_randomizer.py --help` for usage.

# JSON input file
The script requires a JSON input file with all the map layer info in a particular format. 
See `https://github.com/bsubei/squad_map_layers` for an example file (that will hopefully stay updated).

# Running automatically in Crontab
See the `crontab.example` for an example on what to add to the crontab to run this script automatically.

# License
The license is GPLv3. See LICENSE file.
