from setuptools import setup, find_packages
with open(requeriments.txt) as f:
	requeriments = f.readlines()

setup(
	name="analystty",
	version="0.1",
	description="Analysis automation tests",
	author="tty503",
	packages=find_packages(),
	install_requires=requeriments
)