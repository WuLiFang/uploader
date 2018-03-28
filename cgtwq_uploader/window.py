# -*- coding=UTF-8 -*-
"""Upload files to server.  """
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import webbrowser

from Qt.QtCore import Qt, QTimer, Signal, Slot
from Qt.QtGui import QBrush, QColor
from Qt.QtWidgets import QFileDialog, QListWidgetItem, QStyle

from .__about__ import __version__
import cgtwq
from wlf.decorators import run_async
from wlf.files import copy
from wlf.notify import HAS_NUKE, CancelledError, progress
from wlf.path import Path, PurePath, get_unicode
from wlf.uitools import DialogWithDir
from .util import CONFIG, LOGGER, l10n
from .control import ShotsFileDirectory
from . import filetools


class Dialog(DialogWithDir):
    """Main GUI dialog.  """

    default_note = '自上传工具提交'
    instance = None
    upload_finished = Signal()

    def __init__(self, parent=None):

        edits_key = {
            'serverEdit': 'SERVER',
            'folderEdit': 'FOLDER',
            'dirEdit': 'DIR',
            'projectEdit': 'PROJECT',
            'epEdit': 'EPISODE',
            'scEdit': 'SCENE',
            'tabWidget': 'MODE',
            'checkBoxSubmit': 'IS_SUBMIT',
            'checkBoxBurnIn': 'IS_BURN_IN',
            'comboBoxPipeline': 'PIPELINE',
        }
        icons = {
            'toolButtonOpenDir': QStyle.SP_DirOpenIcon,
            'toolButtonOpenServer': QStyle.SP_DirOpenIcon,
            'dirButton': QStyle.SP_DialogOpenButton,
            'serverButton': QStyle.SP_DialogOpenButton,
            'syncButton': QStyle.SP_FileDialogToParent,
            None: QStyle.SP_FileDialogToParent,
        }
        DialogWithDir.__init__(
            self,
            filetools.path('window.ui'),
            config=CONFIG,
            icons=icons,
            parent=parent,
            edits_key=edits_key,
            dir_edit='dirEdit')
        self.version_label.setText('v{}'.format(__version__))
        self.lineEditNote.setPlaceholderText(self.default_note)
        self.file_list_widget = FileListWidget(self.listWidget)

        # Update timer
        self.update_timer = QTimer()
        self.update_timer.setInterval(100)
        self.update_timer.timeout.connect(self.update_ui)

        # Signals
        self.actionDir.triggered.connect(self.ask_dir)
        self.actionSync.triggered.connect(self.upload)
        self.actionServer.triggered.connect(self.ask_server)
        self.actionOpenDir.triggered.connect(
            lambda: webbrowser.open(CONFIG['DIR']))
        self.actionOpenServer.triggered.connect(
            lambda: webbrowser.open(CONFIG['SERVER']))
        self.upload_finished.connect(self.activateWindow)

    def showEvent(self, event):
        LOGGER.debug('Uploader show event triggered.')
        event.accept()
        if HAS_NUKE:
            mov_path = __import__('node').Last.mov_path
            if mov_path:
                self.directory = get_unicode(os.path.dirname(mov_path))
        self.update_timer.start()
        self.file_list_widget.showEvent(event)

    def hideEvent(self, event):
        LOGGER.debug('Uploader hide event triggered.')
        event.accept()
        self.update_timer.stop()
        self.file_list_widget.hideEvent(event)

    def update_ui(self):
        """Update dialog UI content.  """

        mode = self.mode
        sync_button_enable = any(self.file_list_widget.checked_files)
        sync_button_text = u'上传至CGTeamWork'
        if mode == 0:
            sync_button_enable &= Path(Path(self.dest_folder).parent).is_dir()
            sync_button_text = u'上传至: {}'.format(self.dest_folder)

        self.syncButton.setText(sync_button_text)
        self.syncButton.setEnabled(sync_button_enable)

    def upload(self):
        """Upload videos to server.  """

        files = list(self.checked_files)
        directory = self.file_list_widget.directory

        @run_async
        def _run():
            code_dict = {i[0]: i[1] for i
                         in cgtwq.PROJECT.all().get_fields('code', 'database')}

            def _get_database(filename):
                for k, v in code_dict.items():
                    if PurePath(filename).name.startswith(k):
                        return v
                raise ValueError('Can not match file to databse.')

            try:
                for i in progress(files, '上传', parent=self):
                    src = os.path.join(self.directory, i)
                    dst = directory.get_dest(i)
                    shot_name = PurePath(dst).shot
                    if isinstance(dst, Exception):
                        self.error(u'{}\n-> {}'.format(i, dst))
                        continue
                    copy(src, dst)
                    if self.mode == 1:
                        select = cgtwq.Database(_get_database(shot_name))['shot_task'].filter(
                            (cgtwq.Field('shot.shot') == shot_name)
                            & (cgtwq.Field('pipeline') == self.pipeline)
                        )
                        entry = select.to_entry()
                        if src.lower().endswith(('.jpg', '.png', '.jpeg')):
                            entry.set_image(dst)
                        if self.is_submit:
                            note = self.lineEditNote.text() or self.default_note
                            entry.submit([dst], note=note)

            except CancelledError:
                LOGGER.info('用户取消上传')
            self.upload_finished.emit()

        _run()

    def ask_server(self):
        """Show a dialog ask user config['SERVER'].  """

        file_dialog = QFileDialog()
        dir_ = file_dialog.getExistingDirectory(
            dir_=os.path.dirname(CONFIG['SERVER'])
        )
        if dir_:
            self.serverEdit.setText(dir_)

    @property
    def dest_folder(self):
        """File upload folder destination.  """

        ret = os.path.join(
            self.server,
            self.project,
            self.folderEdit.text(),
            self.epEdit.text(),
            self.scEdit.text()
        )
        ret = os.path.normpath(ret)
        return ret

    @property
    def pipeline(self):
        """Current working pipeline.  """

        return self.comboBoxPipeline.currentText()

    @property
    def mode(self):
        """Upload mode. """

        return self.tabWidget.currentIndex()

    @property
    def server(self):
        """Current server path.  """

        return self.serverEdit.text()

    @property
    def project(self):
        """Current working dir.  """

        return self.projectEdit.text()

    @property
    def is_submit(self):
        """Submit when upload or not.  """

        return self.checkBoxSubmit.checkState()

    @property
    def checked_files(self):
        """Return files checked in listwidget.  """

        return self.file_list_widget.checked_files


