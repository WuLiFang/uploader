# -*- coding=UTF-8 -*-
"""Helper for cgtwq query.  """
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from six import text_type

import cgtwq
from wlf.path import PurePath

from .exceptions import DatabaseError


class CGTWQHelper(object):
    """Helper class for cgtwq query.  """
    cache = {}

    @classmethod
    def project_data(cls):
        """Cached project data.  """

        if 'project_data' not in cls.cache:
            cls.cache['project_data'] = cgtwq.PROJECT.all(
            ).get_fields('code', 'database')
        return cls.cache['project_data']

    @classmethod
    def get_database(cls, filename):
        """Get database name from filename.

        Args:
            filename (str): Filename.

        Raises:
            DatabaseError: When can not determinate database from filename.

        Returns:
            str: Database name.
        """

        for i in cls.project_data():
            code, database = i
            if text_type(filename).startswith(code):
                return database
        raise DatabaseError(
            'Can not determinate database from filename.', filename)

    @classmethod
    def get_entry(cls, filename, pipeline):
        """Get entry from filename and pipeline

        Args:
            filename (str): Filename to determinate shot.
            pipeline (str): Server defined pipline name.

        Returns:
            cgtwq.Entry: Entry
        """

        key = (filename, pipeline)
        if key not in cls.cache:
            database = cls.get_database(filename)
            shot = PurePath(filename).shot
            module = cgtwq.Database(database)['shot_task']
            select = module.filter(
                (cgtwq.Field('pipeline') == pipeline)
                & (cgtwq.Field('shot.shot') == shot)
            )
            try:
                entry = select.to_entry()
            except ValueError:
                # TODO
                entry = select.to_entries()[0]
            cls.cache[key] = entry

        return cls.cache[key]
