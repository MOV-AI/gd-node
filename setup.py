import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()


requirements = [
    "aiohttp==3.8.1",
    "aiohttp_cors==0.7.0",
    "bleach==4.1.0",
    "debugpy==1.8.0",
    "uvloop==0.14.0",
    "data-access-layer==2.5.0.*",
]
# requests is required by movai-core-shared
# aioredis is required by data-access-layer


setuptools.setup(
    name="gd-node",
    version="2.5.0-4",
    author="Backend team",
    author_email="backend@mov.ai",
    description="GD_Node",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MOV-AI/gd-node",
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=["Programming Language :: Python :: 3"],
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "gd_node = gd_node.__main__:main",
        ]
    },
)
