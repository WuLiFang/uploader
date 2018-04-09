# -*- coding=UTF-8 -*-
"""Main entry for uploader.  """

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import cgtwq
from wlf.uitools import main_show_dialog
from wlf import mp_logging

from .view import Dialog


def main():
    mp_logging.basic_config()
    cgtwq.update_setting()
    main_show_dialog(Dialog)


if __name__ == '__main__':
    main()
