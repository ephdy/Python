# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

# ================= !!! 请替换这个路径 !!! =================
# ipopt.exe 的完整路径
ipopt_exe_path = r'D:\tool\miniconda3\envs\IPOPT\Library\bin\ipopt.exe'
# =========================================================

# 彻底收集 pyomo 的所有内容 (包括子模块、数据文件、二进制文件)
pyomo_datas, pyomo_binaries, pyomo_hiddenimports = collect_all('pyomo')

# 彻底收集 cyipopt 的所有内容
cyipopt_datas, cyipopt_binaries, cyipopt_hiddenimports = collect_all('cyipopt')

# 手动列出所有已知的、可能被动态导入的 Pyomo 插件模块，作为兜底
plugin_modules = [
    'pyomo.common.plugins',
    'pyomo.opt.plugins',
    'pyomo.dataportal.plugins',
    'pyomo.duality.plugins',
    'pyomo.core.plugins',
    'pyomo.solvers.plugins',
    'pyomo.repn.plugins',
    'pyomo.scripting.plugins',
    'pyomo.network.plugins',
    'pyomo.checker.plugins',
    'pyomo.dae.plugins',
    'pyomo.gdp.plugins',
    'pyomo.mpec.plugins',
    'pyomo.pysp.plugins',
    'pyomo.util.plugins',
    'pyomo.common.dependencies',
    'pyomo.common.errors',
    'pyomo.common.log',
    'pyomo.common.timing',
]

# 合并所有 hidden imports
all_hiddenimports = set(pyomo_hiddenimports + cyipopt_hiddenimports + plugin_modules)

a = Analysis(
    ['main2.py'],
    pathex=[],
    binaries=pyomo_binaries + cyipopt_binaries,
    datas=pyomo_datas + cyipopt_datas + [(ipopt_exe_path, '.')],
    hiddenimports=list(all_hiddenimports),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# 对于目录模式，还需要生成 COLLECT 部分
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='main2',
)