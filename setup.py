from setuptools import setup, find_packages

with open("qth_chromecast/version.py", "r") as f:
    exec(f.read())

setup(
    name="qth_chromecast",
    version=__version__,
    packages=find_packages(),

    # Metadata for PyPi
    url="https://github.com/mossblaser/qth_chromecast",
    author="Jonathan Heathcote",
    description="A minimal Qth interface for controlling Chromecast devices.",
    license="GPLv2",
    classifiers=[
        "Development Status :: 3 - Alpha",

        "Intended Audience :: Developers",

        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",

        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",

        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
    ],
    keywords="home-automation chromecast",

    # Requirements
    install_requires=["qth>=0.6.0", "pychromecast"],

    # Scripts
    entry_points={
        "console_scripts": [
            "qth_chromecast = qth_chromecast:main",
        ],
    }
)