class FileListWidget(object):
    """Folder viewer.  """

    if HAS_NUKE:
        brushes = {'local': QBrush(QColor(200, 200, 200)),
                   'uploaded': QBrush(QColor(100, 100, 100)),
                   'error': QBrush(Qt.red)}
    else:
        brushes = {'local': QBrush(Qt.black),
                   'uploaded': QBrush(Qt.gray),
                   'error': QBrush(Qt.red)}
    directory = None
    burnin_folder = 'burn-in'
    updating = False

    def __init__(self, list_widget):

        self.widget = list_widget
        parent = self.widget.parent()
        assert isinstance(parent, Dialog)
        self.parent = parent

        # Connect signal
        self.widget.itemDoubleClicked.connect(self.open_file)
        self.widget.itemChanged.connect(self.update_widget)
        self.parent.actionSelectAll.triggered.connect(self.select_all)
        self.parent.actionReverseSelection.triggered.connect(
            self.reverse_selection)
        self.parent.actionReset.triggered.connect(
            self.update_directory)

        # Event override
        self.widget.showEvent = self.showEvent
        self.widget.hideEvent = self.hideEvent

    def update_directory(self):
        """Update current working dir.  """

        if self.directory and self.directory.updating:
            return

        mode = self.parent.mode
        kwargs = {}
        if mode == 0:
            parent = self.parent
            assert isinstance(parent, Dialog)
            kwargs = {'dest': self.parent.dest_folder}

        directory = ShotsFileDirectory(
            self.parent.directory, self.parent.pipeline, parent=self.parent, **kwargs)
        directory.changed.connect(self.update_widget)
        directory.update_timer.start()

        if self.directory:
            self.directory.update_timer.stop()
            self.directory.deleteLater()
        self.directory = directory
        self.directory.changed.emit()

    def showEvent(self, event):
        event.accept()
        self.update_directory()

    def hideEvent(self, event):

        event.accept()
        if self.directory:
            self.directory.update_timer.stop()

    def update_widget(self):
        """Update widget.  """

        if self.updating:
            return

        self.updating = True

        widget = self.widget
        parent = self.parent
        brushes = self.brushes
        directory = self.directory
        assert isinstance(parent, Dialog)

        local_files = directory.files
        uploaded_files = directory.uploaded
        unexpected_files = directory.unexpected

        for item in self.items():
            text = item.text()
            # Remove.
            if text not in local_files:
                widget.takeItem(widget.indexFromItem(item).row())
            # Uncheck.
            elif item.checkState() \
                    and isinstance(self.directory.get_dest(text), Exception):
                item.setCheckState(Qt.Unchecked)

        for i in local_files:
            # Add.
            try:
                item = widget.findItems(
                    i, Qt.MatchExactly)[0]
            except IndexError:
                item = QListWidgetItem(i, widget)
                item.setCheckState(Qt.Unchecked)
            # Set style.
            dest = self.directory.get_dest(i)
            if i in uploaded_files:
                item.setFlags(Qt.ItemIsEnabled)
                item.setForeground(brushes['uploaded'])
                item.setCheckState(Qt.Unchecked)
                tooltip = '已上传至: {}'.format(dest)
            elif i in unexpected_files:
                item.setFlags(Qt.ItemIsUserCheckable |
                              Qt.ItemIsEnabled)
                item.setForeground(brushes['error'])
                tooltip = l10n(dest)
            else:
                item.setFlags(Qt.ItemIsUserCheckable |
                              Qt.ItemIsEnabled)
                item.setForeground(brushes['local'])
                tooltip = '将上传至: {}'.format(dest)
            item.setToolTip(tooltip)

        widget.sortItems()

        parent.labelCount.setText(
            '{}/{}/{}'.format(
                len(list(self.checked_files)),
                len(local_files) - len(self.directory.uploaded),
                len(local_files)))

        self.updating = False

    @property
    def checked_files(self):
        """Return files checked in listwidget.  """

        return (i.text() for i in self.items() if i.checkState())

    @property
    def is_use_burnin(self):
        """Use burn-in version when preview.  """

        return self.parent.checkBoxBurnIn.checkState()

    @Slot(QListWidgetItem)
    def open_file(self, item):
        """Open mov file for preview.  """

        filename = item.text()
        path = os.path.join(self.directory.path, filename)
        burn_in_path = os.path.join(
            self.directory.path, self.burnin_folder, filename)

        webbrowser.open(burn_in_path
                        if self.is_use_burnin and os.path.exists(burn_in_path)
                        else path)

    def items(self):
        """Item in list widget -> list."""

        widget = self.widget
        return list(widget.item(i) for i in xrange(widget.count()))

    def select_all(self):
        """Select all item in list widget.  """

        uploaded = self.directory.uploaded
        unexpected = self.directory.unexpected

        files = [i for i in self.directory.files if i not in uploaded.union(
            unexpected)]
        refresh = False
        if not files:
            files = [
                i for i in self.directory.files if i not in uploaded]
            refresh = True

        if not files:
            return

        for item in self.items():
            if item.text() in files:
                item.setCheckState(Qt.Checked)
        if refresh:
            self.update_directory()

    def reverse_selection(self):
        """Select all item in list widget.  """

        for item in self.items():
            if item.text() not in self.directory.uploaded:
                if item.checkState():
                    item.setCheckState(Qt.Unchecked)
                else:
                    item.setCheckState(Qt.Checked)
