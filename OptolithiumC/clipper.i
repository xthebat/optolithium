/*
 *
 * This file is part of Optolithium lithography modelling software.
 *
 * Copyright (C) 2015 Alexei Gladkikh
 *
 * This software is dual-licensed: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version only for NON-COMMERCIAL usage.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
 *
 * If you are interested in other licensing models, including a commercial-
 * license, please contact the author at gladkikhalexei@gmail.com
 *
 */

%module clipper
%{
    #include "clipper.hpp"
%}

%include <std_vector.i>

%include "clipper.hpp"

%template(Path) std::vector<ClipperLib::IntPoint>;
%template(Paths) std::vector<ClipperLib::Path>;

namespace ClipperLib {

	%pythoncode %{

        def merge(polygons, fillType=pftNonZero):
            result = Paths()
            c = Clipper();
            # c.ForceSimple = True
            for polygon in polygons:
                path = Path([IntPoint(*p) for p in polygon])
                c.AddPath(path, ptSubject, True);
            c.Execute(ctUnion, result, fillType, fillType)
            return [[(point.X, point.Y) for point in polygon] for polygon in polygons]
	%}
}