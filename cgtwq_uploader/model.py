# -*- coding=UTF-8 -*-
"""Data models for uploader.  """

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from Qt.QtCore import QDir, QPersistentModelIndex, QSortFilterProxyModel, Qt
from Qt.QtWidgets import QFileSystemModel
from six.moves import range

from wlf.files import version_filter

ROLE_DEST = Qt.UserRole + 1
ROLE_CHECKABLE = Qt.UserRole + 2


class DirectoryModel(QFileSystemModel):
    """Checkable fileSystem model.  """

    def __init__(self, parent=None):
        super(DirectoryModel, self).__init__(parent)
        self.setFilter(QDir.NoDotAndDotDot | QDir.Files)
        self.columns = {
            Qt.CheckStateRole: {},
            Qt.ToolTipRole: {},
            Qt.StatusTipRole: {},
            Qt.ForegroundRole: {},
            ROLE_DEST: {},
            ROLE_CHECKABLE: {}
        }

    def data(self, index, role=Qt.DisplayRole):
        """Override.  """

        pindex = QPersistentModelIndex(index)
        if role in self.columns:
            default = {Qt.CheckStateRole: Qt.Checked}.get(role)
            return self.columns[role].get(pindex, default)
        return super(DirectoryModel, self).data(index, role)

    def flags(self, index):
        """Override.  """

        ret = super(DirectoryModel, self).flags(index)
        if self.data(index, ROLE_CHECKABLE):
            ret |= Qt.ItemIsUserCheckable
        return ret

    def setData(self, index, value, role=Qt.EditRole):
        """Override.  """
        # pylint: disable=invalid-name

        pindex = QPersistentModelIndex(index)
        if role in self.columns:
            self.columns[role][pindex] = value
            self.dataChanged.emit(index, index)
            return True
        return super(DirectoryModel, self).setData(index, value, role)

    def all_file(self):
        """All files under root.  """

        root_index = self.index(self.rootPath())
        return [self.data(self.index(i, 0, root_index)) for i in range(self.rowCount(root_index))]


class VersionFilterProxyModel(QSortFilterProxyModel):
    """Filter data by version.  """

    def filterAcceptsRow(self, source_row, source_parent):
        """Override.  """
        # pylint: disable=invalid-name

        model = self.sourceModel()
        assert isinstance(model, DirectoryModel)

        data = model.data(model.index(source_row, 0, source_parent))
        all_file = model.all_file()
        return data not in all_file or data in version_filter(all_file)

    def all_files(self):
        """All files in display.  """

        root_index = self.root_index()
        count = self.rowCount(root_index)
        return [self.data(self.index(i, 0, root_index)) for i in range(count)]

    def checked_files(self):
        """All checked files.  """

        root_index = self.root_index()
        count = self.rowCount(root_index)
        ret = []
        for i in range(count):
            index = self.index(i, 0, root_index)
            if self.data(index, Qt.CheckStateRole):
                data = self.data(index)
                ret.append(data)
        return ret

    def root_index(self):
        """Index of root path.  """

        model = self.sourceModel()
        return self.mapFromSource(model.index(model.rootPath()))
