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

#ifndef ITERABLE_H_
#define ITERABLE_H_

#include <stdint.h>
#include <opl_log.h>

namespace Iterable
{
	inline uint32_t indx(int32_t k, int32_t len) {
        return static_cast<uint32_t>((k < 0) ? (len + k) % len : k % len);
	}

	template <class object_t>
	class Interface;

	template <class object_t>
	class Iterator
	{
	private:
		uint32_t _pos;
		const Interface<object_t> *_container;

	public:
		Iterator(const Interface<object_t>* p_vec, uint32_t pos): _pos(pos), _container(p_vec){ }

		uint32_t pos(void) const {
			return this->_pos;
		}

		// these three methods form the basis of an iterator for use with a range-based for loop
		bool operator!= (const Iterator& other) const {
			return this->_pos != other._pos;
		}

		object_t operator*(void) const {
			return this->_container->at(indx(this->_pos, this->_container->length()));
		}

		const Iterator& operator++ () {
			++_pos;
			// although not strictly necessary for a range-based for loop
			// following the normal convention of returning a value from
			// operator++ is a good idea.
			return *this;
		}

		Iterator begin(void) const {
			return this->_container->begin();
		}

		Iterator end(void) const {
			return this->_container->end();
		}

		Iterator next(void) const {
			return Iterator(this->_container, indx(this->_pos+1, this->_container->length()));
		}

		Iterator prev(void) const {
			return Iterator(this->_container, indx(this->_pos-1, this->_container->length()));
		}
	};

	template <class object_t>
	class Interface
	{
	public:
		virtual ~Interface() {};

		virtual Iterator<object_t> begin(void) const {
			return Iterator<object_t>(this, 0);
		}

		virtual Iterator<object_t> end(void) const {
			return Iterator<object_t>(this, this->length());
		}

		virtual object_t front(void) const {
			return this->at(0);
		}

		virtual object_t back(void) const {
			return this->at(this->length()-1);
		}

		virtual object_t at(uint32_t index) const = 0;
		virtual uint32_t length(void) const = 0;
	};
}

#endif /* ITERABLE_H_ */
