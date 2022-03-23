# Changelog

All notable changes to this project will be documented in this file. See [standard-version](https://github.com/conventional-changelog/standard-version) for commit guidelines.

## [4.5.0](https://github.com/jayanthkoushik/corgy/compare/v4.4.0...v4.5.0) (2022-03-23)


### Features

* allow specifying default values in `Corgy.add_args_to_parser` and `Corgy.parse_from_cmdline` ([06598c5](https://github.com/jayanthkoushik/corgy/commit/06598c57a4f87ccc7f564c8dd9e15f2245de4e91))

## [4.4.0](https://github.com/jayanthkoushik/corgy/compare/v4.3.0...v4.4.0) (2022-02-07)


### Features

* add handlers to close `corgy.types` file types on exit ([c29e367](https://github.com/jayanthkoushik/corgy/commit/c29e367eb50b25d383b13fce5656157c696c801e))
* add wrappers for `sys.__std<in/out/err>__` to `corgy.types` ([d5f26f1](https://github.com/jayanthkoushik/corgy/commit/d5f26f182500fbd760e9b774b6851d5838ba9395))
* allow creating empty `Corgy` classes ([c259117](https://github.com/jayanthkoushik/corgy/commit/c259117346c389b1d7deadf081cb0ea1dfa30761))
* handle optional positional arguments in `Corgy` classes ([95bb1a6](https://github.com/jayanthkoushik/corgy/commit/95bb1a677196283b29190bc7c84b6be847368ef3))
* raise `TypeError` if `Corgy` instantiated directly ([a64b094](https://github.com/jayanthkoushik/corgy/commit/a64b0947b72fca53528bb1467226d541a357c86b))

## [4.3.0](https://github.com/jayanthkoushik/corgy/compare/v4.2.0...v4.3.0) (2022-01-19)


### Features

* add `as_dict` method to convert `Corgy` classes to dicts ([08c2e0a](https://github.com/jayanthkoushik/corgy/commit/08c2e0a7c7f3421d4f503ef7f81ffb86e917b7b0))
* add `InitArgs` type to generate `Corgy` classes for constructors ([1c8ab43](https://github.com/jayanthkoushik/corgy/commit/1c8ab434f0d60b2233c6879828ba6f490c44d3dd))
* allow default usage formatting with `CorgyHelpFormatter` ([863997e](https://github.com/jayanthkoushik/corgy/commit/863997e4ec99650f9bf62384c2eaabc071a36fa7))
* show usage with help if `CorgyHelpFormatter.show_full_help` is `True` ([ff6685d](https://github.com/jayanthkoushik/corgy/commit/ff6685d0684bf25d2f757697ed88cc7bf7fd2198))
* support new style optional type annotations in Python 3.10+ ([267d459](https://github.com/jayanthkoushik/corgy/commit/267d459174e0f7341e5d71dba413d951a09a3a4f))


### Bug Fixes

* handle `__args__` being present when checking for empty sequences ([370a954](https://github.com/jayanthkoushik/corgy/commit/370a954afe062c51e54818b2f7169caca6c0fe08))
* identify sequence types without `[]` in `Corgy` classes ([a5b42b5](https://github.com/jayanthkoushik/corgy/commit/a5b42b578e9eea0875e8bc574c0a2f38a881905c))

## [4.2.0](https://github.com/jayanthkoushik/corgy/compare/v4.1.0...v4.2.0) (2021-12-14)


### Features

* add copy constructors for `corgy.types` classes ([664d4c2](https://github.com/jayanthkoushik/corgy/commit/664d4c2d34712bf6b55eeb2a561734d08ba3d3e1))
* add dummy `init` methods to non-lazy output file types for compatibility ([1a19df5](https://github.com/jayanthkoushik/corgy/commit/1a19df502081942c4ad881161fcaaeb007c0fa71))
* add lazy output directory type ([1f64087](https://github.com/jayanthkoushik/corgy/commit/1f64087b6704ead04b8c41274a80a9794d65508d))
* add lazy output file types ([e1225b1](https://github.com/jayanthkoushik/corgy/commit/e1225b1ae3b9f58e1314b9d05532dee72e40cf70))


### Bug Fixes

* correctly handle positional argument flags in `Corgy` ([8d2f382](https://github.com/jayanthkoushik/corgy/commit/8d2f3825123d16a855fe3900369a88eaf56ccbd1))

## [4.1.0](https://github.com/jayanthkoushik/corgy/compare/v4.0.0...v4.1.0) (2021-12-06)


### Features

* fully support Python 3.7 and 3.8 ([9648ef8](https://github.com/jayanthkoushik/corgy/commit/9648ef8f85cc441abe80c418f26f45a7f889fb71))
* use local version of `BooleanOptionalAction` to support Python 3.7 and 3.8 ([61c5a89](https://github.com/jayanthkoushik/corgy/commit/61c5a897f1a227b51f702ad9be29f52aba479ec3))

## [4.0.0](https://github.com/jayanthkoushik/corgy/compare/v3.1.0...v4.0.0) (2021-12-05)


### ⚠ BREAKING CHANGES

* `__corgy_fmt_choice__` is no longer used to format
choices in `CorgyHelpFormatter`

### Features

* add `Action` classes for showing short/full help ([627eae5](https://github.com/jayanthkoushik/corgy/commit/627eae5a31bd04c0b5165fd9b3ed7ee7602a716a))
* add `CorgyHelpFormatter.show_full_help` option to configure help verbosity ([f25ee3f](https://github.com/jayanthkoushik/corgy/commit/f25ee3f39206319ff8189e052acbc6b3f682796f))
* add more informative `__repr__` and `__str__` for `types` classes ([d1881f6](https://github.com/jayanthkoushik/corgy/commit/d1881f6e05de4dea839db8a941210745eb90d6a8))
* disable explicit `optional` marker for arguments with `nargs=0` in `CorgyHelpFormatter` ([6c76be8](https://github.com/jayanthkoushik/corgy/commit/6c76be889c7b69c820512ae663b41837e04fc00d))
* implement `Corgy.__str__` which calls `__str__` on members ([7c1c003](https://github.com/jayanthkoushik/corgy/commit/7c1c0032577081c3d3dddcfe5c6126afa46e6d75))
* make `CorgyHelpFormatter.max_help_position` adaptive ([543bca8](https://github.com/jayanthkoushik/corgy/commit/543bca88b06541cdfd3260dcc47710ff76c61d12))
* simplify `types.SubClass.__metavar__` ([0b4e74c](https://github.com/jayanthkoushik/corgy/commit/0b4e74c1f284bc879d61a56954e5afa02b38df4b))
* use `__str__` instead of `__repr__` to display choices and defaults in `CorgyHelpFormatter` ([9d6af55](https://github.com/jayanthkoushik/corgy/commit/9d6af55ee1700d42450242614c20d93170c7987f))


### Bug Fixes

* handle current directory output file types ([538e810](https://github.com/jayanthkoushik/corgy/commit/538e810dee583e1c2e8a6e63d7356f457f6b302c))
* handle exceptions when stringifying inside `CorgyHelpFormatter` ([50a7764](https://github.com/jayanthkoushik/corgy/commit/50a77641f1d3f498a14b9b09b11b603594907600))
* update `corgyparser` type annotation to allow nested wrapping ([08ef0ae](https://github.com/jayanthkoushik/corgy/commit/08ef0ae89e658291d1191b34d899978fa6c3f115))


### revert

* remove support for `__corgy_fmt_choice__` since `__repr__` can do the same ([0070ff0](https://github.com/jayanthkoushik/corgy/commit/0070ff0cf4da1bcb38327bc6a2d32d864e1db34b))

## [3.1.0](https://github.com/jayanthkoushik/corgy/compare/v3.0.0...v3.1.0) (2021-12-02)


### Features

* add `py.typed` to inform type checkers about annotations ([e008b7b](https://github.com/jayanthkoushik/corgy/commit/e008b7bd73cd51c06102cc688111b539db904159))
* prevent re sub-scripting `types.SubClass` and `types.KeyValuePairs` ([fc2314b](https://github.com/jayanthkoushik/corgy/commit/fc2314b7a6c3a0b1f6bd1b85bfefc4a7b98d76d3))
* remove deprecated `Corgy.new_with_args` ([1c0b270](https://github.com/jayanthkoushik/corgy/commit/1c0b27088cdbe21f9428e78567500cd43bd8e234))

## [3.0.0](https://github.com/jayanthkoushik/corgy/compare/v2.4.0...v3.0.0) (2021-12-02)


### ⚠ BREAKING CHANGES

* rewrite `corgy.types` to work better with typing

### Features

* rewrite `corgy.types` to work better with typing ([252a823](https://github.com/jayanthkoushik/corgy/commit/252a82336d5a4b1fe2ef9dfc8bc31e1c15921bfd))

## [2.4.0](https://github.com/jayanthkoushik/corgy/compare/v2.3.0...v2.4.0) (2021-11-29)


### Features

* add nested groups to the base parser in `Corgy.add_args_to_parser` ([720178e](https://github.com/jayanthkoushik/corgy/commit/720178e7ff2a8de24c590346713ed55c197b20f5))
* allow `@staticmethod` to be used with `@corgyparser` ([17c2115](https://github.com/jayanthkoushik/corgy/commit/17c2115017cfb35b470da200b9377ee1ba75aca8))
* allow custom `__slots__` in `Corgy` classes ([1532b15](https://github.com/jayanthkoushik/corgy/commit/1532b15d3b167955294a83c61ad161e7394708b8))
* allow functions decorated by `@corgyparser` to be used as static methods ([8ed8727](https://github.com/jayanthkoushik/corgy/commit/8ed8727a955dea5cb6f53ffad4621756ceb3d6bc))
* allow multiple `@corgyparser` decorators on the same function ([a96d5b7](https://github.com/jayanthkoushik/corgy/commit/a96d5b7a4cef9edcc78e6a0611634174fbbbf49d))
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
