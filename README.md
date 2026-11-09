# ztadd — Zotero Research Paper Importer

`ztadd` is a cross-platform command-line tool that searches Crossref by paper title, retrieves BibTeX metadata using the DOI, converts it into a Zotero item, checks for duplicates, previews the item, and asks before importing it.

## Features

- Search Crossref by bibliographic title.
- Fetch BibTeX using the paper DOI.
- Convert BibTeX fields and creators into Zotero item JSON.
- Support common journal articles, conference papers, books, theses, reports, and other document types.
- Search Zotero for a possible duplicate before creation.
- Preview the item and ask for confirmation.
- Optionally add the item to a Zotero collection by collection key.
- Works on macOS, Linux, and Windows.

## Requirements

- Python 3.9 or newer.
- Git (for installing directly from GitHub).
- A Zotero account and a working `pyzotero` CLI configuration.

This tool delegates Zotero authentication and item creation to the `pyzotero` command-line interface. Configure `pyzotero` and verify that its `search` and `createitem` commands work before using `ztadd`. Follow the current pyzotero documentation for your library ID, library type, and API key. Do not commit or share API keys.

## Install from GitHub with pipx

`pipx` installs the application in an isolated environment and exposes the `ztadd` command.

### macOS

If you use Homebrew:

```bash
brew install pipx
pipx ensurepath
```

Open a new terminal, then:

```bash
pipx install git+https://github.com/codexifyim/ztadd.git
```

### Linux

Install `pipx` using your distribution's package manager or the official pipx installation instructions. For example, on Ubuntu/Debian:

```bash
sudo apt update
sudo apt install pipx
pipx ensurepath
```

Then install:

```bash
pipx install git+https://github.com/codexifyim/ztadd.git
```

If you do not have sudo access, use the pipx installation method documented for your Linux distribution/user environment.

### Windows (PowerShell)

Install Python and Git first. Then:

```powershell
py -m pip install --user pipx
py -m pipx ensurepath
```

Close and reopen PowerShell, then:

```powershell
pipx install git+https://github.com/YOUR_USERNAME/ztadd.git
```

## Usage

Search for a paper:

```bash
ztadd "Attention is all you need"
```

Add to a Zotero collection:

```bash
ztadd "Paper Title" --collection ABC12345
```

`ABC12345` is a placeholder. Use the actual Zotero collection key, not the collection's display name.

The command will search Crossref, fetch and parse BibTeX, check Zotero for a possible duplicate, show a preview, and ask for confirmation before creating the item.

## Updating

For a GitHub installation:

```bash
pipx upgrade zotero-add-cli
```

## Uninstalling

```bash
pipx uninstall zotero-add-cli
```

## Install from a local clone (development)

```bash
git clone https://github.com/codexifyim/ztadd.git
cd ztadd
python -m pip install -e .
```

Then run:

```bash
ztadd "Paper Title"
```

## Troubleshooting

### `ztadd` command not found

Run:

```bash
pipx ensurepath
```

Then open a new terminal. On Windows, reopen PowerShell after running `pipx ensurepath`.

### pyzotero executable not found

Make sure `pyzotero` is installed in the same Python environment used by the `ztadd` installation. Reinstall `ztadd` with pipx after correcting the package configuration.

### Collection not found

The `--collection` argument requires a Zotero collection key, not its visible name.

## Development

```bash
git clone https://github.com/codexifyim/ztadd.git
cd ztadd
python -m venv .venv
```

Activate the environment:

macOS/Linux:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install in editable mode:

```bash
python -m pip install -e .
```

## License

MIT. See [LICENSE](LICENSE).
