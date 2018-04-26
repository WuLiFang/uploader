# -*- coding=UTF-8 -*-
"""Uploader control.  """
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging
import mimetypes
import os
import webbrowser
from multiprocessing.dummy import Pool

from Qt.QtCore import QModelIndex, QObject, Qt, Signal, QCoreApplication
from Qt.QtGui import QBrush, QColor
from six.moves import range

import cgtwq
from cgtwq.helper.qt import ask_login
from cgtwq.helper.wlf import CGTWQHelper
from wlf.env import has_nuke
from wlf.files import copy, is_same
from wlf.notify import CancelledError, progress
from wlf.path import PurePath

from .exceptions import DatabaseError
from .model import (ROLE_CHECKABLE, ROLE_DEST, DirectoryModel,
                    VersionFilterProxyModel)
from .util import LOGGER
from collections import namedtuple

LOGGER = logging.getLogger(__name__)


class UploadTask(
    namedtuple('UploadTask',
               ('label', 'src',
                'dst', 'is_submit', 'pipeline',
                'submit_note'))):
    def __str__(self):
        return self.label


class Controller(QObject):
    """Controller for uploader.  """

    root_changed = Signal(str)
    upload_finished = Signal()
    upload_started = Signal()
    pipeline = '合成'
    burnin_folder = 'burn-in'
    default_widget = None

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
        self.is_updating = False

        self.model.layoutChanged.connect(self.update_model)
        self.upload_finished.connect(self.update_model)

    def change_pipeline(self, value):
        """Change target pipline.  """
        self.pipeline = value
        self.update_model()

    def change_root(self, value):
        """Change uploader root.  """

        if isinstance(value, QModelIndex):
            if not self.model.is_dir(value):
                return
            data = self.model.file_path(value)
            value = self.model.absolute_path(data)

        value = os.path.normpath(value)
        self.model.sourceModel().setRootPath(value)
        LOGGER.debug('Change root: %s', value)
        self.root_changed.emit(value)

    def open_index(self, index, is_use_burnin=True):
        """Open item in browser

        Args:
            index (Qt.QtCore.QModelIndex): Item index.
            is_use_burnin (bool, optional): Defaults to True.
                If use the burn-in version.
        """

        data = self.model.data(index)
        filename = self.model.absolute_path(data)
        burn_in_path = self.model.absolute_path(self.burnin_folder, data)

        webbrowser.open(burn_in_path
                        if is_use_burnin and os.path.exists(burn_in_path)
                        else filename)

    def source_index(self, path):
        """Get source model index from path.

        Args:
            path (str): Path data.

        Returns:
            Qt.QtCore.ModelIndex: Index in source model.
        """

        model = self.model
        source_model = model.sourceModel()
        return model.mapFromSource(source_model.index(path))

    def update_model(self):
        """Update directory model.  """
        if self.is_updating:
            return

        self.is_updating = True
        try:
            self._update_model()
        finally:
            self.is_updating = False

    def _update_model(self):
        model = self.model
        root_index = model.root_index()
        if cgtwq.DesktopClient.is_logged_in():
            cgtwq.update_setting()
            current_id = cgtwq.current_account_id()
        elif not cgtwq.server.setting.DEFAULT_TOKEN:
            account_info = ask_login(self.default_widget)
            cgtwq.server.setting.DEFAULT_TOKEN = account_info.token
            current_id = account_info.account_id
        else:
            current_id = cgtwq.get_account_id(
                cgtwq.server.setting.DEFAULT_TOKEN)

        def _do(i):
            index = model.index(i, 0, root_index)
            if self.model.is_dir(index):
                model.setData(index, False, ROLE_CHECKABLE)
                model.setData(index, Qt.Unchecked, Qt.CheckStateRole)
                return
            data = model.data(index)
            filename = self.model.absolute_path(data)

            def _on_error(reason):
                model.setData(index, reason, Qt.StatusTipRole)
                model.setData(index, Qt.Unchecked, Qt.CheckStateRole)
                model.setData(index,
                              self.brushes['error'],
                              Qt.ForegroundRole)

            try:
                try:
                    entry = CGTWQHelper.get_entry(data, self.pipeline)
                except DatabaseError:
                    _on_error('找不到对应数据库')
                    return
                except ValueError as ex:
                    if ex.args[0] == 'Empty selection.':
                        _on_error('找不到对应任务')
                        return
                    raise
                assert isinstance(entry, cgtwq.Entry), type(entry)
                shot = PurePath(data).shot
                dest = (model.data(index, ROLE_DEST)
                        or (PurePath(entry.filebox.get_submit().path) /
                            PurePath(shot).with_suffix(PurePath(data).suffix)).as_posix())

                # Set dest.
                model.setData(index, dest, ROLE_DEST)

                # Set tooltip.
                model.setData(index,
                              '<br>'.join([
                                  '数据库: {0}'.format(
                                      entry.module.database.name),
                                  '镜头: {0}'.format(shot),
                                  '目的地: {0}'.format(dest)
                              ]),
                              Qt.ToolTipRole)

                # Set statustip.
                is_ok = False
                is_uploaded = is_same(filename, dest)
                if current_id in entry['account_id'].split(','):
                    is_ok = True
                    model.setData(
                        index, '已上传' if is_uploaded else '等待上传', Qt.StatusTipRole)
                else:
                    assigned = entry['artist']
                    _on_error(
                        '此任务已分配给:{0}'.format(assigned)
                        if assigned else '任务未分配'
                    )

                # Set check state.
                model.setData(index, is_ok, ROLE_CHECKABLE)
                if not is_ok or is_uploaded:
                    model.setData(index, Qt.Unchecked, Qt.CheckStateRole)

                # Set color.
                if is_ok:
                    model.setData(index,
                                  self.brushes['uploaded']
                                  if is_uploaded
                                  else self.brushes['local'],
                                  Qt.ForegroundRole)
                else:
                    model.setData(index,
                                  self.brushes['error'],
                                  Qt.ForegroundRole)

                return data
            except:  # pylint: disable=bare-except
                logging.error(
                    'Unexpect error during access database.', exc_info=True)
                return '<出错>'

        pool = Pool()
        count = model.rowCount(model.root_index())
        try:
            for _ in progress(
                    pool.imap_unordered(_do, range(count)),
                    name='访问数据库',
                    total=count,
                    parent=self.parent()):
                pass
        except CancelledError:
            LOGGER.info('用户取消')

    def upload(self, is_submit=True, submit_note=''):
        """Upload videos to server.  """

        def _do(i):
            assert isinstance(i, UploadTask)
            copy(i.src, i.dst)
            entry = CGTWQHelper.get_entry(PurePath(i.src).name, i.pipeline)
            assert isinstance(entry, cgtwq.Entry)
            # Submit
            if i.is_submit:
                entry.submit([i.dst], [i.dst], note=i.submit_note)
            # Set image
            mime, _ = mimetypes.guess_type(i.dst)
            if mime and mime.startswith('image'):
                entry.set_image(i.dst)
            return i.label

        pool = Pool()
        tasks = self.tasks(is_submit, submit_note)
        self.upload_started.emit()
        try:
            for i in progress(
                    tasks,
                    name='上传',
                    parent=self.parent()):
                result = pool.apply_async(_do, (i,))
                while not result.ready():
                    QCoreApplication.processEvents()
                if not result.successful():
                    break
        except CancelledError:
            LOGGER.info('用户取消')
        self.upload_finished.emit()

    def tasks(self, is_submit=True, submit_note=''):
        """Get task list from model.
            is_submit (bool, optional): Defaults to True. Task attribute
            submit_note (str, optional): Defaults to ''. Task attribute

        Returns:
            list[UploadTask]: Tasks list.
        """

        model = self.model
        root_index = model.root_index()
        count = model.rowCount(root_index)

        ret = []
        for i in range(count):
            index = model.index(i, 0, root_index)
            if model.data(index, Qt.CheckStateRole):
                label = model.data(index, Qt.DisplayRole)
                src = model.file_path(index)
                dst = model.data(index, ROLE_DEST)
                task = UploadTask(label, src, dst, is_submit,
                                  self.pipeline, submit_note)
                ret.append(task)
        return ret

    def reverse_selection(self):
        """Reverse current selection.  """

        model = self.model
        for i in model.indexes():
            state = model.data(i, Qt.CheckStateRole)
            if model.data(i, Qt.ForegroundRole) == self.brushes['local']:
                model.setData(i, Qt.Unchecked
                              if state else Qt.Checked,
                              Qt.CheckStateRole)
            else:
                model.setData(i, Qt.Unchecked,
                              Qt.CheckStateRole)

    def select_all(self):
        """Select all local item.  """

        model = self.model
        for i in model.indexes():
            if model.data(i, Qt.ForegroundRole) == self.brushes['local']:
                model.setData(i, Qt.Checked, Qt.CheckStateRole)
            else:
                model.setData(i, Qt.Unchecked,
                              Qt.CheckStateRole)
