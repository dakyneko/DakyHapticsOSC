# DakyHapticsOSC
My goal is to make an OSC server optimized for VRChat/ChilloutVR, that is flexible and modular enough to use with DIY haptics devices.
Originally I have implemented my own server with fancy velocity-based behavior for my own hardware, it worked quite well and now it's time I make a new version that I can publish and share for the community: that is the effort of this repository.

Features:
- React to velocity or proximity, with lots of parameter to tune to your liking
- Combo "Daky stack" Python OSC software + Arduino firmware (ESP32/Pico)
- Customization for your own setup using a single config file (YAML)
- Modular supports: ESP32 and Pico through Wifi and USB and multiple protocols (hopefully senseshift/bH, giggle stuff)

This is work in progress.
The associated firmware to upload on hardware microcontrollers like ESP32 should arrive soon.
In mean time you can use the prototype from gist here: https://gist.github.com/dakyneko/229e7701e375058a6401de5267c3cd08#file-esp32_haptics_example-cpp (ignore the Python code below, it's the predecessor of this repository)

# Install & Run

- git clone
- ensure python ≥3.10
- pip install python-osc pyserial pyserial-asyncio
- cp config_sample.yaml config.yaml
- edit config.yaml
- python run.py config.yaml
