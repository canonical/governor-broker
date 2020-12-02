from setuptools import setup, find_packages
setup(
    name="governor-broker",
    version="0.1",
    packages=["broker"],
    entry_points={
        "console_scripts": [
            "broker=broker.main:main"]
        },
)
