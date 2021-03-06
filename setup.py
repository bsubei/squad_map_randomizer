from setuptools import setup

setup(name='squad_map_randomizer',
      version='0.2.0',
      description='A tool to generate a random map rotation for Squad servers.',
      url='http://github.com/bsubei/squad_map_randomizer',
      author='Basheer Subei',
      author_email='basheersubei@gmail.com',
      license='GPLv3',
      scripts=['squad_map_randomizer.py'],
      package_data={
        '': ['configs/*.yml', 'configs/examples/*.yml'],
        }
      )
