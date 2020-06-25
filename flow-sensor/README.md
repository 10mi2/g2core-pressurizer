![Flow sensor animation](images/v32.2-Animation.gif)

# g2Core Pressurizer Flow Sensor

This project [described in this blog post](https://tenmilesquare.com/designing-and-building-a-ventilator-flow-sensor-from-home-pt-3/) provides a flow sensor that may be used completely independently of the Pressurizer.

# Downloads

| Version | Links |
| ----: | --- |
| v32.2 | [STL](./flow-sensor-v32.2.stl) - [Fusion360](https://a360.co/2NsMhkD) |

# Instructions

## Printable version

Tested by printing with PETG, but PLA should work as well. Print oriented on it's end with the ports pointing **up**. This will leave little contact with the bed, so you'll need to make sure your bed is clean and prepared properly for your type of printer and meaterial. On the Prusa MK3s, that means cleaned with dish soap thoroughly (every 4-5 prints) and then a thin layer of glue stick applied where the print will land and the bottom left corner where it primes the extruder.

### Print Settings:
- NO support (unless you have disolvable support)
- 0.15mm layer height or less (thinner layers are better)
- 15% infill (can be adjusted, not much infill on this one)
- Designed for a 0.4mm nozzle, so that most of the walls are exactly three perimeters width. The wall thickness is a parameter in Fusion360 if it needs to be adjusted


# Python Monitor Usage

The python monitor needs cleaned up and made more user-friendly, but in the interest of getting stuff out there, I'm posting it now as-is.

- Clone or download this repo to a Raspberry Pi (or any machine supported by the [Sparkfun Qwiic Python library](https://github.com/sparkfun/qwiic_py#supported-platforms))
- Make sure you have `python3` and `pip3` installed
- In a terminal (one time, for installation)
  ```bash
  cd flow-sensor/python-flow-sensor-monitor
  pip install -r requirements.txt
  ```
- For now, you have to alter the code for the flow sensors you have
- Near the end, choose what output style you'd like, comment the ones you don't, uncomment the one you do
- Call it:
  ```bash
  ./flow-sensor-monitor.py
  # or to make a csv file
  ./flow-sensor-monitor.py > test-output.csv
  ```
- When you're done, hit `Ctrl-C` (maybe twice) to make it stop

# On the way

- List of sensors that are usable
- Assembly instructions
- More complete calibration instructions, building on those in the [blog post](https://tenmilesquare.com/designing-and-building-a-ventilator-flow-sensor-from-home-pt-3)

# TODO

- Cleanup the python to take a configuration file and command line options.
- Provide calibration Excel / google sheets templates
