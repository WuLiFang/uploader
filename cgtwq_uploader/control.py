# -*- coding=UTF-8 -*-
"""Uploader control.  """
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging
import mimetypes
import os
import webbrowser
from collections import namedtuple
from multiprocessing.dummy import Pool

from Qt.QtCore import QCoreApplication, QModelIndex, QObject, Qt, Signal
from Qt.QtGui import QBrush, QColor
from six.moves import range

import cgtwq
from cgtwq.helper.qt import ask_login
from cgtwq.helper.wlf import DatabaseError, get_entry_by_file
from wlf.env import has_nuke
from wlf.fileutil import copy, is_same
from wlf.mimetools import is_mimetype
from wlf.path import PurePath
from wlf.progress import CancelledError, progress

from .model import (ROLE_CHECKABLE, ROLE_DEST, DirectoryModel,
                    VersionFilterProxyModel)
from .util import LOGGER

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
                   'error': QBrush(Qt.red),
                   'warning': QBrush(QColor(255, 200, 90))}
    else:
        brushes = {'local': QBrush(Qt.black),
                   'uploaded': QBrush(Qt.gray),
                   'error': QBrush(Qt.red),
                   'warning': QBrush(QColor(200, 100, 50))}
    pipeline_filetypes = {
        '灯光': 'image',
        '渲染': 'video',
        '合成': 'image',
        '输出': 'video'
    }
    pipeline_ext = {
        '场景细化': ('.ma', '.mb', '.jpg', '.png'),
        '绘景': ('.psd', '.png', '.tif', '.tga', '.jpg', 'exr'),
        '监修': ('.psg', '.ma', '.mb', '.jpg', '.png'),
        '数码作画': ('.tga', '.exr', '.png', '.tif', '.jpg', '.nk'),
        '手绘特效': ('.jpg', '.png', '.psd', '.mov', '.mp4', '.gif'),
        '预合成': ('.nk', '.mov', '.mp4')
    }

    def __init__(self, parent=None):
        super(Controller, self).__init__(parent)
        model = DirectoryModel(self)
        proxy_model = VersionFilterProxyModel(self)
        proxy_model.setSourceModel(model)
        self.model = proxy_model
        self.is_updating = False
        self.current_id = None

        self.model.layoutChanged.connect(self.update_model)
        self.upload_finished.connect(self.update_model)

    def change_pipeline(self, value):
        """Change target pipline.  """

        self.pipeline = value
        self.model.sourceModel().columns[ROLE_DEST].clear()
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

    def _ask_login(self):
        account_info = ask_login(self.default_widget)
        cgtwq.core.CONFIG['DEFAULT_TOKEN'] = account_info.token
        return account_info

    def update_model(self):
        """Update directory model.  """
        if self.is_updating:
            return

        self.is_updating = True
        try:
            self._update_model()
        except cgtwq.LoginError:
            self._ask_login()
        finally:
            self.is_updating = False

    def _update_model(self):
        self._update_current_id()

        pool = Pool()
        count = self.model.rowCount(self.model.root_index())
        try:
            for _ in progress(
                    pool.imap_unordered(self._update_model_item, range(count)),
                    name='访问数据库',
                    total=count,
                    parent=self.parent()):
                pass
        except CancelledError:
            LOGGER.info('用户取消')

    def _update_current_id(self):
        client = cgtwq.DesktopClient()
        if client.is_logged_in():
            client.connect()

        if not cgtwq.core.CONFIG['DEFAULT_TOKEN']:
            current_id = self._ask_login().account_id
        else:
            current_id = cgtwq.get_account_id()

        self.current_id = current_id

    def _update_model_item(self, i):
        model = self.model
        root_index = model.root_index()
        index = model.index(i, 0, root_index)
        if model.is_dir(index):
            model.setData(index, False, ROLE_CHECKABLE)
            model.setData(index, Qt.Unchecked, Qt.CheckStateRole)
            return
        data = model.data(index)
        filename = model.absolute_path(data)

        def _on_error(reason):
            model.setData(index, reason, Qt.StatusTipRole)
            model.setData(index, Qt.Unchecked, Qt.CheckStateRole)
            model.setData(index,
                          self.brushes['error'],
                          Qt.ForegroundRole)

        try:
            try:
                entry = get_entry_by_file(data, self.pipeline)
            except DatabaseError:
                _on_error('找不到对应数据库')
                return
            except ValueError as ex:
                if ex.args[0] == 'Empty selection.':
                    _on_error('找不到对应任务')
                    return
                raise
            assert isinstance(entry, cgtwq.Entry), type(entry)
            ext = PurePath(data).suffix.lower()

            # Check extionsion
            limited_ext = self.pipeline_ext.get(self.pipeline)
            if limited_ext and not ext in limited_ext:
                _on_error('此文件扩展名不是 {0}'.format(limited_ext))
                return

            shot = PurePath(data).shot
            dest = (model.data(index, ROLE_DEST)
                    or (PurePath(entry.filebox.get_submit().path) /
                        PurePath(shot).with_suffix(ext)).as_posix())
            # Check mimetype
            limited_filetype = self.pipeline_filetypes.get(self.pipeline)
            if limited_filetype and not is_mimetype(data, limited_filetype):
                _on_error('此文件类型不是 {0}'.format(limited_filetype))
                return

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
            is_warning = False
            is_uploaded = is_same(filename, dest)
            account_id = entry['account_id']
            if not account_id:
                is_ok = True
                is_warning = True
                model.setData(
                    index,
                    '*注意*: 此任务尚未分配',
                    Qt.StatusTipRole)
            elif self.current_id in account_id.split(','):
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
            if is_uploaded:
                model.setData(index,
                              self.brushes['uploaded'],
                              Qt.ForegroundRole)
            elif is_warning:
                model.setData(index,
                              self.brushes['warning'],
                              Qt.ForegroundRole)
            elif is_ok:
                model.setData(index,
                              self.brushes['local'],
                              Qt.ForegroundRole)
            else:
                model.setData(index,
                              self.brushes['error'],
                              Qt.ForegroundRole)

            return data
        except:  # pylint: disable=bare-except
            logging.error(
                'Unexpected error during access database.', exc_info=True)
            return '<出错>'

    def upload(self, is_submit=True, submit_note=''):
        """Upload videos to server.  """

        def _do(i):
            assert isinstance(i, UploadTask)
            copy(i.src, i.dst)
            entry = get_entry_by_file(PurePath(i.src).name, i.pipeline)
            assert isinstance(entry, cgtwq.Entry)

            message = cgtwq.Message(i.submit_note)
            # Set image
            mime, _ = mimetypes.guess_type(i.dst)
            is_image = mime and mime.startswith('image')
            if is_image:
                image = entry.set_image(i.dst)
                message.images.append(image)
            # Submit
            if i.is_submit:
                entry.flow.submit([i.dst], message=message)
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
