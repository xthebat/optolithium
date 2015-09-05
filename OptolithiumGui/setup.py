# This file is part of Optolithium lithography modelling software.
#
# Copyright (C) 2015 Alexei Gladkikh
#
# This software is dual-licensed: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version only for NON-COMMERCIAL usage.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
# If you are interested in other licensing models, including a commercial-
# license, please contact the author at gladkikhalexei@gmail.com


import os
import sys
import time
import hashlib
import shutil
from distutils.extension import Extension
from Cython.Build import cythonize
from info import __name__ as name
from info import __version__ as version


__author__ = 'Alexei Gladkikh'

DO_CYTHONIZE = False

shared_ext = {"nt": ".pyd", "posix": ".so"}[os.name]


try:
    from cx_Freeze import setup, Executable
except ImportError:
    setup = None
    Executable = None


TEMP_CYTHON_C_DIR = "build/temp_c"
TEMP_CYTHON_SHARED_DIR = "build/temp_shared"


CYTHON_EXTENSIONS = [
    Extension("optolithium", ["optolithium.py"]),
    Extension("pcpi", ["pcpi.py"]),
    Extension("physc", ["physc.py"]),
    Extension("plugins", ["plugins.py"]),
    Extension("qt", ["qt.py"]),
    Extension("resources", ["resources.py"]),
    Extension("config", ["config.py"]),
    Extension("core", ["core.py"]),
    Extension("auxmath", ["auxmath.py"]),
    Extension("metrics", ["metrics.py"]),
    Extension("options.structures", ["options/structures.py"]),
    Extension("options.common", ["options/common.py"]),
    Extension("database.common", ["database/common.py"]),
    Extension("database.dbparser", ["database/dbparser.py"]),
    Extension("database.Enum", ["database/Enum.py"]),
    Extension("database.orm", ["database/orm.py"]),
    Extension("database.settings", ["database/settings.py"]),
    Extension("views.common", ["views/common.py"]),
    Extension("views.controls", ["views/controls.py"]),
    Extension("views.dbview", ["views/dbview.py"]),
    Extension("views.development", ["views/development.py"]),
    Extension("views.metrology", ["views/metrology.py"]),
    Extension("views.exposure", ["views/exposure.py"]),
    Extension("views.numerics", ["views/numerics.py"]),
    Extension("views.peb", ["views/peb.py"]),
    Extension("views.resist", ["views/resist.py"]),
    Extension("views.summary", ["views/summary.py"]),
    Extension("views.wafer", ["views/wafer.py"]),
    Extension("views.diffraction", ["views/diffraction.py"]),
    Extension("views.simulations", ["views/simulations.py"]),
]

if os.name == "nt":
    WINLIBS = [
        "zlib1.dll",
        "magic.dll",
        "regex2.dll"
    ]
else:
    WINLIBS = []

# Dependencies are automatically detected, but it might need fine tuning.
CX_BUILD_OPTIONS = {
    # "icon": "icons/ResistProfile.png",
    "packages": [
        "database",
        "views",
        "PySide.QtCore",
        "PySide.QtGui",
        "PySide.QtWebKit",
        "sqlalchemy",
        "matplotlib.figure",
        "matplotlib.backends.backend_qt4agg",
        "scipy.interpolate",
        "scipy.linalg",
        "scipy.special",
        "scipy.sparse",
        "gdsii",
        "magic",
    ],
    "includes": [
        "sqlalchemy.dialects.sqlite",
        "config",
        "core",
        "auxmath",
        "metrics",
        "options",
        "optolithium",
        "optolithiumc",
        "helpers",
        "clipper",
        "pcpi",
        "physc",
        "plugins",
        "qt",
        "resources",
        "webbrowser",
        "psutil",
        "magic",
        "bson",
        "json",
    ],
    "include_files": [
        "matplotlibrc", 
        "icons/", 
        "plugins/", 
        "xhtml/", 
        "share/", 
        "_clipper" + shared_ext,
        "_optolithiumc" + shared_ext,
    ] + WINLIBS,
    "excludes": [
        "apport",
        "apt",
        "PyQt4",
        "_tkinter",
        "Tkinter",
        # "unittest",
        "numpy.distutils",
        # "numpy.testing",
        "setuptools",
        "serial",
        "pysqlite2",
        "apt",
        "compiler",
        "backports",
        "curses",
        # "distutils",
        "email",
        "glib",
        "gobject",
        "importlib",
        "_markerlib",
        "nose",
        "pydoc",
        "pydoc_data",
        # "opcode",
        "ast",
        "BaseHTTPServer",
        "cgi",
        "doctest",
        "_MozillaCookieJar",
        "SimpleHTTPServer",
        "_codecs_cn",
        "_codecs_hk",
        "_codecs_iso2022",
        "_codecs_jp",
        "_codecs_kr",
        "_codecs_tw",
        # "matplotlib._delaunay",
        "urllib.datetime",
        "urllib._heapq",
        "urllib.readline",
    ],
    #"exclude_files": [
    #    "/usr/lib/pymodules/python2.7/matplotlib/mpl-data/fonts/ttf/cmsy10.ttf",
    #]
}


