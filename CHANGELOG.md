# Changelog

All notable changes to this project will be documented in this file. See [standard-version](https://github.com/conventional-changelog/standard-version) for commit guidelines.

### [8.0.1](https://github.com/jayanthkoushik/corgy/compare/v8.0.0...v8.0.1) (2023-04-14)


### Bug Fixes

* raise `ArgumentError` instead of `ArgumentTypeError` from `CorgyParserAction` ([f798132](https://github.com/jayanthkoushik/corgy/commit/f79813285a80ffeaf6d61a56b4829ec882d90372))

## [8.0.0](https://github.com/jayanthkoushik/corgy/compare/v7.0.0...v8.0.0) (2023-04-14)


### ⚠ BREAKING CHANGES

* The following path based types have been removed from
`Corgy.types`: `ReadableFile`, `WritableFile`, `InputDirectory`,
`OutputDirectory`, `LazyOutputDirectory`, `IODirectory`. The "promises"
communicated by these types were only true when objects were created
by calling the type--any operation could cause they types to have a value
that did not satisfy the type's condition. For example, with
`f: ReadableFile`, `f.parent` would be an object of type `ReadableFile`,
but is not a file at all. For enforcing the conditions provided by the
removed types in `Corgy` classes, custom parsers should be used instead.

### Features

* use `store_*` actions in `Corgy.add_args_to_parser` for single value literals ([88b0aa1](https://github.com/jayanthkoushik/corgy/commit/88b0aa15a6de4024b43185bd0ed09e54a3f3462b))


* remove path sub-class types ([ac73147](https://github.com/jayanthkoushik/corgy/commit/ac7314733ffcca1c1f3be0173a3a9fff1c9a587d))

## [7.0.0](https://github.com/jayanthkoushik/corgy/compare/v6.0.0...v7.0.0) (2023-04-11)


### ⚠ BREAKING CHANGES

* A few types in `corgy.types` accepted arbitrary keyword
arguments. This was not consistent, not tested, and has been removed.
All file related types now accept a single "path-like" argument.
* `Path` subclasses in `corgy.types` now perform user
home (~) and environment variable expansion by default. These classes
also have two new attributes: `do_expanduser` and `do_expandvars` which
can be set to `False` to disable expansion of home and environment vars
respectively.
* `OutputTextFile.stdout_wrapper`,
`OutputTextFile.stderr_wrapper`, `InputTextFile.stdin_wrapper` are now
classmethods instead of classproperties. The change allows simpler
implementation without relying on custom metaclass, and also enables
type checking in these methods.
* The package no longer relies on, or uses
`typing.Required` and `typing.NotRequired`, since type checkers consider
it an error to use them outside of `TypedDict`s. `corgy` now provides
its own versions of these types, implemented using `typing.Annotated`,
so that type checking works as expected. Usage remains the same.

### Features

* add binary versions of `stdout/stderr/stdin` wrappers in `corgy.types` ([5083b23](https://github.com/jayanthkoushik/corgy/commit/5083b238e5e87d1917332ca0d735608893d40b3e))
* add types for input/output file paths ([f96eca7](https://github.com/jayanthkoushik/corgy/commit/f96eca710524d91605521cf237aede4a05d63eb9))
* perform user and environment variable expansion in `Path` types ([e3100fe](https://github.com/jayanthkoushik/corgy/commit/e3100feeb8c16845ca4edba4a0b6339d09fa7156))


### Bug Fixes

* do not convert positional bools to option pairs in `Corgy.add_args_to_parser` ([7fcda64](https://github.com/jayanthkoushik/corgy/commit/7fcda649a2a8f65d4b990a0f923b7371cb4173ae))
* fix handling of choices when using custom parsers ([40ec87b](https://github.com/jayanthkoushik/corgy/commit/40ec87b1ae44572bfdc591b9f819d8074c7c60c2))
* only mark args as 'optional' by 'CorgyHelpFormatter' if `default=SUPPRESS` ([5b7603f](https://github.com/jayanthkoushik/corgy/commit/5b7603f272a7f56fa9487c5dc523d876b4732269))
* remove `kwargs` from argument list of file types ([f3aa648](https://github.com/jayanthkoushik/corgy/commit/f3aa6487bb7cfd7acf61610c4dc0da93cd888bf0))
* use custom implementations of `Required` and `NotRequired` ([ebf0913](https://github.com/jayanthkoushik/corgy/commit/ebf0913c4f0b61ae9d88422456c477ef170dfbf1))
* use proper delegation to concrete `Path` types in `corgy.types` ([580dd86](https://github.com/jayanthkoushik/corgy/commit/580dd868c95b8f7e8d8a9ae4af2b0a1bdae767b0))


* rewrite `stdout/stderr/stdin` wrappers in \`corgy.types\` ([99307eb](https://github.com/jayanthkoushik/corgy/commit/99307ebf6f9811e79c907fcb292625d44a2552a8))

## [6.0.0](https://github.com/jayanthkoushik/corgy/compare/v5.0.0...v6.0.0) (2023-03-27)


### ⚠ BREAKING CHANGES

* By default, `Corgy.add_args_to_parser` now adds
attributes as optional. This makes command line parsing consistent with
the rest of the `Corgy` interface. To get the previous behavior,
pass `corgy_required_by_default=True` to the `Corgy` class. But note
that this will also make attributes required during init.
* Attributes marked with `Optional` are no longer added
by `Corgy.add_args_to_parser` with `optional=True`, unless they have a
default value. This behavior is consistent with the treatment of other
types--`Optional` only indicates that the attribute can be `None`. In
line with this change, `Optional` attributes are added with a custom
action with allows arguments to accept zero arguments (which will be
treated as `None`).
* `Corgy` now uses defaults only during `__init__`.
This means after init, attributes with default values are
undistinguishable from the rest. The key effect of this change is that
an attribute with a default value can be unset using `del`. Previously,
such attributes would "fallback" to the default value.
* `Corgy` now handles `Set` and `List` types for
collections. Collection handling has been re-written to fix various
issues.
* `Corgy.add_args_to_parser` no longer adds collection
types with custom actions. Dictionaries parsed from the command line
should be loaded using `Corgy.from_dict` with `try_cast=True`.
* `Corgy.parse_from_cmdline` and `Corgy.parse_from_toml`
now try to cast parsed values. This allows `parse_from_cmdline` to not
be dependent on custom actions added to the parser.
* Unset values of `Corgy` instances are no longer shown
by `repr`. This makes `repr` consistent with code for creating an
instance, i.e., `eval`ing the `repr` of a `Corgy` instance will create
an instance with the same values. `Corgy.__str__` is unchanged, and will
show unset values as before.
* The default value of the `recursive` argument of
`Corgy.as_dict` has been changed from `False` to `True`. Groups will be
converted to dictionaries recursively by default.
* By default, arguments with a custom parser will now
always receive a single string argument, regardless of the argument
type. This behavior can be controlled with the newly added `nargs`
argument for `@corgyparser`. Setting this argument (which is `None` by
default) will cause the set value to be passed as the `nargs` argument
for `ArgumentParser.add_argument`, and the correspondingly, the custom
parser will be called with all arguments in a list (unless `nargs` is
`None`).
* `Corgy` classes now enforce attribute types. This
applies to both assigned values, and defaults. Incorrectly typed values
will raise `ValueError`.
* `Corgy.__init__` no longer accepts group arguments
specified with the `:` syntax. Instead this functionality has been moved
to `Corgy.from_dict`.
* Classes in `corgy.types` raise `ValueError` instead of
`ArgumentTypeError`.

### Features

* add `Corgy.attrs` class method ([f39dc7b](https://github.com/jayanthkoushik/corgy/commit/f39dc7b0fa60f6e3b8add82bfb8493c8f9a2ba12))
* add `Corgy.freeze` method ([d855dd4](https://github.com/jayanthkoushik/corgy/commit/d855dd461b4f49712aecf7e03f328e0eda253dbb))
* add `Corgy.load_dict` method ([c2aa69a](https://github.com/jayanthkoushik/corgy/commit/c2aa69aec6e07de8adb69fa045712aed78c77ba5))
* add `corgy.types.IODirectory` type ([889f11c](https://github.com/jayanthkoushik/corgy/commit/889f11cf754831d813322dd47ceef41cf889f7c5))
* add `flatten` argument to `Corgy.as_dict` ([82207a0](https://github.com/jayanthkoushik/corgy/commit/82207a03ccaf8e31865acae3c6e3d46b40548c0a))
* add option to cast values in `Corgy.from_dict` ([267e325](https://github.com/jayanthkoushik/corgy/commit/267e325c74bc88639850f8cbb578f493cd4e085a))
* add support for `Required` and `NotRequired` annotations ([ba537d3](https://github.com/jayanthkoushik/corgy/commit/ba537d3a0069ebd36688a6029f68b38cca58c881))
* allow `Corgy` attributes with default values to be unset ([65550fa](https://github.com/jayanthkoushik/corgy/commit/65550fa40fec86249dc34f3eff61d3c081cea69d))
* allow `Corgy` class attributes to be unset with `del` ([da3c1c8](https://github.com/jayanthkoushik/corgy/commit/da3c1c8dbbe50864d8311ab9573aca3eb6089f97))
* allow `corgyparser` functions to specify nargs ([1d8d10c](https://github.com/jayanthkoushik/corgy/commit/1d8d10c96d7760e45637c1ffd48ee844f29835eb))
* allow freezing `Corgy` instances after init with `corgy_freeze_after_init` ([931f925](https://github.com/jayanthkoushik/corgy/commit/931f925938be8cd4ed7032adc0207dda194df647))
* allow passing multiple argument names to `corgyparser` ([9cd7539](https://github.com/jayanthkoushik/corgy/commit/9cd7539cff6d347a24b81aceed259f04e8ca19b4))
* allow setting metavar when decorating with `corgyparser` ([9b0b8f2](https://github.com/jayanthkoushik/corgy/commit/9b0b8f20ec0ba4f1fac5a4e0d96dbd8b22fdef7c))
* change typing annotation of `Corgy.from_dict` to accept arbitrary mappings ([a9d65cc](https://github.com/jayanthkoushik/corgy/commit/a9d65ccae6999e17b6da364fedb515a2dd5cc1d1))
* enforce type checking for `Corgy` classes ([6871838](https://github.com/jayanthkoushik/corgy/commit/687183815902dfc3b0bb30c9f513cffaa4a62939))
* handle formatting of nested sequence and optional types ([6c9fe58](https://github.com/jayanthkoushik/corgy/commit/6c9fe5896d5d7c80cf1b79ce4a020db2c75f4892))
* handle groups within collections in `Corgy.as_dict` ([b673335](https://github.com/jayanthkoushik/corgy/commit/b673335cb5ced43268b91bdb499e735a0c833148))
* handle groups within collections in `Corgy.from_dict` ([bf1b0ec](https://github.com/jayanthkoushik/corgy/commit/bf1b0ece091fb20e8f9e59b5e66926c3e9b68783))
* hide unset values in `Corgy.__repr__` ([7fda899](https://github.com/jayanthkoushik/corgy/commit/7fda899c0ffbdd3587b1105976efb1cd17a6d412))
* implement equality for `Corgy` instances ([bc56f54](https://github.com/jayanthkoushik/corgy/commit/bc56f543d7dde79fc66b87ff214d2199a85aca42))
* make `Corgy.as_dict` recursive by default ([f74e341](https://github.com/jayanthkoushik/corgy/commit/f74e3412d74c73dcabbf87001001fee3b4a7d43b))
* make `types.SubClass/KeyValuePairs/InitArgs` objects pickleable ([fbd817c](https://github.com/jayanthkoushik/corgy/commit/fbd817c2c6c900864e9a4c09a17bb64ffde4ff92))
* make formatting of zero or more sequence metavars in Python<3.9 match later versions ([261fcef](https://github.com/jayanthkoushik/corgy/commit/261fcefe3cf3f369d2df64d20493180fd3671b96))
* make parsing of `Optional` attributes consistent with other types ([c96cdd3](https://github.com/jayanthkoushik/corgy/commit/c96cdd39dd4f624d12c1908692f42086a5e6b162))
* move functionality to parse args with `:` from `Corgy.__init__` to ([f0378b8](https://github.com/jayanthkoushik/corgy/commit/f0378b830044953750be47da19f0cc827ecf687a))
* rewrite handling of collection types ([6c60628](https://github.com/jayanthkoushik/corgy/commit/6c6062836bf1ad65592afde0e5c12a33b1a77374))


### Bug Fixes

* correct formatting of tuples by `CorgyHelpFormatter` ([51b29ca](https://github.com/jayanthkoushik/corgy/commit/51b29caf6d46ef6abf2d6d9ec04885154748888d))
* don't use `BooleanOptionalAction` for `Literal` boolean types in `Corgy.add_args_to_parser` ([a8d0546](https://github.com/jayanthkoushik/corgy/commit/a8d0546c012b50eca90ae99c07631f87bf483c05))
* handle `dict` defaults/choices in `CorgyHelpFormatter` ([6d2c20c](https://github.com/jayanthkoushik/corgy/commit/6d2c20c995a7540cadc34876436cacb242534606))
* handle sequence edge cases in `CorgyHelpFormatter` ([2824e64](https://github.com/jayanthkoushik/corgy/commit/2824e645f3e099cc4e9bf30ace12cf6546a76168))
* prevent class variables from being assigned `corgyparsers` ([4cd9557](https://github.com/jayanthkoushik/corgy/commit/4cd9557938db38c20286ef0beec488021923e744))
* remove enclosing `[]` from `KeyValuePairs.__metavar__` ([195c614](https://github.com/jayanthkoushik/corgy/commit/195c614a69d6c29ba19e91eeead88ab518d43e61))
* use `__init__` to initialize in `Corgy.from_dict` ([2c3cd2a](https://github.com/jayanthkoushik/corgy/commit/2c3cd2abb905e8181a64d4de91e32df4ec27774c))
* use `_typeshed.StrPath` for annotations instead of custom implementation ([099736e](https://github.com/jayanthkoushik/corgy/commit/099736efc696f745106b4c51c224ec927e3bd100))
* use binary open mode for binary file types in `corgy.types` ([8469ae9](https://github.com/jayanthkoushik/corgy/commit/8469ae9c029f930c94790519bff4a932120db50c))
* use correct metavar when adding bool sequences in `Corgy.add_args_to_parser` ([70a3742](https://github.com/jayanthkoushik/corgy/commit/70a37426074fb5944b63f6f8e8f481f2e3a27d20))


* raise `ValueError` from classes in `corgy.types` if `__init__` fails ([deb4153](https://github.com/jayanthkoushik/corgy/commit/deb41538184237eaf2c3e307ec2dd7d8332a785d))

## [5.0.0](https://github.com/jayanthkoushik/corgy/compare/v4.7.0...v5.0.0) (2022-11-17)


### ⚠ BREAKING CHANGES

* function signature for `Corgy.add_args_to_parser` has
been changed. `make_group` and `group_help` arguments have been removed,
and `flatten_subgrps` argument has been added.

### Features

* add `SubClass.which` property ([ed37ea4](https://github.com/jayanthkoushik/corgy/commit/ed37ea4a7388b714f34ac54d5c476782681e8871))
* allow disabling `__slots__` in `Corgy` classes ([c3ac08b](https://github.com/jayanthkoushik/corgy/commit/c3ac08bce8a5ac0541e134553c7aabbc69fea3d3))
* handle `ClassVar` annotations in `Corgy` classes ([6d83ab4](https://github.com/jayanthkoushik/corgy/commit/6d83ab4e71fbd4f6c08f9cc485a1ac0d83d9fff7))
* re-write `Corgy.add_args_to_parser` to accept both parsers/groups ([492020b](https://github.com/jayanthkoushik/corgy/commit/492020bb4620f7b5f007b436ff8aeed75cc169be))


### Bug Fixes

* make `Corgy.from_dict` ignore unknown arguments ([49c94e4](https://github.com/jayanthkoushik/corgy/commit/49c94e4b5490cd15c82870d7cc1cf409da1f9219))
* raise `TypeError` if a `Corgy` class defines a conflicting slot variable ([90278b2](https://github.com/jayanthkoushik/corgy/commit/90278b2a6b0c7a91f8ff47be3b6df3387dc6c9d6))

## [4.7.0](https://github.com/jayanthkoushik/corgy/compare/v4.6.0...v4.7.0) (2022-08-16)


### Features

* allow `Tuple` to be used instead of `Sequence` in `Corgy` classes ([55fe0b6](https://github.com/jayanthkoushik/corgy/commit/55fe0b61b37d679b3663b6eeb45f634c99276ecf))

## [4.6.0](https://github.com/jayanthkoushik/corgy/compare/v4.5.0...v4.6.0) (2022-08-15)


### Features

* add `Corgy.from_dict` method ([cb53aee](https://github.com/jayanthkoushik/corgy/commit/cb53aeefb11dd74230cd8c774ce5746673b53b1b))
* add `Corgy.parse_from_toml` method ([bdb31b5](https://github.com/jayanthkoushik/corgy/commit/bdb31b5cbbd952d1c8c924ab673e2c4519bf4eb8))
* add argument to allow `Corgy.as_dict` to be recursive ([fede1bb](https://github.com/jayanthkoushik/corgy/commit/fede1bbf527c5242ccc292ee5c397bef91d418cc))
* allow `Corgy` classes to be sub-classed ([a0a9568](https://github.com/jayanthkoushik/corgy/commit/a0a9568ffca5feb533ac0f70abd4ff3949e16f88))
* allow `Corgy` classes to have string annotations ([f71a148](https://github.com/jayanthkoushik/corgy/commit/f71a14872af6763b953148f0e291dd4fc1a73232))


### Bug Fixes

* handle arbitrary depth descendants in `types.SubClass` ([106361a](https://github.com/jayanthkoushik/corgy/commit/106361a13bfc41d8038e9364396452858bb82923))
* handle imports from `typing_extensions` in Python>=3.9 ([3d017f9](https://github.com/jayanthkoushik/corgy/commit/3d017f9e6b295e4ec8acab492c389ae8145ffa93))
* handle unknown group arguments in `Corgy.__init__` ([d02ff89](https://github.com/jayanthkoushik/corgy/commit/d02ff897ac6893590ce587928d2af406ff865c84))
* use correct argument name for exception message in `Corgy.__init__` ([a5fa326](https://github.com/jayanthkoushik/corgy/commit/a5fa3262d59e37b92497833447af45377c479bce))

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
