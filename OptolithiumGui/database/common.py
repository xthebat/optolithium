# -*- coding: utf-8 -*-

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
import logging as module_logging
from database import dbparser

import orm

import config
import helpers


__author__ = 'Alexei Gladkikh'


logging = module_logging.getLogger(__name__)
logging.setLevel(module_logging.DEBUG)
helpers.logStreamEnable(logging)


DB_VERSION = 6
DB_SCHEME = "sqlite"


# noinspection PyPep8Naming
def appdbCloseIfError(function):
    def wrapped(inst, *args, **kwargs):
        try:
            return function(inst, *args, **kwargs)
        except:
            inst.close()
            raise
    return wrapped


class ApplicationDatabase(object):

    standard_tables = orm.standard_tables
    plugin_tables = orm.plugin_tables

    # ------------------------------------------------------------------------------------------------------------------

    class OperationError(Exception):
        def __init__(self, *args, **kwargs):
            super(ApplicationDatabase.OperationError, self).__init__(*args, **kwargs)

    class SqlError(OperationError):
        def __init__(self, *args, **kwargs):
            super(ApplicationDatabase.SqlError, self).__init__(*args, **kwargs)

    class ObjectExisted(OperationError):
        def __init__(self, p_object):
            super(ApplicationDatabase.ObjectExisted, self).__init__()
            self.object = p_object

    class ImportError(OperationError):
        def __init__(self, *args, **kwargs):
            super(ApplicationDatabase.ImportError, self).__init__(*args, **kwargs)

    class VersionError(OperationError):
        def __init__(self, version, *args):
            super(ApplicationDatabase.VersionError, self).__init__(*args)
            self.__version = version

        @property
        def version(self):
            return self.__version

    class DefaultObjectsError(OperationError):
        def __init__(self, database, create_callbacks, *args):
            """
            :param ApplicationDatabase database: Database
            :param list create_callbacks: List of callbacks to create default objects
            """
            super(ApplicationDatabase.DefaultObjectsError, self).__init__(*args)
            self.__create_callbacks = create_callbacks
            self.__database = database

        def fix(self):
            for callback in self.__create_callbacks:
                callback(self.__database, commit=True)
            return self.__database

    # ------------------------------------------------------------------------------------------------------------------

    def __init__(self, path):
        self.__path = path
        """:type: str"""
        self.__connection = orm.Connection("%s:///%s" % (DB_SCHEME, path), echo=config.LOG_DATABASE_QUERIES)
        self.__session = orm.Session(bind=self.__connection)
        self.__is_closed = False

        self.__parser = None
        """:type: database.dbparser.GenericParser or None"""

    @property
    def parser(self):
        return self.__parser

    @parser.setter
    def parser(self, value):
        """:type value: database.dbparser.GenericParser or None"""
        if self.__parser and self.__parser.selector is not None:
            logging.warning("Parser has already tethered to the database and will be rewritten!")
            self.__parser.selector = None
        self.__parser = value
        self.__parser.selector = self.__session.query

    def _create_db_scheme(self):
        orm.Base.metadata.create_all(self.__connection)
        self.__session.add(orm.Info(DB_VERSION))
        self.__session.commit()

    @classmethod
    def create(cls, path, rewrite=False):
        """
        Create new database file and initialize it (required for template.db generation)

        :param str path: Path to database file (may be empty string then db created in the memory)
        :param bool rewrite: If True and DB already existed then it will be rewritten
        :raises: ApplicationDatabase.SqlError
        """
        if os.path.isfile(path):
            if rewrite:
                os.remove(path)
            else:
                raise ApplicationDatabase.OperationError("Configuration database already existed!")

        appdb = cls(path)
        appdb._create_db_scheme()

        return appdb

    @staticmethod
    def _check_sqlite_db(path):
        """
        Check that database file existed and file has format of the SQLite database

        :param str path: Database file path
        :raises: ApplicationDatabase.OperationError
        """
        # SQLite database file header is 100 bytes
        if os.path.getsize(path) < 100:
            raise ApplicationDatabase.OperationError("Wrong SQLite file size! (Most possible file is not SQLite)")

        with open(path, "rb") as db_file:
            header = db_file.read(100)

        if header[0:16] != "SQLite format 3\x00":
            raise ApplicationDatabase.OperationError("Wrong SQLite header! (Most possible file is not SQLite database)")

    @staticmethod
    def _check_tables(inspector):
        orm_table_names = orm.tables.keys()
        db_tables_names = inspector.get_table_names()

        orm_set = set(orm_table_names)
        db_set = set(db_tables_names)

        if orm_set != db_set:
            diff = orm_set.symmetric_difference(db_set)
            raise ApplicationDatabase.SqlError("Wrong database scheme:\n*Not equal tables %s" % (" ".join(diff)))

    @staticmethod
    def _check_columns(inspector):
        for table_name, orm_table in orm.tables.iteritems():
            orm_columns = ["%s" % column for column in orm_table.columns]
            db_columns = ["%s.%s" % (table_name, d["name"]) for d in inspector.get_columns(table_name)]

            orm_set = set(orm_columns)
            db_set = set(db_columns)

            if orm_set != db_set:
                diff = orm_set.symmetric_difference(db_set)
                raise ApplicationDatabase.SqlError(
                    "Wrong database table %s columns:\n*Not equal columns %s" %
                    (table_name, " ".join([str(c) for c in diff])))

    @appdbCloseIfError
    def _check_db_scheme(self, check_compat):
        """
        Check database scheme and version

        :param bool check_compat: Check compatibility of the database with supported scheme
        :raises: ApplicationDatabase.SqlError
        """
        logging.info("Check database scheme")

        try:
            info = self.__session.query(orm.Info).one()
        except orm.NoResultFound:
            raise ApplicationDatabase.SqlError("Version record in application database not found!")
        except orm.MultipleResultsFound:
            raise ApplicationDatabase.SqlError("Info table in application database not found!")

        if check_compat:
            if info.version != DB_VERSION:
                raise ApplicationDatabase.VersionError(info.version, "Database version not supported!")
            inspector = orm.Inspector.from_engine(self.__connection)
            self._check_tables(inspector)
            self._check_columns(inspector)

    @classmethod
    def open(cls, path, create=False, check_compat=True):
        """
        Open existed database and check it

        :param str path: Path to database file
        :param bool create: Create the database if not existed
        :param bool check_compat: Check the version of the database scheme also
        :raises: ApplicationDatabase.OperationError, ApplicationDatabase.SqlError
        """
        logging.info("Open application database: %s" % path)

        if not os.path.isfile(path):
            if create:
                appdb = cls(path)
                appdb._create_db_scheme()
            else:
                raise ApplicationDatabase.OperationError("Application database file not found!")
        else:
            cls._check_sqlite_db(path)
            appdb = cls(path)
            appdb._check_db_scheme(check_compat)

        return appdb

    def close(self):
        self.__session.close()
        self.__is_closed = True

    @property
    def closed(self):
        return self.__is_closed

    def _existed(self, p_object):
        """
        :type p_object: orm.Generic
        :rtype: bool
        """
        return self.__session.query(orm.Generic).filter(orm.Generic.name == p_object.name).first() is not None

    def commit(self):
        try:
            self.__session.commit()

        except (orm.IntegrityError, orm.OperationalError) as error:
            self.__session.rollback()
            signature = "CHECK constraint failed: "
            if signature in error.orig.message:
                message = "While added %s: %s" % (error.params, error.orig.message.split(signature)[-1])
            else:
                message = error.message
            raise ApplicationDatabase.SqlError(message)

        except:
            self.__session.rollback()
            raise

    def add(self, p_object, commit=True):
        """
        Add object to the database store

        :param orm.Generic p_object: ORM Object to be added to the database
        :param bool commit: Commit changes after modification
        :raises: ApplicationDatabase.ObjectExisted
        :rtype: list of orm.Generic
        """
        if self._existed(p_object):
            raise ApplicationDatabase.ObjectExisted(p_object)

        self.__session.add(p_object)

        new_objects = [obj for obj in self.__session.new if isinstance(obj, orm.Generic)]

        if commit:
            self.commit()

        return new_objects

    def remove(self, name=None, p_object=None, commit=True):
        """
        Remove object from the database using an object or using name of the object

        :param string name: Removing object name
        :param orm.Generic p_object: Removing object
        :param bool commit: Commit changes after modification
        :rtype: list of orm.Generic
        """
        if name is not None:
            try:
                this = self.__session.query(orm.Generic).filter(orm.Generic.name == name).one()
            except orm.NoResultFound:
                pass
            else:
                logging.debug("Remove object: %s" % this)
                self.__session.delete(this)
        elif p_object is not None:
            self.__session.delete(p_object)
        else:
            raise ValueError("Name of the object or deleted object must be set!")

        deleted = [obj for obj in self.__session.deleted if isinstance(obj, orm.Generic)]

        if commit:
            self.commit()

        return deleted

    def replace(self, p_object, commit=True):
        """
        Replace object in the database store. Exception will be raised if object was not found in DB.

        :param orm.Generic p_object: ORM Object to be added to the database
        :param commit: Commit changes after modification
        """
        # Commit required because it can be composed objects that also must be deleted
        # So after_flush (see orm module) must executed
        self.remove(name=p_object.name, commit=True)
        self.add(p_object, commit)

    def import_object(self, path):
        """:rtype: list of orm.Generic"""
        filename = helpers.GetFilename(path)
        try:
            p_object = self.__parser.parse(path)
            new_objects = self.add(p_object)
        except dbparser.GenericParserError as error:
            logging.info("Parsing error: %s" % path)
            raise ApplicationDatabase.ImportError("Parsing error: %s\n\n%s!" % (filename, error.message))
        except ApplicationDatabase.SqlError as error:
            logging.info("Insert error: %s" % path)
            raise ApplicationDatabase.ImportError("Inserting into database error: %s\n\n%s" % (filename, error.message))
        else:
            return new_objects

    @property
    def path(self):
        return self.__path

    @appdbCloseIfError
    def __getitem__(self, item):
        """:rtype: sqlalchemy.orm.Query"""
        return self.__session.query(item)