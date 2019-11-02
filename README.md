# Summary
A script that generates a random map rotation for Squad using a certain pattern.

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
You will need Python 3.6+ installed. Then install required dependencies using `pip install -r requirements.txt`.

# Usage
Run `python3 squad_map_randomizer.py --help` for usage.

# JSON input file
The script requires a JSON input file with all the map layer info in a particular format. The default provided JSON file
was last updated by DrStrangeLove in 2019-10-28.

# Running automatically in Crontab
See the `crontab.example` for an example on what to add to the crontab to run this script automatically.

# License
The license is GPLv3. See LICENSE file.
