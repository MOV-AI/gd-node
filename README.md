# gd-node
The gd-node is an extendible and flexible node with the following features:
    1) Can activate ROS1, ROS2 and other protocols such as HTTP
    2) Allows for flexibility via callbacs that can be modified outside of the node 
    3) Provide support for a GUI represintation of the node when building a Flow
A gd-node is represented by a JSON configuration file
A gd-node configuration has the following sections
    1) Info - Provide a general information about the node
    2) Parameters - Provide the nodes parameters and their default values
    3) Ports Info - A list of the nodes' ports
        A port can be an in-port or an out-port
        In-port typically invoke a user define callback provided in the port configuration
        Each port represent a spesific protocol service e.g. ROS1 Publisher, ROS1 Service client ...
        Each port is handeling a spesific message which is specified in the port configuration e.g. std_msgs/Float32 (ROS)

## Usage
GD node is build via the MOV.AI platform node editor
GD node template can be customized for a spesific Flow requirement by modifying the default node template parameters
GD node is used in the context of a flow in which multiple nodes are linked together to generate a desirable robot action
GD node is created as a package and it is used by the Spawner container

> Prerequisites : The GD node depends on the DAL package


## Build

The complete build process:
- a python module building step which will create a `.whl` file


## build pip module

    rm dist/*
    python3 -m build .

## install pip module locally

    python3 -m venv .testenv
    source .testenv/bin/activate
    python3 -m pip install --no-cache-dir \
    --index-url="https://artifacts.cloud.mov.ai/repository/pypi-experimental/simple" \
    --extra-index-url https://pypi.org/simple \
    ./dist/*.whl

