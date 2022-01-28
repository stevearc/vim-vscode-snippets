# vim-vscode-snippets

A collection of vscode snippets for vim

The VSCode marketplace has a large number of extensions with code snippets
included. These snippets are not available in a format that can be easily
ingested by vim snippet plugins (e.g.
[vim-vsnip](https://github.com/hrsh7th/vim-vsnip) or
[luasnip](https://github.com/L3MON4D3/LuaSnip)). This plugin is the missing link
that gathers together a collection of snippets from VSCode extensions for many
languages. This repo contains _only_ the snippet files from those extensions.

If there is a language or extension missing, please
submit a pull request with the missing extension (see
[Contributing](#contributing) below).

## Installation

supports all the usual plugin managers

<details>
  <summary>Packer</summary>

```lua
require('packer').startup(function()
    use {'stevearc/vim-vscode-snippets'}
end)
```

</details>

<details>
  <summary>Paq</summary>

```lua
require "paq" {
    {'stevearc/vim-vscode-snippets'};
}
```

</details>

<details>
  <summary>vim-plug</summary>

```vim
Plug 'stevearc/vim-vscode-snippets'
```

</details>

<details>
  <summary>dein</summary>

```vim
call dein#add('stevearc/vim-vscode-snippets')
```

</details>

<details>
  <summary>Pathogen</summary>

```sh
git clone --depth=1 https://github.com/stevearc/vim-vscode-snippets.git ~/.vim/bundle/
```

</details>

<details>
  <summary>Neovim native package</summary>

```sh
git clone --depth=1 https://github.com/stevearc/vim-vscode-snippets.git \
  "${XDG_DATA_HOME:-$HOME/.local/share}"/nvim/site/pack/vim-vscode-snippets/start/vim-vscode-snippets
```

</details>

## Languages

- c - [vscode-cpp-snippets](https://github.com/one-harsh/vscode-cpp-snippets.git)
- cpp - [vscode-cpp-snippets](https://github.com/one-harsh/vscode-cpp-snippets.git)
- csharp - [vscode-csharp-snippets](https://github.com/J0rgeSerran0/vscode-csharp-snippets.git), [vscode-unity-code-snippets](https://github.com/kleber-swf/vscode-unity-code-snippets.git)
- erb - [vscode-ruby](https://github.com/rubyide/vscode-ruby.git)
- go - [vscode-go](https://github.com/golang/vscode-go.git)
- groovy - [vscode](https://github.com/microsoft/vscode.git)
- html - [php-awesome-snippets](https://github.com/h4kst3r/php-awesome-snippets.git), [vscode-javascript](https://github.com/xabikos/vscode-javascript.git)
- javascript - [vscode-es7-javascript-react-snippets](https://github.com/dsznajder/vscode-es7-javascript-react-snippets.git), [vscode](https://github.com/microsoft/vscode.git), [vscode-javascript](https://github.com/xabikos/vscode-javascript.git)
- lua - [vsc-lua](https://github.com/keyring/vsc-lua.git)
- markdown - [vscode](https://github.com/microsoft/vscode.git)
- php - [php-awesome-snippets](https://github.com/h4kst3r/php-awesome-snippets.git), [vscode](https://github.com/microsoft/vscode.git)
- python - [vscode-python-snippet-pack](https://github.com/ylcnfrht/vscode-python-snippet-pack.git)
- ruby - [vscode-ruby](https://github.com/rubyide/vscode-ruby.git)
- rust - [vscode-rust](https://github.com/rust-lang/vscode-rust.git)
- swift - [vscode](https://github.com/microsoft/vscode.git)
- typescript - [vscode-es7-javascript-react-snippets](https://github.com/dsznajder/vscode-es7-javascript-react-snippets.git), [vscode](https://github.com/microsoft/vscode.git), [vscode-javascript](https://github.com/xabikos/vscode-javascript.git)
- vb - [vscode](https://github.com/microsoft/vscode.git)
- vue - [vscode-javascript](https://github.com/xabikos/vscode-javascript.git)

## Contributing

All snippets are generated programmatically. To add new extensions:

- Edit `sources.json`
- Run the `build.py` script (requires `pip install json5`)
- Open a pull request

## License

The build script and all other code unique to this repository are under the MIT
license (see LICENSE file). All snippets are under the specific license of their
source repository. Each of these is in a subdirectory under `snippets/`, and
their applicable license(s) are present in that subdirectory.
