# -*- coding=UTF-8 -*-
"""Uploader control.  """
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging
import os
from collections import namedtuple
from multiprocessing.dummy import Pool

from Qt.QtCore import QCoreApplication, QObject, Qt, QTimer, Signal
from six import text_type
from six.moves import range

import cgtwq
from wlf import mp_logging
from wlf.decorators import run_async
from wlf.files import is_same, version_filter
from wlf.notify import CancelledError, progress
from wlf.path import PurePath

from .__about__ import __version__
#         ret = self.dest_dict.get(PurePath(filename).shot, self.dest)
#         if isinstance(ret, (str, unicode)):
#             ret = str(PurePath(ret) / PurePath(filename).as_no_version())
#         return ret
from .model import ROLE_DEST, VersionFilterProxyModel, ROLE_CHECKABLE
from .util import LOGGER

# class ShotsFileDirectory(QObject):
#     """Directory that store shots output files.  """

#     pipeline_ext = {
#         '灯光': ('.jpg', '.png', '.jpeg'),
#         '渲染': ('.mov',),
#         '合成': ('.mov',),
#         '输出': ('.mov',)
#     }
#     dest_dict = None
#     changed = Signal()
#     updating = False
#     _uploaded = None

#     def __init__(self, path, pipeline, dest=None, parent=None):
#         assert os.path.exists(
#             path), '{} is not existed.'.format(path)
#         assert pipeline in self.pipeline_ext, '{} is not a pipeline'.format(
#             pipeline)

#         LOGGER.debug('Init directory.')
#         super(ShotsFileDirectory, self).__init__()
#         self.path = path
#         self.pipeline = pipeline
#         self.ext = self.pipeline_ext[pipeline]
#         self.dest = dest
#         self.files = []
#         self.dest_dict = {}
#         self.parent = parent

#         # Direcotry update timer
#         self.update_timer = QTimer(self)
#         self.update_timer.setInterval(1000)
#         self.update_timer.timeout.connect(self.update)

#     @run_async
#     def update(self):
#         """Update directory content.  """

#         if self.updating:
#             return

#         self.updating = True

#         if self.update_uploaded():
#             self.changed.emit()
#         try:
#             path = self.path
#             prev_files = self.files
#             prev_shots = self.shots()
#             self.files = version_filter(i for i in os.listdir(path)
#                                         if i.lower().endswith(self.ext))
#             if prev_files == self.files or self.shots() == prev_shots:
#                 return

#             if not prev_files or set(self.files).difference(prev_files):
#                 try:
#                     self.dest_dict = self.get_dest_dict()
#                 except CancelledError:
#                     self.dest_dict = {}
#                     LOGGER.info('用户取消获取信息')
#             self.changed.emit()
#         finally:
#             self.updating = False

#     def get_dest_dict(self):
#         """Get upload destinations.  """

#         code_dict = {i[0]: i[1] for i
#                      in cgtwq.PROJECT.all().get_fields('code', 'database')}

#         def _get_database(filename):
#             for k, v in code_dict.items():
#                 if PurePath(filename).name.startswith(k):
#                     return v
#             raise ValueError('Can not match file to databse.')

#         all_shots = self.shots()
#         dest = self.dest
#         dest_dict = {}

#         def _get_from_database(database):
#             if self.dest:
#                 return

#             shots = [i for i in all_shots if _get_database(i) == database]

#             module = cgtwq.Database(database)['shot_task']
#             select = module.filter(
#                 (cgtwq.Field('shot.shot') | shots)
#                 & (cgtwq.Field('pipeline') == self.pipeline)
#             )

#             current_id = cgtwq.current_account_id()
#             current_name = cgtwq.current_account()

#             for i in progress(select.get_fields('id', 'shot.shot', 'account_id', 'artist'),
#                               '获取镜头信息', parent=self.parent):
#                 id_, shot, account_id, artist = i
#                 try:
#                     if account_id and current_id not in account_id.split(','):
#                         raise cgtwq.AccountError(
#                             owner=artist, current=current_name)
#                     dest_dict[shot] = module.select(
#                         id_).get_filebox_submit().path
#                 except cgtwq.CGTeamWorkException as ex:
#                     dest_dict[shot] = ex
#                 except KeyError as ex:
#                     dest_dict[shot] = cgtwq.IDError(ex)

#         if not dest:
#             all_database = set(_get_database(i) for i in self.files)
#             for database in progress(all_database, '连接数据库', parent=self.parent):
#                 _get_from_database(database)

#         return dest_dict

#     def shots(self):
#         """Files related shots.  """

#         return sorted(PurePath(i).shot for i in self.files)

#     @property
#     def unexpected(self):
#         """Files that can not get destination.  """

#         files = self.files
#         ret = set()

#         for filename in files:
#             dest = self.get_dest(filename)
#             if not dest or isinstance(dest, Exception):
#                 ret.add(filename)
#         return ret

