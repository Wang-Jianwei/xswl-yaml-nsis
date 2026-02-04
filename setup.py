from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="xswl-yaml-nsis",
    version="0.1.0",
    author="Wang-Jianwei",
    description="A lightweight Windows packaging tool that converts YAML to NSIS scripts",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Wang-Jianwei/xswl-yaml-nsis",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "PyYAML>=5.1",
    ],
    entry_points={
        "console_scripts": [
            "xswl-yaml-nsis=xswl_yaml_nsis.cli:main",
        ],
    },
)
