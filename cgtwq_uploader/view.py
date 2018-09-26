# -*- coding=UTF-8 -*-
"""Upload files to server.  """
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import webbrowser

from Qt.QtCore import QEvent, Qt, Signal
from Qt.QtWidgets import QStyle

from wlf.uitools.template.dialog_with_dir import DialogWithDir

from . import filetools
from .__about__ import __version__
from .control import Controller
from .util import CONFIG


class Dialog(DialogWithDir):
    """Main GUI dialog.  """

    instance = None
    upload_finished = Signal()
    icons = {
        'toolButtonOpenDir': QStyle.SP_DirOpenIcon,
        'dirButton': QStyle.SP_DialogOpenButton,
        'syncButton': QStyle.SP_FileDialogToParent,
        None: QStyle.SP_FileDialogToParent,
    }
    uifile = filetools.path('dialog.ui')

    def __init__(self, parent=None):

        DialogWithDir.__init__(self, config=CONFIG, parent=parent)
        self.is_uploading = False
        self.version_label.setText('v{}'.format(__version__))

        # Set controller
        self.controller = Controller(self)
        self.controller.widget = self
        self.listView.setModel(self.controller.model)

        # Signals
        self.dirEdit.textChanged.connect(self.controller.change_root)
        self.listView.clicked.connect(self.on_view_item_clicked)
        self.listView.doubleClicked.connect(self.on_view_item_double_clicked)

        self.comboBoxPipeline.currentIndexChanged.connect(
            lambda index: self.on_pipeline_changed(self.comboBoxPipeline.itemText(index)))

        self.actionDir.triggered.connect(self.ask_dir)
        self.actionSync.triggered.connect(self.on_action_sync)
        self.actionSelectAll.triggered.connect(
            self.controller.select_all)
        self.actionReverseSelection.triggered.connect(
            self.controller.reverse_selection)
        self.actionReset.triggered.connect(
            self.controller.update_model)
        self.actionOpenDir.triggered.connect(
            lambda: webbrowser.open(CONFIG['DIR']))

        self.controller.root_changed.connect(self.on_root_changed)
        self.controller.upload_started.connect(self.on_upload_started)
        self.controller.upload_finished.connect(self.on_upload_finished)
        self.controller.model.dataChanged.connect(self.on_data_changed)

        # Recover state.
        self.controller.pipeline = CONFIG['PIPELINE']
        self.controller.change_root(self.directory)

    def on_action_sync(self):
        self.controller.upload(
            self.checkBoxSubmit.checkState(),
            self.lineEditNote.text())
        self.lineEditNote.clear()

    def _edits_key(self):
        return {
            'dirEdit': 'DIR',
            'checkBoxSubmit': 'IS_SUBMIT',
            'checkBoxBurnIn': 'IS_BURN_IN',
            'comboBoxPipeline': 'PIPELINE',
        }

    @property
    def dir_edit(self):
        """Line edit for dir input.  """

        return self.dirEdit

    def on_root_changed(self, value):
        self.directory = value
        self.listView.setRootIndex(self.controller.source_index(value))

    def on_view_item_clicked(self, index):
        pass

    def on_view_item_double_clicked(self, index):
        if self.controller.model.is_dir(index):
            self.controller.change_root(index)
        else:
            self.controller.open_index(index, self.checkBoxBurnIn.checkState())

    def on_pipeline_changed(self, pipeline):
        self.controller.change_pipeline(pipeline)

    def on_data_changed(self):
        model = self.controller.model
        states = [model.data(i, Qt.CheckStateRole) for i in model.indexes()]
        checked_count = len([i for i in states if i == Qt.Checked])
        total_count = len(states)
        self.labelCount.setText('{}/{}'.format(checked_count, total_count))
        self.syncButton.setEnabled(not self.is_uploading and checked_count)

    def on_upload_started(self):
        self.is_uploading = True
        self.syncButton.setEnabled(False)

    def on_upload_finished(self):
        self.is_uploading = False
        self.activateWindow()

    def event(self, event):
        """Override.  """

        if event.type() == QEvent.StatusTip:
            self.statusBar.showMessage(event.tip())
        return super(Dialog, self).event(event)
