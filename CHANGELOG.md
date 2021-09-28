# Changelog

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
