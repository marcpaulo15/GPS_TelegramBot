# GPS Telegram Bot
Implementation of a Telegram Bot to get you from A to B
TODO...

# Introduction
TODO...

# Project Structure
TODO...
## Guide Module
TODO...
## Bot Module
TODO...

# How to create a Telegram Bot
TODO...

# How to interact with the Bot
TODO...

# Getting started 
First, please make sure you have [Python](https://www.python.org/downloads/) installed.

Before installing the **Python libraries** used in this project, you may want to create a **Python Virtual Environment** ([venv](https://www.python.org/downloads/)), to avoid problems if you are working on other projects as well.

The Python Libraries used in this project are listed in the ```requirements.txt``` file. There you will find the Python libraries and their versions. You may use a package manager called ```pip``` to install them. If ```pip``` is not installed, you need to install it. If you have Python 3.4 or newer, pip should come pre-installed.

Enter your project directory:
```
cd <YOUR_PROJECT_DIR>
```

Clone the repository:
```
git clone https://github.com/marcpaulo15/GPS_TelegramBot.git
```

Create and activate your **Python Virtual Environment**. Then run the following command to install the libraries listed in your requirements.txt file:
```
pip install -r requirements.txt
```

To activate the Bot, run the following command in your project directory:
```
python3 src/main_bot.py
```

Then, you can interact with your Bot through the Telegram App (mobile or desktop)

# Dependencies

### [Haversine](https://pypi.org/project/haversine/)
The **Haversine** library is a Python package designed to **calculate the distance between two points on the Earth** given their latitude and longitude. The library is handy for applications that involve geospatial calculations, such as determining distances between locations. It uses the [**haversine formula**](https://en.wikipedia.org/wiki/Haversine_formula) to compute distances. The library supports various units for distance measurement, such as kilometers, miles, nautical miles, and meters.

### [NetworkX](https://networkx.org/documentation/stable/)
The **NetworkX** library is a powerful Python package for the creation, manipulation, and study of the structure, dynamics, and functions of complex networks (a.k.a. graphs). Networks, in this context, are mathematical representations of relationships between a set of objects, and they are widely used in various fields such as social network analysis, biological network analysis, transportation networks, and more.

The library includes **a wide range of algorithms for analyzing graphs**, including algorithms for finding paths, clustering coefficients, centrality measures, and community detection. It also allows for the visualization of graphs, providing tools to create clear and informative visual representations of network structures.


### [OSMnx](https://osmnx.readthedocs.io/en/stable/)
**OSMnx** is a Python library for **retrieving, modeling, analyzing, and visualizing street networks from [OpenStreetMap (OSM)](https://www.openstreetmap.org/#map=19/41.38657/2.09301&layers=G)** data. It simplifies the process of working with spatial and network data related to urban planning, transportation, and geography. This library allows users to download and construct street networks from OpenStreetMap data by specifying a bounding box or by providing other location information. The library provides **a NetworkX graph representation of the street network**, making it compatible with various network analysis tools (like the ```NetworkX`` library)

### [StaticMap](https://github.com/komoot/staticmap)
A small, python-based library for **creating map images with lines and markers**.
StaticMap is open source and licensed under Apache License, Version 2.0.

### [GeoPy](https://geopy.readthedocs.io/en/stable/)
The GeoPy library is a Python client for several popular **geocoding web services**. Geocoding is the process of converting addresses (like "1600 Amphitheatre Parkway, Mountain View, CA") into geographic coordinates (like latitude 37.423021 and longitude -122.083739), which can then be used for mapping or other location-based applications.

### [Telegram-Api-Bot](https://docs.python-telegram-bot.org/en/v20.6/)
For **interacting with the Telegram API in Python**, the python-telegram-bot library is commonly used. This library provides a convenient interface for working with the Telegram Bot API, allowing you to create and manage Telegram bots. The library facilitates the creation of Telegram bots, allowing developers to handle messages,and process commands and updates. The library supports sending and receiving files, location, photos, videos, and other media types.

### [PyYAML](https://pyyaml.org/wiki/PyYAMLDocumentation)
*"Yet Another Markup Language"* (**YAML**) is a human-readable data serialization format. **It's often used for configuration files**, data exchange between languages with different data structures, and in various applications where data needs to be stored, transmitted, or configured in a human-readable format. YAML's design aims to be simple and easy for both humans to read and write and for machines to parse and generate.

# Contribute
Contributions to this project are welcome! If you'd like to improve the game, fix bugs, or add new features, feel free to fork the repository and submit a pull request.


# License
This project is licensed under the MIT License. See the [LICENSE file](./LICENSE) for details.

# Hope you enjoyed it! Thanks! :)
