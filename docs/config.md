+++
title = 'config'
date = 2025-01-18T15:43:18+08:00
description = 'Config tool for creating a config file template.'
+++

`kci-dev config` is a config tool for creating a config file template.
This command is needed when no configuration is present.

### kci-dev config

`kci-dev config` without arguments will check for config file,  
if none are found will create a config file template by default to  
`~/config/kci-dev/kci-dev.toml`    

## Base parameters

### --file-path

Optional file path for creating a config file,   
if none is provided `~/config/kci-dev/kci-dev.toml` is used.   

## Example

### kci-dev config

Example:

```sh
$ kci-dev config
Config file not present, adding a config file to ~/.config/kci-dev/kci-dev.toml
```

### kci-dev config --file-path

Example:

```sh
$ kci-dev config --file-path ~/test/test.toml
Config file not present, adding a config file to ~/test/test.toml
```

