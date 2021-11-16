# Changelog

## [2.0.0](https://github.com/jayanthkoushik/corgy/compare/v1.5.0...v2.0.0) (2021-11-16)


### ⚠ BREAKING CHANGES

* return the actual types from SubClassType.choices for compatibility with argparse

### Features

* make Corgy.new_with_args public ([b025614](https://github.com/jayanthkoushik/corgy/commit/b0256141b9f46db0b657e00a825433946a81e2f5))
* use __name__ for displaying choices/defaults if available ([4603c29](https://github.com/jayanthkoushik/corgy/commit/4603c295f5c3a9abe1e9f467c040655d29b731b8))


### Bug Fixes

* allow parsing with extra args in Corgy.parse_from_cmdline ([f565a84](https://github.com/jayanthkoushik/corgy/commit/f565a84df86b87b062c668d15b69bdc1eea9d12a))
* return the actual types from SubClassType.choices for compatibility with argparse ([17a693e](https://github.com/jayanthkoushik/corgy/commit/17a693e39c4d5208a44027d23830a49f2749c82c))

## [1.5.0](https://github.com/jayanthkoushik/corgy/compare/v1.4.0...v1.5.0) (2021-10-19)


### Features

* allow specifying custom flags in Corgy classes ([6111bca](https://github.com/jayanthkoushik/corgy/commit/6111bca5538e9f2a1175a7897804316a3968988e))

## [1.4.0](https://github.com/jayanthkoushik/corgy/compare/v1.3.0...v1.4.0) (2021-09-28)


### Features

* add corgy.types.KeyValueType ([8d0df8b](https://github.com/jayanthkoushik/corgy/commit/8d0df8b88f72c5ed218a2b436ddc1a5acfa548c9))

## [1.3.0](https://github.com/jayanthkoushik/corgy/compare/v1.2.2...v1.3.0) (2021-09-21)


### Features

* add limited support for Python 3.7 and 3.8 ([7ffa1d5](https://github.com/jayanthkoushik/corgy/commit/7ffa1d5e5f28c6336d8f4eaf8d99d2b57cdcc23d))


### Bug Fixes

* remove incorrect type annotation in InputFileType ([bb70a26](https://github.com/jayanthkoushik/corgy/commit/bb70a2658b1358f87e0be386d231e0b7eb454912))

### [1.2.2](https://github.com/jayanthkoushik/corgy/compare/v1.2.1...v1.2.2) (2021-09-16)


### Bug Fixes

* handle __name__ being unavailable when getting default metavar ([f7b3869](https://github.com/jayanthkoushik/corgy/commit/f7b38699e2fd7293f5970e149dc78537a1762cfa))

### [1.2.1](https://github.com/jayanthkoushik/corgy/compare/v1.2.0...v1.2.1) (2021-09-13)


### Bug Fixes

* allow all valid modes in Input/OutputFileType ([5b094ec](https://github.com/jayanthkoushik/corgy/commit/5b094ec5fff7a7687e10dc8fd10097338753f16f))
* handle formatted defaults when removing suffix for BooleanOptionalAction ([b41be44](https://github.com/jayanthkoushik/corgy/commit/b41be444ea6e877b02668c323acca5e3ba117b9a))

## [1.2.0](https://github.com/jayanthkoushik/corgy/compare/v1.1.0...v1.2.0) (2021-08-30)


### Features

* add types module ([1e8c702](https://github.com/jayanthkoushik/corgy/commit/1e8c7025dd866144bd7fbaad509da9c882b17643))
* allow arbitrary objects to be used as types in Corgy classes ([3f8d2b8](https://github.com/jayanthkoushik/corgy/commit/3f8d2b87bfee56f471a5921c1cd82a48b1471536))
* use function name for metavar instead of return type ([51e8023](https://github.com/jayanthkoushik/corgy/commit/51e80237b9c609e229dcb8d2d94dd3c11d55eb85))
