import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

requires = [
    "beautifulsoup4",
    "html2text",
    "python-mpd2",
    "mutagen",
    "numpy",
    "pillow",
    "pyinotify",
    "pyramid",
    "pyramid_debugtoolbar",
    "requests",
    "scikit-image",
    "sqlalchemy",
    "themyutils",
    "waitress",
    ]

setup(name='player',
      version='0.0',
      description='player',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='',
      author_email='',
      url='',
      keywords='web pyramid pylons',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=requires,
      dependency_links=[
        "https://github.com/themylogin/themyutils/archive/master.zip#egg=themyutils",
        "svn+http://pygoogle.googlecode.com/svn/trunk/#egg=pygoogle",
      ],
      test_suite="player",
      entry_points="""\
      [paste.app_factory]
      main = player:main
      [console_scripts]
      player_updates_manager = player.scripts:updates_manager
      player_rebuild_lyrics = player.scripts:rebuild_lyrics
      """,
      )
