CMAKE_MINIMUM_REQUIRED(VERSION 2.8)
CMAKE_POLICY(SET CMP0015 NEW)
CMAKE_POLICY(SET CMP0054 OLD)

SET(CMAKE_BUILD_TYPE "Release")
SET(BUILD_DIR "build")

SET(CMAKE_USE_RELATIVE_PATHS ON)
SET(CMAKE_SKIP_RPATH TRUE)

SET(OPTOLITHIUMGUI_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../OptolithiumGui")

SET(src "${CMAKE_CURRENT_SOURCE_DIR}/src")

INCLUDE_DIRECTORIES("../include")

MACRO(SUBDIRLIST result curdir)
  FILE(GLOB children ABSOLUTE ${curdir} ${curdir}/*)
  SET(dirlist "")
  FOREACH(child_path ${children})
  	GET_FILENAME_COMPONENT(child "${child_path}" NAME)
    IF((IS_DIRECTORY "${curdir}/${child}") AND NOT (${curdir} EQUAL "${child}"))
        LIST(APPEND dirlist ${child})
    ENDIF()
  ENDFOREACH()
  SET(${result} ${dirlist})
ENDMACRO()

SUBDIRLIST(subdirs "${src}")

FOREACH(plugins_type ${subdirs})
	# MESSAGE(STATUS "Plugin Type = ${plugins_type}")
	FILE(GLOB plugins_files ABSOLUTE "${src}/${plugins_type}" "${src}/${plugins_type}/*.c")
	FOREACH (plugin_path ${plugins_files})
		GET_FILENAME_COMPONENT(plugin_name "${plugin_path}" NAME_WE)
		SET(input_src "${src}/${plugins_type}/${plugin_name}.c")
		IF (EXISTS "${input_src}")
			MESSAGE(STATUS "${plugins_type}: ${plugin_name}")
			ADD_LIBRARY(${plugin_name} SHARED "${input_src}")
			SET_TARGET_PROPERTIES(${plugin_name} PROPERTIES LIBRARY_OUTPUT_DIRECTORY "${BUILD_DIR}/${plugins_type}/")
			INSTALL(
                TARGETS ${plugin_name} 
                LIBRARY DESTINATION "${OPTOLITHIUMGUI_DIR}/plugins/${plugins_type}/"
                RUNTIME DESTINATION "${OPTOLITHIUMGUI_DIR}/plugins/${plugins_type}/"
            )
		ENDIF()
	ENDFOREACH()
ENDFOREACH()