def cmp_hash(file1, file2):
    with open(file1, "rb") as tmp:
        text1 = tmp.read()

    with open(file2, "rb") as tmp:
        text2 = tmp.read()

    hash1 = hashlib.md5()
    hash1.update(text1)
    hash1 = hash1.hexdigest()

    hash2 = hashlib.md5()
    hash2.update(text2)
    hash2 = hash2.hexdigest()

    return hash1 == hash2


def restore_cython_files(tmp_dir, extensions, ext):
    if os.path.exists(tmp_dir):
        for extension in extensions:
            for src in extension.sources:
                path, x = os.path.splitext(src)
                real_path = path + ext
                if os.path.exists(os.path.join(tmp_dir, real_path)):
                    os.rename(os.path.join(tmp_dir, real_path), real_path)


def save_cython_files(tmp_dir, extensions, ext):
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    else:
        shutil.rmtree(tmp_dir)
        os.makedirs(tmp_dir)

    for extension in extensions:
        for src in extension.sources:
            path, x = os.path.splitext(src)
            real_path = path + ext

            if not os.path.exists(os.path.join(tmp_dir, real_path)):
                print "Move %s to %s" % (real_path, os.path.join(tmp_dir, real_path))
                os.renames(real_path, os.path.join(tmp_dir, real_path))

            elif cmp_hash(real_path, os.path.join(tmp_dir, real_path)):
                print "Move %s to %s" % (real_path, os.path.join(tmp_dir, real_path))
                os.renames(real_path, os.path.join(tmp_dir, real_path))


def main():
    # GUI applications require a different base on Windows (the default is for a console application).
    base = None
    if sys.platform == "win32":
        base = "Win32GUI"
        exe_ext = ".exe"
    else:
        exe_ext = ""

    if DO_CYTHONIZE:
        restore_cython_files(TEMP_CYTHON_C_DIR, CYTHON_EXTENSIONS, ext=".c")
        restore_cython_files(TEMP_CYTHON_SHARED_DIR, CYTHON_EXTENSIONS, ext=shared_ext)
        sys.argv = [sys.argv[0], "build_ext", "--inplace"]
        print("Build Cython extensions")
        setup(name=name, version=version, ext_modules=cythonize(CYTHON_EXTENSIONS))
        save_cython_files(TEMP_CYTHON_C_DIR, CYTHON_EXTENSIONS, ext=".c")

    sys.argv = [sys.argv[0], "build"]

    print("Build project")
    
    setup(name=name,
          version=version,
          description="Optolithium Application",
          options={"build_exe": CX_BUILD_OPTIONS},
          executables=[Executable(
              script="main.py",
              targetName=name + exe_ext,
              base=base,
              icon="icon.ico")])
    
    if DO_CYTHONIZE:
        save_cython_files(TEMP_CYTHON_SHARED_DIR, CYTHON_EXTENSIONS, ext=shared_ext)


if __name__ == "__main__":
    start_time = time.time()
    main()
    print("Build Optolithium project done in: %s s" % (time.time() - start_time))
