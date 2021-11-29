# Changelog

## [2.4.0](https://github.com/jayanthkoushik/corgy/compare/v2.3.0...v2.4.0) (2021-11-29)


### Features

* add nested groups to the base parser in `Corgy.add_args_to_parser` ([720178e](https://github.com/jayanthkoushik/corgy/commit/720178e7ff2a8de24c590346713ed55c197b20f5))
* allow `[@staticmethod](https://github.com/staticmethod)` to be used with `[@corgyparser](https://github.com/corgyparser)` ([17c2115](https://github.com/jayanthkoushik/corgy/commit/17c2115017cfb35b470da200b9377ee1ba75aca8))
* allow custom `__slots__` in `Corgy` classes ([1532b15](https://github.com/jayanthkoushik/corgy/commit/1532b15d3b167955294a83c61ad161e7394708b8))
* allow functions decorated by `[@corgyparser](https://github.com/corgyparser)` to be used as static methods ([8ed8727](https://github.com/jayanthkoushik/corgy/commit/8ed8727a955dea5cb6f53ffad4621756ceb3d6bc))
* allow multiple `[@corgyparser](https://github.com/corgyparser)` decorators on the same function ([a96d5b7](https://github.com/jayanthkoushik/corgy/commit/a96d5b7a4cef9edcc78e6a0611634174fbbbf49d))
* implement `__repr__` for `types` members ([2b12191](https://github.com/jayanthkoushik/corgy/commit/2b12191f30032704a099a4a70d61ccc5493b2c46))
* use custom metavar if present in `Corgy.add_args_to_parser` ([332ddc1](https://github.com/jayanthkoushik/corgy/commit/332ddc1e155ef0146e02fe37b5b8b2a129f99e1d))

## [2.3.0](https://github.com/jayanthkoushik/corgy/compare/v2.2.0...v2.3.0) (2021-11-24)


### Features

* implement `Corgy.__init__` and deprecate `new_with_args` ([2413eef](https://github.com/jayanthkoushik/corgy/commit/2413eefb281705c0dae7a28dc90364c28aef9b1e))
* make `Corgy.__repr__` equal to `__str__` ([a72527d](https://github.com/jayanthkoushik/corgy/commit/a72527dddad39cf467007a921f6a8dd480a9d521))
* show informative message if trying to import `Corgy` with Python < 3.9 ([9ec99ce](https://github.com/jayanthkoushik/corgy/commit/9ec99ce25794c62471af09876c2a6fabf6db9a2f))

## [2.2.0](https://github.com/jayanthkoushik/corgy/compare/v2.1.0...v2.2.0) (2021-11-24)


### Features

* add `__choices__` to `types.SubClassType` ([b817e17](https://github.com/jayanthkoushik/corgy/commit/b817e1736e5c34349182e20b4f0b8e5aece4392e))
* allow `Literal` types to be classes themselves ([b772e6e](https://github.com/jayanthkoushik/corgy/commit/b772e6eb57db310f17716c147df0e9765876a2b1))
* allow custom choices with `__choices__` ([3140aaa](https://github.com/jayanthkoushik/corgy/commit/3140aaa96bb18e2a82a54b31296f9066bf7731a6))

## [2.1.0](https://github.com/jayanthkoushik/corgy/compare/v2.0.1...v2.1.0) (2021-11-21)


### Features

* add option to use full option names in `SubClassType` ([c4b68d7](https://github.com/jayanthkoushik/corgy/commit/c4b68d7cb9e4ea143c65260f1f534d4eed699a16))
* allow customizing choice formatting with `__corgy_choice_str__` ([97b925d](https://github.com/jayanthkoushik/corgy/commit/97b925d15ef79cc03ee130a9fc9be0e28890d2ce))

### [2.0.1](https://github.com/jayanthkoushik/corgy/compare/v2.0.0...v2.0.1) (2021-11-16)


### Bug Fixes

* disable lru cache for stringify helper function ([589b6c4](https://github.com/jayanthkoushik/corgy/commit/589b6c45fa44f2bd2efc65b0dc2fdd9e2a287fd7))

## [2.0.0](https://github.com/jayanthkoushik/corgy/compare/v1.5.0...v2.0.0) (2021-11-16)


### ⚠ BREAKING CHANGES

* return the actual types from `SubClassType.choices` for compatibility with `argparse`

### Features

* make `Corgy.new_with_args` public ([b025614](https://github.com/jayanthkoushik/corgy/commit/b0256141b9f46db0b657e00a825433946a81e2f5))
* use `__name__` for displaying choices/defaults if available ([4603c29](https://github.com/jayanthkoushik/corgy/commit/4603c295f5c3a9abe1e9f467c040655d29b731b8))


### Bug Fixes

* allow parsing with extra args in `Corgy.parse_from_cmdline` ([f565a84](https://github.com/jayanthkoushik/corgy/commit/f565a84df86b87b062c668d15b69bdc1eea9d12a))
* return the actual types from `SubClassType.choices` for compatibility with `argparse` ([17a693e](https://github.com/jayanthkoushik/corgy/commit/17a693e39c4d5208a44027d23830a49f2749c82c))

## [1.5.0](https://github.com/jayanthkoushik/corgy/compare/v1.4.0...v1.5.0) (2021-10-19)


### Features

* allow specifying custom flags in `Corgy` classes ([6111bca](https://github.com/jayanthkoushik/corgy/commit/6111bca5538e9f2a1175a7897804316a3968988e))

## [1.4.0](https://github.com/jayanthkoushik/corgy/compare/v1.3.0...v1.4.0) (2021-09-28)


### Features

* add `corgy.types.KeyValueType` ([8d0df8b](https://github.com/jayanthkoushik/corgy/commit/8d0df8b88f72c5ed218a2b436ddc1a5acfa548c9))

## [1.3.0](https://github.com/jayanthkoushik/corgy/compare/v1.2.2...v1.3.0) (2021-09-21)


### Features

* add limited support for Python 3.7 and 3.8 ([7ffa1d5](https://github.com/jayanthkoushik/corgy/commit/7ffa1d5e5f28c6336d8f4eaf8d99d2b57cdcc23d))


### Bug Fixes

* remove incorrect type annotation in `InputFileType` ([bb70a26](https://github.com/jayanthkoushik/corgy/commit/bb70a2658b1358f87e0be386d231e0b7eb454912))

### [1.2.2](https://github.com/jayanthkoushik/corgy/compare/v1.2.1...v1.2.2) (2021-09-16)


### Bug Fixes

* handle `__name__` being unavailable when getting default metavar ([f7b3869](https://github.com/jayanthkoushik/corgy/commit/f7b38699e2fd7293f5970e149dc78537a1762cfa))

### [1.2.1](https://github.com/jayanthkoushik/corgy/compare/v1.2.0...v1.2.1) (2021-09-13)


### Bug Fixes

* allow all valid modes in `Input/OutputFileType` ([5b094ec](https://github.com/jayanthkoushik/corgy/commit/5b094ec5fff7a7687e10dc8fd10097338753f16f))
* handle formatted defaults when removing suffix for `BooleanOptionalAction` ([b41be44](https://github.com/jayanthkoushik/corgy/commit/b41be444ea6e877b02668c323acca5e3ba117b9a))

## [1.2.0](https://github.com/jayanthkoushik/corgy/compare/v1.1.0...v1.2.0) (2021-08-30)


### Features

* add `types` module ([1e8c702](https://github.com/jayanthkoushik/corgy/commit/1e8c7025dd866144bd7fbaad509da9c882b17643))
* allow arbitrary objects to be used as types in `Corgy` classes ([3f8d2b8](https://github.com/jayanthkoushik/corgy/commit/3f8d2b87bfee56f471a5921c1cd82a48b1471536))
* use function name for metavar instead of return type ([51e8023](https://github.com/jayanthkoushik/corgy/commit/51e80237b9c609e229dcb8d2d94dd3c11d55eb85))
