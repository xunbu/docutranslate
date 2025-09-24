# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import os

from .conditional_import import available_packages, conditional_import

USE_PROXY = True if (os.getenv("DOCUTRANSLATE_PROXY_ENABLED") and os.getenv(
    "DOCUTRANSLATE_PROXY_ENABLED").lower() == "true") else False
if USE_PROXY:
    print(f"USE_PROXY:{USE_PROXY}")