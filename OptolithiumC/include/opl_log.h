/*
 * opl_log.h
 *
 *  Created on: Jul 22, 2014
 *      Author: batman
 */

#ifndef OPL_LOG_H_
#define OPL_LOG_H_

#include <easylogging++.h>

class OptolithiumCoreLog {
public:
	OptolithiumCoreLog(void);
	virtual ~OptolithiumCoreLog(void);
	void set_verbose_level(int level);
	void log(const std::string &message);
	void vlog(const std::string &message, int level=4);
};


#endif /* OPL_LOG_H_ */
