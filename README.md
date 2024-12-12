# DakyHapticsOSC
My goal is to make an OSC server optimized for VRChat/ChilloutVR, that is flexible and modular enough to use with DIY haptics devices.

Features:
- React to velocity or proximity, with lots of parameter to tune to your liking
- Combo "Daky stack" Python OSC software + Arduino firmware (ESP32/Pico)
- Customization for your own setup using a single config file (YAML)
- Modular supports: ESP32 and Pico through Wifi and USB and multiple protocols (hopefully senseshift/bH, giggle stuff)

This is work in progress.
The associated firmware to upload on hardware microcontrollers like ESP32 should arrive soon.
In mean time you can use the prototype from gist here: https://gist.github.com/dakyneko/229e7701e375058a6401de5267c3cd08#file-esp32_haptics_example-cpp (ignore the Python code below, it's the predecessor of this repository)

# Install & Run

- `git clone`
- ensure python ≥3.10
- `pip install -r requirements.txt`
- `cp config_sample.yaml config.yaml`
- `edit config.yaml`
- `python run.py config.yaml`

# Config

The sample file `config_sample.yaml` demonstrates VRChat with 3 haptics points connected an ESP32 running Daky firmware connected to Wifi by UDP.
The yaml files has 2 main sections: games and setup. You may notice `cfg_head` which is not a section but just a shorthand snippet used multiple times later (YAML reference block).

## Game part
The game part: For VRChat, should be all good to go unless you need custom ports or testing (AV3Emul).

## Setup part
The setup part is the one that you will need to focus on. Basically it defines everything happening after the game detect a contact: from an OSC message that need to be mapped to a certain actuator (the brrr), to the computation of strength values, then communicate to its controller (ESP32, Pico, ect) to do its magic brrr.

First pay attention to the OSC **prefix** defined in the router: for VRC it uses OSC, all your receiver components in Unity need to starts with the last part after / which by default is `haptX-`. In Unity for example that 1st actuator `headCheekR` then the parameter name should be `haptX-headCheekR` exactly.

Second you may want to choose the **behavior**, how it reacts to a contact sender: ProximityBased and VelocityBased are available for now.

Third and most technical: the **controllers**. That's where you describe the topoology and behavior of the setup. Basically each controller controls a few actuators based on a certain behavior and receives order over a connection (Wifi UDP, USB, etc) using a certain protocol (Daky, OpenVR, SenseShift, etc). You can give it a name for your benifit.

the **protocol** section defines how to generate commands to communicate with the device correctly (like a language). For now only DakyProtocol. Later it may support more. This relates to the firmware of the controller you're using.

the **connection** section defines where to send orders to reach the controller (like speaking or writting). This can be UDP or USB. For UDP (for ex if you use Wifi), you need to specific the address and the port of the device (eg: ESP32). This also relates to the firmware of the controller you're using. For USB, you'll need to specify the code name and serial.

the **actuators** section:
 - the name is used to address it from OSC, remember the router prefix is appended.
 - the most important `min` and `max` defines the strength value range between 0.0 to 1.0, it's proportional to voltage.
 - For other parameters (included from cfg head) you can keep sane defaults. A few notes: `min_sensitivity` defines the minimum value sent by the behavior below which are considered 0 (useful to prevent motor stall); `collider_scaler` is a magic number relating to the size of your collider in unity, it impacts the scale of numbers. `throttle` depends on the behavior, it's advanced setup.
