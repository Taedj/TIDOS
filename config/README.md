# TIDOS Configuration (`config/`)

The `config/` directory contains centralized configuration files for the TIDOS framework. These files define canonical values used throughout the documentation and scripts.

## Purpose

By centralizing configuration (repository URL, version, metadata) in this directory, TIDOS avoids hardcoded values scattered across dozens of files. When the repository moves or versions change, only `config/framework.md` needs updating.

## Contents

- [framework.md](framework.md) - Repository metadata, version info, and canonical URLs
