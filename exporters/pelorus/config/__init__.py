"""
A declarative way to load configuration from environment variables, and log that configuration properly.

Configuration needs to be consistent, and easy to get right.
Configuration should be logged in order to make debugging easier.
However, accidentally logging sensitive information (API credentials, etc.) must be hard.

This module handles the above goals by using `attrs`.

# A Simple Example

```python
from pelorus.config import config, load_and_log, var

@config
class MyConfiguration:
    username: str = "GVR"
    password: str
    namespaces: list[str]
```

Calling `load_and_log(MyConfiguration)` will perform the following:

1. Look for the environment variable `USERNAME`.
2. Look for the environment variable `PASSWORD`.
3. Look for the environment variable `NAMESPACES` and split at each comma, stripping all whitespace.
4. Call `MyConfiguration(...)`:
  If `USERNAME` is missing, it will default to `GVR`.
  If `PASSWORD` is missing, a TypeError will be thrown.
  If `NAMESPACES` is present but empty, an empty list will be given.

It will then print `MyConfiguration` followed by each field's value.
Sensitive values will be redacted.
Each field will also list where the value came from.

For example:

1. `username=GVR default value; USERNAME was not set)`
2. `password=REDACTED (from env var PASSWORD)`.
  (Any field name that contains any word in `REDACT_WORDS` will not be printed by default.)
3. `namespaces=[''] (from env var NAMESPACES)`

# Supported Variable Types

| type      | transformation from str                                 |
|-----------|---------------------------------------------------------|
| str       | set as-is                                               |
| list[str] | split on `,` with whitespace stripped from each element |
| set[str]  | same as above                                           |

Optional versions of the above will always work, but the default must be set to `None`.

Other types may be supported with customization and converters, shown in the next section.

# Customization

You may need to deviate from the default behavior, or pass an argument that won't come from the environment.
You can customize each field with `var`:

@config
class AdvancedConfiguration:
    anonymous_user: str = var(log=False)
    should_pass_tests: bool = var(log=True)
    whoami: str = var(env_lookups=["API_USER", "GIT_USER"])

    api_client: Client = var(env_lookups=None)

    optional_name: str = var(default="someone")
    optional_list: list[str] = var(factory=list)

    _private_field: Any = var(env_lookups=[])
    public_but_ignore_me: Any = var(log=None)

Notable differences:
- anonymous_user will not be logged, when it otherwise would be.
- should_pass_tests _will_ be logged.
  We'd assume it's sensitive because it has "pass" in it, so we override that behavior.
- whoami is set to the first value found of either `API_USER` or `GIT_USER`, instead of looking at `WHOAMI`.
- optional_name and optional_list are optional.
- optional_list uses `factory` because using an empty list in `default` would mean every instance sharing the same list!
  This is known as the "python mutable default arg" issue.
- _private_field and public_but_ignore_me will not be logged at all-- not even redacted.

api_client is not looked for at all. This is meant to handle objects that are more complex to set up.
You will need to pass it when using `load`:
`load_and_log(AdvancedConfiguration, other=dict(api_client=client_instance))`

## Converters

`var` wraps `attrs.field`. You can support fancier type transformations using converters.
Attrs even allows them to be composed.

You should consider supporting passing in an object of the target type,
having each converter skip it if it's already correct.

```python
from typing import Optional
from pelorus.config import var, config
from pelorus.config.converters import comma_separated
from attrs.converters import default_if_none

def treat_empty_str_as_none(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return None
    else:
        return value


@config
class FancyConfig:
    not_quite_a_list: SomeCollection[str] = var(field_args=dict(
            converters=comma_separated(SomeCollection)
            ))

    required_int_with_empty_as_zero: int = var(field_args=dict(
            converters=[treat_empty_str_as_none, default_if_none(default=0), int]
    ))
```

The env vars:
NOT_QUITE_A_LIST="foo,bar"
REQUIRED_INT_WITH_EMPTY_AS_ZERO="3"

Will result in the equivalent of:
```python
FancyConfig(
    not_quite_a_list=SomeCollection("foo", "bar"),
    required_int_with_empty_as_zero=4
    )
```

While the env vars:
NOT_QUITE_A_LIST=""
REQUIRED_INT_WITH_EMPTY_AS_ZERO=""

Will result in the equivalent of:
```python
FancyConfig(
    not_quite_a_list=SomeCollection(),
    required_int_with_empty_as_zero=0
    )
```

# Details

See each individual function for details.

# Development

See [DEVELOPING.md](./DEVELOPING.md) for details.
"""
