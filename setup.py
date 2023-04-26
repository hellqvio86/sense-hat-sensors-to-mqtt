# from distutils.core import setup
from setuptools import setup, find_packages

# read the contents of README file
from os import path

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="sensehatsensorstomqtt",
    packages=find_packages("src"),
    package_dir={"": "src"},
    version="0.004",
    license="MIT",
    description="sense-hat sensors data to mqtt",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Olof Hellqvist",
    author_email="olof.hellqvist@gmail.com",
    url="https://github.com/hellqvio86/sense-hat-sensors-to-mqtt",
    download_url="https://github.com/hellqvio86/sense-hat-sensors-to-mqtt/archive/v_01.tar.gz",
    keywords=["sense-hat", "temperature", "mqtt"],
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "sensehatsensorstomqtt = sensehatsensorstomqtt.main:main",
        ],
    },
    install_requires=["sense-hat", "paho-mqtt", "pyyaml", "setproctitle", "psutil"],
    extras_require={"tests": ["pyyaml", "pytest"]},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
    ],
)