#     @property
#     def uploaded(self):
#         """Files that does not need to upload agian.  """

#         if self._uploaded is None:
#             self.update_uploaded()
#         return self._uploaded

#     def update_uploaded(self):
#         """Update uploaded files.  """

#         old_value = self._uploaded
#         files = self.files
#         ret = set()

#         for filename in files:
#             src = os.path.join(self.path, filename)
#             dst = self.get_dest(filename)

#             if isinstance(dst, (str, unicode)) and is_same(src, dst):
#                 ret.add(filename)

#         self._uploaded = ret

#         return old_value != ret

#     def get_dest(self, filename):
#         """Get cgteamwork upload destination for @filename.  """
from Qt.QtGui import QBrush, QColor

from wlf.env import has_nuke
from .model import DirectoryModel, VersionFilterProxyModel


class Controller(QObject):
    """Controller for uploader.  """
    root_changed = Signal(str)
    pipeline = '合成'
    if has_nuke():
        brushes = {'local': QBrush(QColor(200, 200, 200)),
                   'uploaded': QBrush(QColor(100, 100, 100)),
                   'error': QBrush(Qt.red)}
    else:
        brushes = {'local': QBrush(Qt.black),
                   'uploaded': QBrush(Qt.gray),
                   'error': QBrush(Qt.red)}

    def __init__(self, parent=None):
        super(Controller, self).__init__(parent)
        model = DirectoryModel(self)

        proxy_model = VersionFilterProxyModel(self)

        proxy_model.setSourceModel(model)
        self.model = proxy_model
        self.model.dataChanged.connect(self.on_data_changed)
        self.model.sourceModel().directoryLoaded.connect(self.update_model)

    def on_data_changed(self):
        pass

    def change_pipeline(self, value):
        self.pipeline = value
        self.update_model()

    def change_root(self, value):
        self.model.sourceModel().setRootPath(value)
        self.root_changed.emit(value)

    def source_index(self, path):
        model = self.model
        source_model = model.sourceModel()
        return model.mapFromSource(source_model.index(path))

    def update_model(self):
        """Update directory model.  """

        QCoreApplication.processEvents()

        model = self.model
        root_index = model.root_index()
        project_data = cgtwq.PROJECT.all().get_fields('code', 'database')
        cgtwq.update_setting()
        current_id = cgtwq.current_account_id()

        def _get_database(filename):
            for i in project_data:
                code, database = i
                if text_type(filename).startswith(code):
                    return database
            raise ValueError('Can not determinate database from filename.')

        def _do(i):
            index = model.index(i, 0, root_index)
            filename = model.data(index)
            try:
                try:
                    database = _get_database(filename)
                except ValueError:
                    model.setData(index, Qt.Unchecked, Qt.CheckStateRole)
                    model.setData(index, '找不到对应数据库', Qt.ToolTipRole)
                    return
                shot = PurePath(filename).shot
                module = cgtwq.Database(database)['shot_task']
                select = module.filter(
                    (cgtwq.Field('pipeline') == self.pipeline)
                    & (cgtwq.Field('shot.shot') == shot)
                )
                try:
                    entry = select.to_entry()
                except ValueError:
                    # TODO
                    entry = select.to_entries()[0]

                dest = (PurePath(entry.filebox.get_submit().path) /
                        PurePath(shot).with_suffix(PurePath(filename).suffix)).as_posix()

                # Set dest.
                model.setData(index, dest, ROLE_DEST)

                # Set tooltip.
                model.setData(index,
                              '<br>'.join([
                                  '数据库: {0}'.format(database),
                                  '镜头: {0}'.format(shot),
                                  '目的地: {0}'.format(dest)
                              ]),
                              Qt.ToolTipRole)

                # Set statustip.
                is_ok = False
                if current_id in entry['account_id'].split(','):
                    is_ok = True
                    model.setData(index, '等待上传', Qt.StatusTipRole)
                else:
                    assigned = entry['artist']
                    model.setData(index,
                                  '此任务已分配给:{0}'.format(assigned)
                                  if assigned else '任务未分配',
                                  Qt.StatusTipRole)

                model.setData(index, is_ok, ROLE_CHECKABLE)
                model.setData(
                    index, Qt.Checked if is_ok else Qt.Unchecked, Qt.CheckStateRole)

                # Set color.
                if is_ok:
                    model.setData(index,
                                  self.brushes['local'],
                                  Qt.ForegroundRole)
                else:
                    model.setData(index,
                                  self.brushes['error'],
                                  Qt.ForegroundRole)

            except:  # pylint: disable=bare-except
                logging.error(
                    'Unexpect error during access database.', exc_info=True)

        pool = Pool()
        count = model.rowCount(model.root_index())
        for _ in progress(
                pool.imap_unordered(_do, range(count)),
                name='访问数据库',
                total=count,
                parent=self.parent()):
            pass

    def upload(self):
        pass


mp_logging.basic_config(level='DEBUG')
