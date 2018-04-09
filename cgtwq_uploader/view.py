# -*- coding=UTF-8 -*-
"""Upload files to server.  """
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import webbrowser

from Qt.QtCore import QEvent, Qt, Signal
from Qt.QtWidgets import QStyle

from wlf.uitools import DialogWithDir

from . import filetools
from .__about__ import __version__
from .control import Controller
from .util import CONFIG


class Dialog(DialogWithDir):
    """Main GUI dialog.  """

    default_note = '自上传工具提交'
    instance = None
    upload_finished = Signal()

    def __init__(self, parent=None):

        edits_key = {
            'dirEdit': 'DIR',
            'checkBoxSubmit': 'IS_SUBMIT',
            'checkBoxBurnIn': 'IS_BURN_IN',
            'comboBoxPipeline': 'PIPELINE',
        }
        icons = {
            'toolButtonOpenDir': QStyle.SP_DirOpenIcon,
            'dirButton': QStyle.SP_DialogOpenButton,
            'syncButton': QStyle.SP_FileDialogToParent,
            None: QStyle.SP_FileDialogToParent,
        }
        DialogWithDir.__init__(
            self,
            filetools.path('dialog.ui'),
            config=CONFIG,
            icons=icons,
            parent=parent,
            edits_key=edits_key,
            dir_edit='dirEdit')
        self.version_label.setText('v{}'.format(__version__))
        self.lineEditNote.setPlaceholderText(self.default_note)

        # Set controller
        self.controller = Controller(self)
        self.listView.setModel(self.controller.model)

        # Signals
        self.dirEdit.textChanged.connect(self.controller.change_root)
        self.listView.clicked.connect(self.on_view_item_clicked)
        self.listView.doubleClicked.connect(self.on_view_item_double_clicked)

        self.comboBoxPipeline.currentIndexChanged.connect(
            lambda index: self.on_pipeline_changed(self.comboBoxPipeline.itemText(index)))

        self.actionDir.triggered.connect(self.ask_dir)
        self.actionSync.triggered.connect(
            lambda: self.controller.upload(
                self.checkBoxSubmit.checkState(),
                self.lineEditNote.text()
            )
        )
        self.actionSelectAll.triggered.connect(
            self.controller.select_all)
        self.actionReverseSelection.triggered.connect(
            self.controller.reverse_selection)
        self.actionReset.triggered.connect(
            self.controller.update_model)
        self.actionOpenDir.triggered.connect(
            lambda: webbrowser.open(CONFIG['DIR']))

        self.controller.root_changed.connect(self.on_root_changed)
        self.controller.upload_finished.connect(self.activateWindow)
        self.controller.model.dataChanged.connect(self.on_data_changed)

        # Recover state.
        self.controller.pipeline = CONFIG['PIPELINE']
        self.controller.change_root(self.directory)

    def on_root_changed(self, value):
        self.dirEdit.setText(value)
        self.listView.setRootIndex(self.controller.source_index(value))

    def on_view_item_clicked(self, index):
        self.controller.change_root(index)

    def on_view_item_double_clicked(self, index):
        self.controller.open_index(index, self.checkBoxBurnIn.checkState())

    def on_pipeline_changed(self, pipeline):
        self.controller.change_pipeline(pipeline)

    def on_data_changed(self):
        model = self.controller.model
        states = [model.data(i, Qt.CheckStateRole) for i in model.indexes()]
        checked_count = len([i for i in states if i == Qt.Checked])
        total_count = len(states)
        self.labelCount.setText('{}/{}'.format(checked_count, total_count))
        self.syncButton.setEnabled(checked_count)

    def event(self, event):
        """Override.  """

        if event.type() == QEvent.StatusTip:
            self.statusBar.showMessage(event.tip())
        return super(Dialog, self).event(event)
