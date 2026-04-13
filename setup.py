import pathlib
import setuptools

setuptools.setup(
    name="easy_frankfurter",
    version="1.0.0",
    description="A lightweight Python wrapper for the Frankfurter API with v1 and v2 support",
    long_description=pathlib.Path("README.md").read_text(encoding='utf-8'),
    long_description_content_type="text/markdown",
    url="https://github.com/theimes/frankfurter",
    author="Thorsten Heimes",
    license="MIT",
    project_urls={
        "Homepage": "https://github.com/theimes/frankfurter",
        "Repository": "https://github.com/theimes/frankfurter",
    },
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.8",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    packages=setuptools.find_packages(),
    include_package_data=True,
)
