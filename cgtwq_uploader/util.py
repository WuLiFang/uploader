# -*- coding=UTF-8 -*-
"""Utility for uploader.  """
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging
import os
import cgtwq
from wlf.config import Config as _Config


class Config(_Config):
    """A disk config can be manipulated like a dict."""

    default = {
        'DIR': 'E:/',
        'SERVER': 'Z:\\',
        'PROJECT': 'SNJYW',
        'FOLDER': 'Comp\\mov',
        'PIPELINE': '合成',
        'EPISODE': '',
        'SCENE': '',
        'MODE': 1,
        'IS_SUBMIT': 2,
        'IS_BURN_IN': 2
    }
    path = os.path.expanduser('~/.wlf.uploader.json')


CONFIG = Config()

LOGGER = logging.getLogger('com.wlf.uploader')


def l10n(obj):
    """Localization.  """

    ret = obj
    if isinstance(ret, cgtwq.LoginError):
        ret = '需要登录CGTeamWork'
    elif isinstance(ret, cgtwq.AccountError):
        ret = '已被分配给: {}\n当前用户: {}'.format(
            ret.owner or u'<未分配>', ret.current)
    elif isinstance(ret, cgtwq.IDError):
        ret = 'CGTW上未找到对应镜头'

    return unicode(ret)
