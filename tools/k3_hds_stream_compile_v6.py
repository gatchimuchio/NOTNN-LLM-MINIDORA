#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import k3_hds_stream_compile as base
from k3_hds_semantics_v6 import install

install(base)

if __name__ == '__main__':
    raise SystemExit(base.main())
