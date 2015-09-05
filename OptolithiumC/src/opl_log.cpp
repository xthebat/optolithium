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

#include "opl_log.h"


_INITIALIZE_EASYLOGGINGPP


OptolithiumCoreLog::OptolithiumCoreLog(void) {
	el::Loggers::reconfigureAllLoggers(el::ConfigurationType::Format,
			"%level %datetime{%H:%m:%s} [%file:%line]: %msg");
	el::Loggers::reconfigureAllLoggers(el::ConfigurationType::ToStandardOutput, "true");
	el::Loggers::addFlag(el::LoggingFlag::ColoredTerminalOutput);
	LOG(INFO) << "Initialize Optolithium Core logging system";
};

OptolithiumCoreLog::~OptolithiumCoreLog(void) {
	LOG(INFO) << "Finalize Optolithium Core logging system";
};

void OptolithiumCoreLog::set_verbose_level(int level) {
	int argc = 2;
	std::ostringstream verbosity;
	verbosity << "--v=" << level;
	const char *argv[2] = { "Optolithium",  verbosity.str().c_str() };
	el::Helpers::setArgs(argc, argv);
};

void OptolithiumCoreLog::log(const std::string &message) {
	LOG(INFO) << message;
};

void OptolithiumCoreLog::vlog(const std::string &message, int level) {
	VLOG(level) << message;
}
