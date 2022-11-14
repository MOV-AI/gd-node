import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

requirements = [
    "aiohttp==3.8.1",
    "aioredis==1.3.0",
    "bleach==4.1.0",
    "requests==2.22.0",
    "uvloop==0.14.0",
    "dal==1.0.1.0"
]


with open("requirements.txt", "r") as fh:
    for line in fh.readlines(): 
        if line != '\n':
            if '\n' in line:
                line = line.rstrip('\n')
            requirements.append(str(line))



setuptools.setup(
    name="gd-node",
    version="1.0.1-0",
    author="Backend team",
    author_email="backend@mov.ai",
    description="GD_Node",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MOV-AI/gd-node",
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=["Programming Language :: Python :: 3"],
    install_requires=[requirements],
    entry_points={},
)
