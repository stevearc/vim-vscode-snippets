# vim-vsnip-snippets
A collection of vscode snippets for vim

> Why does this project exist?

Inspired by [vim-polyglot](https://github.com/sheerun/vim-polyglot), I didn't
want to have to hunt down and find a ton of different VSCode extensions just to
have vsnip snippets for the languages I work with. I want one easy installation
that *doesn't* come with a bunch of bloat (a lot of those extensions have images
or even videos in their repo). This repo has *only* the snippet files for a
range of languages.

This repository is in its early days, and I've only added extensions for a few
languages that I use most often. If your favorite language is missing, please
submit a pull request with the missing extension (see
[Contributing](#contributing) below).

## Installation
Supports any vim package manager, e.g. [Pathogen](https://github.com/tpope/vim-pathogen), [Vundle](https://github.com/VundleVim/Vundle.vim), [NeoBundle](https://github.com/Shougo/neobundle.vim), or [Plug](https://github.com/junegunn/vim-plug).

## Languages
* bat - [vscode](https://github.com/microsoft/vscode.git)
* c - [vscode](https://github.com/microsoft/vscode.git)
* coffeescript - [vscode](https://github.com/microsoft/vscode.git)
* cpp - [vscode](https://github.com/microsoft/vscode.git)
* csharp - [vscode-csharp-snippets](https://github.com/J0rgeSerran0/vscode-csharp-snippets.git), [vscode-unity-code-snippets](https://github.com/kleber-swf/vscode-unity-code-snippets.git), [vscode](https://github.com/microsoft/vscode.git)
* fsharp - [vscode](https://github.com/microsoft/vscode.git)
* go - [vscode-go](https://github.com/golang/vscode-go.git)
* groovy - [vscode](https://github.com/microsoft/vscode.git)
* html - [php-awesome-snippets](https://github.com/h4kst3r/php-awesome-snippets.git), [vscode-javascript](https://github.com/xabikos/vscode-javascript.git)
* java - [vscode](https://github.com/microsoft/vscode.git)
* javascript - [vscode-es7-javascript-react-snippets](https://github.com/dsznajder/vscode-es7-javascript-react-snippets.git), [vscode](https://github.com/microsoft/vscode.git), [vscode-javascript](https://github.com/xabikos/vscode-javascript.git)
* lua - [vsc-lua](https://github.com/keyring/vsc-lua.git)
* markdown - [vscode](https://github.com/microsoft/vscode.git)
* php - [php-awesome-snippets](https://github.com/h4kst3r/php-awesome-snippets.git), [vscode](https://github.com/microsoft/vscode.git)
* powershell - [vscode](https://github.com/microsoft/vscode.git)
* python - [vscode-python-snippet-pack](https://github.com/ylcnfrht/vscode-python-snippet-pack.git)
* rust - [vscode-rust](https://github.com/rust-lang/vscode-rust.git)
* swift - [vscode](https://github.com/microsoft/vscode.git)
* typescript - [vscode-es7-javascript-react-snippets](https://github.com/dsznajder/vscode-es7-javascript-react-snippets.git), [vscode](https://github.com/microsoft/vscode.git), [vscode-javascript](https://github.com/xabikos/vscode-javascript.git)
* vb - [vscode](https://github.com/microsoft/vscode.git)
* vue - [vscode-javascript](https://github.com/xabikos/vscode-javascript.git)

## Contributing
All snippets are generated programmatically. To add new extensions:

* Edit `sources.json` 
* Run the `build.py` script (requires `pip install json5`)
* Open a pull request

## License

The build script and all other code unique to this repository are under the MIT
license (see LICENSE file). All snippets are under the specific license of their
source repository. Each of these is in a subdirectory under `snippets/`, and
their applicable license(s) are present in that subdirectory.
