# pyrtools: Windows Version

## Statement
This project is to make `pyrtools` available on `Windows`. I tested it on Windows 10 64-bit. If you have other operating system, please rebuild c code in `pyrtools/pyramids/c/Windows` into `*.dll`.

## 基础工作
原始项目地址 https://github.com/LabForComputationalVision/pyrtools

## 错误原因
在 `Windows` 系统下安装时，`ext_modules` 中的 `*.c` 文件不会像在其他系统一样被编译成动态链接库，而是 `*.pyd` 文件。但是 `*.pyd` 文件下的函数和方法需要经过 `PyInit_` 的封装才能被正确链接。该项目中的装饰是直接用 `Cython` 调用动态链接库装饰而成的 Python 函数.

## 解决办法
采用 `Windows` 下生成动态链接库的方法重新封装了 `*.c` 中的函数，并且编译成 `*.dll` 文件，再修改 `wrapper.py` 的代码，当检测到是 `Windows` 系统时直接利用 `Cython` 进行调用。在编译环节无论是采用 `MSVC` 还是 `MinGw` 均可。修改过的代码在 `pyrtools/pyramids/c/Windows` 目录下。

## 安装
请在安装之前请先确认操作系统版本与位数，如果与我不一致，请仔细阅读解决办法，手动编译动态链接库，再执行 `python setup.py install`。如有问题可与我联系。

