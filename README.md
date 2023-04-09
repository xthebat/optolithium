# Optolithium #

![Logo.png](https://bitbucket.org/repo/AzXMMM/images/2525627138-Logo.png)

## What is it? ##

Optolithium is a optical lithography (see [Photolithography](http://en.wikipedia.org/wiki/Photolithography)) modelling software that allow to calculate results at the different steps of process. It's open-source software and it isn't aimed to correspond to high-end VLSI fabrication technological nodes. The main goal of the project is studying students basics of nanotechnological processes (as an example is optical lithography). Optolithium refers to [computational lithography](http://en.wikipedia.org/wiki/Computational_lithography) software and can be used for simulation of different stage of the lithography process. The following stages can be simulated at current version: 

* Aerial image
* Aerial image in resist 
* Exposed latent image in resist
* PEB latent image in resist
* Develop time contours
* Resist profile

Also automated simulation set with variating at most two parameters is available.
At this time only 2D resist profile modelling is implemented but one of roadmap's point is add 3D simulation possibility. The following figure denotes resist profile simulations results for 365 nm technological process:

![Optolithium-Profile.png](https://bitbucket.org/repo/AzXMMM/images/3359108389-Optolithium-Profile.png)
Screenshot of the main window of Optolithium software with simulation results of aerial image in resist as distribution of light intensity. Also an effect of standing waves could be seen in this figure.  

![Optolithium_IR.png](https://bitbucket.org/repo/AzXMMM/images/50062255-Optolithium_IR.png)

## Papers

Note: all papers made in Russian language.

- ![Optical lithography basics](https://github.com/xthebat/optolithium/releases/download/papers/Optical.Lithography.Simulation.Basics.pdf)
- ![Lithography lecture](https://github.com/xthebat/optolithium/releases/download/papers/4.Lecture.ppt.pdf)
- ![Simulation lecture](https://github.com/xthebat/optolithium/releases/download/papers/7.Lecture.ppt.pdf)
- ![Optolithium lecture](https://github.com/xthebat/optolithium/releases/download/papers/8.Lecture.ppt.pdf)

## What are internals? ##

The program can be considered as two main part:

* The Core (OptolithiumC) - part of software that required high performance calculations and different iterations throughout list, arrays and etc.
* The GUI (OptoltihiumGui) - another part where interaction with user performed. This part use OptolithiumC for optical lithography modelling.

Accordingly, Optolithium software separated into two parts, is written primarily by mean of the two complementary programming language: Python (only version 2.7 supported) and C++11x. The Optolithium Core wrapped with Python binding and can be used sheer without OptolithiumGui module. Also software can be extent by plugins. Plugin is standalone shared library with a special exported symbol (descriptor) and Optolithium plugin can represent different objects modelling object:

* Photomask 1D/2D
* Source shape map model
* Optical system pupil filter model
* Resist rate development model

Anyone could simple write own plugin using C programming language with definition in header file:

    <OPTOLITHIUM_SRC>/OptolithiumC/include/optolithium.h

At this time next plugins have already implemented:

* 1D - binary space
* 1D - binary line
* 1D - binary line with SRAF (Sub-Resolution Assist Features)
* Annular source shape
* Partially coherent source shape
* Coherent source shape 
* Mack resist rate model
* Enhanced Mack resist rate model
* Notch resist rate model

## Current software state ##

Optolithium is open source software and under developing. There are a lot of bugs may appear when you work with software. I'll be glad if detailed reports and bug description will be added to issue whenever it possible. That helps me to improve Optolithium and make it more comprehensive.

## How to run software? ##

You can choose one of two choices: the first use prebuilt by mean of Cython executable distributive and the second is compile and configure software by your self. When using prebuilt binaries total package will be in binary but if you will built it from source you can only compile Optolithium Core (not necessarily Cythonize Optolithium GUI module written in pure Python). Development of the source code was carried out with opportunity to compile Optolithium Core under various OS: Windows, Linux and Mac OS X. Currently prebuilt packages you could found in Downloads.

Since a half of program written in Python programming language GUI can be run without any compilation and set up. You only required to install all dependencies libraries that were used in GUI module (see OptolithiumGui below) . As for photolithography modelling core it should be compiled using GCC compatible compiler. To compile go into OptolithiumC directory and run build using CMake:

    cd <OPTOLITHIUM_SRC>/OptolithiumC
    cmake CMakeLists.txt
    make install

These commands will build OptolithiumC module (core) and also build standard plugins set.
The software tested for build with GNU GCC Toolchain hence MinGW required in Windows operating system environment. Also cmake configuration command should be replaced with the next:

    cmake CMakeLists.txt -G "MSYS Makefiles"

## Fourier Transform ##

Since light diffraction simulation is tied to a huge count of Fourier transform calculation a very fast algorithm and approaches or library must be used. The one fastest library to calculate Fourier transform is [FFTW3](http://www.fftw.org/) it can be used thought the front-end is presented in source code. Currently Optolithium used it self Fourier Transform library. FFTW3 can be activated by uncommenting the following line in CMakeLists.txt (see "How to run software?")

    SET(OPTOLITHIUMC_USE_FFTW_LIBRARY "ON") 

and comment the following:

    SET(OPTOLITHIUMC_USE_FOURIER_LIBRARY "ON")

This front-end has been used just to compare performance FFTW3 library and Optolithium Fourier library. The comparison has been made for ~160 1D-simulation of binary line when calculate Focus-Exposure Matrix using  "Simulation Sets" tab (X/Y and Z grid = 5 nm, Speed Factor = 5) on Intel Core i7 2.2 GHz with 8 Gb RAM. In result Optolithium Fourier library is approximately 2.5 times slower then FFTW3 library in presented benchmark (NOTE: it isn't mean that for any other simulation types, masks, models and etc. Optolithium Fourier library will be in 2.5 times slower the results can be different).

The source code of the Optolithium Fourier Transform library is presented under the next path:

    <OPTOLITHIUM_SRC>/OptolithiumC/libs/fourier

The simple benchmark code can be found in src/check.c files

### Optolithium Fourier Transform library License ###

Copyright © 2015 *Alexei Gladkikh*. All rights reserved.
This software may be modified and distributed under the terms of the BSD license.  See the LICENSE file for details.

## Dependencies ##

### Optolithium GUI ###

Because the project required heavily numerical calculation different third party libraries have been used (Note Optolithium has been tested with the specified versions of libraries)

* [Python 2.7.8](https://www.python.org/)
* [PySide 1.2.1](https://pypi.python.org/pypi/PySide)
* [NumPy-1.6.2](https://pypi.python.org/pypi/numpy)
* [SciPy-0.15.1](https://pypi.python.org/pypi/scipy)
* [Matplotlib-1.4.0](https://pypi.python.org/pypi/matplotlib)
* [SQLAlchemy-0.9.4](https://pypi.python.org/pypi/SQLAlchemy)
* [python-gdsii-0.2.1](https://pypi.python.org/pypi/python-gdsii/)
* [bson-0.3.3](https://pypi.python.org/pypi/bson)
* [psutils-2.2.1](https://pypi.python.org/pypi/psutil)
* [filemagic-1.6](https://pypi.python.org/pypi/filemagic/1.6)

Binary packages and libraries

* [File for Windows](http://gnuwin32.sourceforge.net/packages/file.htm) 

### Optolithium Core ###

See in: <OPTOLITHIUM_SRC>/OptolithiumC/libs

* [Armadillo](http://arma.sourceforge.net/)
* [armanpy-0.1.3](http://sourceforge.net/projects/armanpy/) - modified
* [clipper-6.1.3](http://www.angusj.com/delphi/clipper.php)
* [easylogging++.h](https://github.com/easylogging/easyloggingpp)
* [LSMLIB](https://github.com/ktchu/LSMLIB) - modified
* [SWIG-3.0.5](http://www.swig.org/) *Attention*: version equal or above 3.0.5 is required

## Optolithium License ##

Copyright © 2014-2015 *Alexei Gladkikh*

This software is dual-licensed: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version only for NON-COMMERCIAL usage.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
 
If you are interested in other licensing models, including a commercial-license, please contact the author at gladkikhalexei@gmail.com

## Armadillo ##

Armadillo is a C++ linear algebra library (matrix maths) aiming towards a good balance between speed and ease of use. The syntax is deliberately similar to Matlab. The library provides efficient classes for vectors, matrices and cubes, as well as many functions which operate on the classes (eg. contiguous and non-contiguous submatrix views). This library is useful for conversion of research code into production environments, or if C++ has been decided as the language of choice, due to speed and/or integration capabilities.

The library is open-source software, and is distributed under a license that is useful in both open-source and commercial/proprietary contexts. Armadillo is primarily developed at NICTA (Australia), with contributions from around the world.  More information about NICTA can be obtained from http://nicta.com.au

Main developers: Conrad Sanderson(lead developer; NICTA, Australia), Ryan Curtin(sparse matrices; Georgia Tech, USA)

=================================================================================

* The Armadillo library can be distributed and/or modified under the terms of the Mozilla Public License 2.0 (MPL).
* You are free to choose the license for work that uses the Armadillo library (eg. a proprietary application).
* The MPL does not automatically apply to your programs.

## armanpy ##

Copyright © 2012-2014 Thomas Natschlдger (thomas.natschlaeger@gmail.com)

ArmaNpy is a set of SWIG interface files which allows generating Python bindings to C++ code which uses the Armadillo matrix library. From within Python any Armadillo matrices are represented as NumPy matrices. This is possible due to the same memory layout used. Copying of memory is avoided whenever possible. It also supports boost::shared_ptr wrapped return values of Armadillo matrices.

=================================================================================

ArmaNpy is provided without any warranty of fitness for any purpose. You can redistribute this file and/or modify it under the terms of the GNU Lesser General Public License (LGPL) as published by the Free Software Foundation, either version 3 of the License or (at your option) any later version. (see http://www.opensource.org/licenses for more info).

## clipper ##

Copyright © 2010-2014 Angus Johnson. Freeware for both open source and commercial applications (Boost Software License).

The Clipper library performs line & polygon clipping - intersection, union, difference & exclusive-or, and line & polygon offsetting. The library is based on Vatti's clipping algorithm. The download package contains the library's full source code (written in Delphi, C++ and C#), numerous demos, a help file and links to third party Python, Perl, Ruby and Haskell modules.

## LSMLIB ##

Copyright © 2005 The Trustees of Princeton University and Board of Regents of the University of Texas.  All rights reserved.
Copyright © 2009 Kevin T. Chu.  All rights reserved.

The Level Set Method Library (LSMLIB) provides support for the serial and parallel simulation of implicit surface and curve dynamics in two- and three-dimensions. It contains an implementation of the basic level set method algorithms and numerical kernels described in "Level Set Methods and Dynamics Implicit Surfaces" by S. Osher and R. Fedkiw and "Level Set Methods and Fast Marching Methods" by J.A. Sethian. It also contains implementations of several advanced level set method techniques available in the literature.

=================================================================================

Full license text you could found [here](https://github.com/ktchu/LSMLIB/blob/master/LICENSE)

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
* Redistribution and use of the software (in either source code or binary form) must be for research or instructional use.
* Neither the name of Princeton University, the University of Texas at Austin nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior  written permission.

## Easylogging++ ##

Copyright © 2015 muflihun.com under the terms of The MIT License (MIT)

Easylogging++ is single header only, feature-rich, efficient logging library for C++ applications. It has been written keeping three things in mind; performance, management (setup, configure, logging, simplicity) and portability. Its highly configurable and extremely useful for small to large sized projects.

## PySide ##

Copyright PySide Team under the terms of the GNU Lesser General Public License (LGPL) as published by the Free Software Foundation.

Python bindings for the Qt cross-platform application and UI framework. PySide is the Python Qt bindings project, providing access the complete Qt 4.8 framework as well as to generator tools for rapidly generating bindings for any C++ libraries. The PySide project is developed in the open, with all facilities you’d expect from any modern OSS project such as all code in a git repository, an open Bugzilla for reporting bugs, and an open design process. We welcome any contribution without requiring a transfer of copyright.

## NumPy ##

Copyright NumPy Developers under the terms of BSD license.

NumPy is a general-purpose array-processing package designed to efficiently manipulate large multi-dimensional arrays of arbitrary records without sacrificing too much speed for small multi-dimensional arrays. NumPy is built on the Numeric code base and adds features introduced by numarray as well as an extended C-API and the ability to create arrays of arbitrary type which also makes NumPy suitable for interfacing with general-purpose data-base applications. There are also basic facilities for discrete fourier transform, basic linear algebra and random number generation.

## SciPy ##

Copyright SciPy Developers under the terms of BSD license.

SciPy (pronounced “Sigh Pie”) is open-source software for mathematics, science, and engineering. The SciPy library depends on NumPy, which provides convenient and fast N-dimensional array manipulation. The SciPy library is built to work with NumPy arrays, and provides many user-friendly and efficient numerical routines such as routines for numerical integration and optimization. Together, they run on all popular operating systems, are quick to install, and are free of charge. NumPy and SciPy are easy to use, but powerful enough to be depended upon by some of the world’s leading scientists and engineers. If you need to manipulate numbers on a computer and display or publish the results, give SciPy a try!

## Matplotlib ##

Copyright John D. Hunter, Michael Droettboom under the terms of BSD license.

Python plotting package matplotlib strives to produce publication quality 2D graphics for interactive graphing, scientific publishing, user interface development and web application servers targeting multiple user interfaces and hardcopy output formats. There is a ‘pylab’ mode which emulates matlab graphics.

## SQLAlchemy ##

Copyright Mike Bayer under the terms of MIT license.

SQLAlchemy is the Python SQL toolkit and Object Relational Mapper that gives application developers the full power and flexibility of SQL. SQLAlchemy provides a full suite of well known enterprise-level persistence patterns, designed for efficient and high-performing database access, adapted into a simple and Pythonic domain language.

## python-gdsii ##

Copyright Eugeniy Meshcheryakov under the terms of the GNU Lesser General Public License (LGPL) 3+

python-gdsii is a library that can be used to read, create, modify and save GDSII files. It supports both low-level record I/O and high level interface to GDSII libraries (databases), structures, and elements. This package also includes scripts that can be used to convert binary GDS file to a simple text format (gds2txt), YAML (gds2yaml), and from text fromat back to GDSII (txt2gds).

## bson ##

Copyright Kou Man Tong under the terms of BSD license.

Independent BSON codec for Python that doesn’t depend on MongoDB.

## psutils ##

Copyright Giampaolo Rodola under the terms of BSD license.

psutil is a cross-platform library for retrieving information onrunning processes and system utilization (CPU, memory, disks, network)in Python.

## filemagic ##

Copyright Aaron Iles under the terms of ASL license.

A Python API for libmagic, the library behind the Unix file command
