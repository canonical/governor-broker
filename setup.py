from setuptools import setup, find_packages
setup(
    name="governor-broker",
    version="0.1",
    packages=["src"],
    entry_points={
        "console_scripts": [
            "broker=src.broker:main"]
        },
)
