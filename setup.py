from setuptools import setup, find_packages

setup(
    name="market_making",
    version="0.1.0",
    package_dir={"": "src"},  # 告诉setuptools包在src目录下
    packages=find_packages(where="src"),  # 在src目录下查找包
    install_requires=[
    ],
)