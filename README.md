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

Possible environments:
- pypi-experimental (unstable and personal use)
- pypi-integration: Internally avaiable (stable. Where you should grab your dependencies from.)
- pypi-edge: Generally avaiable (Source for production purposes.)


Write the following content into your pip.conf(**~/.config/pip/pip.conf**):
```
[global]
index-url = https://artifacts.cloud.mov.ai/repository/<environment>/simple
extra-index-url = https://pypi.org/simple
trusted-host = artifacts.cloud.mov.ai
               pypi.org
```

## Versioning and branching

The branches and meanings:
- branches derived from dev (feature/ or bugfix/): Its where developements should be introduced to. Its lifetime should be as should as the developments time. 
- dev: The most recent version of the code should be here as its the source of the feature branches. The purpose of this branch is the first point of integration from all features.
- main/ main*: The branch where you will find the most stable version of the component. Its a "deploy" of dev version to an internal release. This deploy must create an artifact that is avaiable to all other teams to use it and provide feedback to it.
- branches derived from main (hotfix/): Its where your hotfixes should be implemented. Do not forget to propagate your hotfixes to the other release versions and the main development release line.
![Screenshot from 2021-10-14 16-29-53](https://user-images.githubusercontent.com/84720623/137349613-368ea252-3c05-460c-8eef-20bb6c4b94f4.png)

In terms of versioning, we basically use semantic versioning but with a 4th digit, automatic incremented by our CI systems:
**{Major}.{Minor}.{Patch}.{buildid}**

If your component has a straight relation with a centralized system, we suggest keeping a relation with it in terms of major,minor and patch to ease support.

## Testing

To run the tests locally, you simply execute:
- python3 -m pytest

## Component packaging
The python component is packaged through the python module **build** and published by the twine **framework**

python3 -m build

python3 -m twine upload -r nexus dist/*

## Component version bumping
To bump the version you can use the **bump2version** framework. Simply in your repository root execute:

bump2version **\<version section>**

version section can be:
- major
- minor
- patch

You don't need to worry about the 4th digit, as the CI system does the automatic bump of it.
