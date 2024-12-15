# DakyHapticsOSC
My goal is to make an OSC server optimized for VRChat/ChilloutVR, that is flexible and modular enough to use with DIY haptics devices.

**Features**:
- React to velocity or proximity, with lots of parameter to tune to your liking
- Combo "Daky stack" Python OSC software + Arduino firmware (ESP32/Pico)
- Customization for your own setup using a single config file (YAML)
- Modular supports: ESP32 and Pico through Wifi and USB and multiple protocols (hopefully senseshift/bH, giggle stuff)

This is work in progress.
This repository is the **software** that runs on your PC and will communicate with VRC. That alone isn't enough, you also need the **firmware** (embedded software) that runs on your microcontrollers/haptic devices: the recommended and simplest way is to use the companion project implementing The DakyProtocol: https://github.com/dakyneko/DakyHapticsFirmware . It's the simplest way to get started with custom hardware ESP32. However you can use your own or some third party if supported (or you can contribute, PR welcome).

# Install & Run

- `git clone`
- ensure python ≥3.10
- `pip install -r requirements.txt`
- `cp config_sample.yaml config.yaml`
- `edit config.yaml`
- `python run.py config.yaml`

# Config

The sample file `config_sample.yaml` demonstrates VRChat with 3 haptics points controlled by an ESP32 running Daky firmware connected to Wifi by UDP.
The yaml files has 2 main sections: games and setup. You may notice `cfg_head` which is not a section but just a shorthand snippet used multiple times later (YAML reference block).

## Game part
The game part: For VRChat, should be all good to go unless you need custom ports or testing (AV3Emul).

## Setup part
The setup part is the one that you will need to focus on. Basically it defines everything happening after the game detect a contact: from an OSC message that need to be mapped to a certain actuator (the brrr), to the computation of strength values, then communicate to its controller (ESP32, Pico, ect) to do its magic brrr.

First pay attention to the OSC **prefix** defined in the router: for VRC it uses OSC, all your receiver components in Unity need to starts with the last part after / which by default is `haptX-`. In Unity for example that 1st actuator `headCheekR` then the parameter name should be `haptX-headCheekR` exactly.

Second you may want to choose the **behavior**, how it reacts to a contact sender: ProximityBased and VelocityBased are available for now.

Third and most technical: the **controllers**. That's where you describe the topoology and behavior of the setup. Basically each controller controls a few actuators based on a certain behavior and receives order over a connection (Wifi UDP, USB, etc) using a certain protocol (Daky, OpenVR, SenseShift, etc). You can give it a name for your benefit.

the **protocol** section defines how to generate commands to communicate with the device correctly (like a language). For now only DakyProtocol. Later it may support more. This relates to the firmware of the controller you're using (for DakyProtocol use the companion DakyHapticsFirmware linked above in the intro).

the **connection** section defines where to send orders to reach the controller (like speaking or writting). This can be UDP or USB. For UDP (for ex if you use Wifi), you need to specific the address and the port of the device (eg: ESP32). This also relates to the firmware of the controller you're using. For USB, you'll need to specify the code name and serial.

the **actuators** section:
 - this is a mapping from the address to its configuration. The address is determined by the firmware you're using. For DakyProtocol it's the index number starting from 0, look at the `motor_pins` definitions, this is part of the firmware setup (see the companion DakyHapticsFirmware link above).
 - the name is used to address it from OSC, remember the router prefix is appended.
 - the most important `min` and `max` defines the strength value range between 0.0 to 1.0, it's proportional to voltage.
 - For other parameters (included from cfg head) you can keep sane defaults. A few notes: `min_sensitivity` defines the minimum value sent by the behavior below which are considered 0 (useful to prevent **motor stall**); `collider_scaler` is a magic number relating to the size of your **collider** in unity, it impacts the scale of numbers. `throttle` depends on the behavior, it's advanced setup.


# Game setup

The setup will receive command from a game, like VRChat (VRC) or ChilloutVR (CVR). *TODO*: write more instructions about OSC setup: especially CVR need a mod.

## VRChat and Avatar Unity

Two parts: Avatar in unity and OSC json.

**Avatar** part:
- for VRC to send OSC message it needs one collider with one parameter each. With avatar this is done by adding a contact receiver in proximity mode with the correct parameter name (example above: `haptX-headCheekR`). Notes:
  - It is recommended to disable collision on self.
  - You don't have to define the parameter in the avatar VRC descriptor nor do so in the animator, it is only used locally.
  - Be sure that each collider shape is big enough to capture where you want to have haptics and ideally they don't overlap for a better effect.
  - Also note your collider size will impact the value computed by the behavior in the haptic setup. If you use VelocityBased behavior, you may need to tweak the `collider_scaler`, which is around 5 for a body part, like the head top. Yes, it's a heuristic magic value, the tested avatar is around 1m tall so if it's twice bigger or smaller, adjust in proportion.

**OSC** part:
- you can check the official doc <https://docs.vrchat.com/docs/osc-avatar-parameters>. Don't forget each of your parameter must be present in there to tell VRC to send it by OSC, otherwise it won't work.
    - *TODO*: complete the doc with an example

**Testing**:
It is possible to test in Unity using AV3Emulator (check VRC companion to install the extension). The result isn't exactly 100% the same, for example it doesn't respect "ignore self collision" so you will need to move each sender away or disable avatar colliders. Enable the OSC mode and it should connect.

## ChilloutVR

*TODO*: OSC mod by kafy and document when implemented + tested.
