# Light Modules

Official, independently versioned language and tool modules for [Light IDE](https://github.com/sherhn/Light).

This public repository owns the module sources (`tools/registry_src`), generated manifests, covers and licenses (`registry`), and reproducible release packages. These files were extracted from Light commit `d11bf79`; their MIT license and original third-party attribution are preserved.

## Build and validate

Python 3.12 or newer is required. Existing covers are preserved; Node.js and `sharp` are only needed to redraw them.

```sh
python tools/release_modules.py build
python -m unittest discover -s tools -p test_modules.py
python tools/release_modules.py verify
```

Each module is a ZIP with `module.json`, its resources, `LICENSE` and `THIRD_PARTY_NOTICES.md` at the root. The catalog records its version, minimum IDE version, immutable-version download URL, archive size/SHA-256 and size/SHA-256 of every unpacked file. Published versioned assets must never be replaced; fix an error in a new catalog release.

`dist/light-modules-<catalog-version>.zip` contains the complete offline registry. Light pins its URL and checksum in `modules.lock.json`; its installers keep offline installation available without storing module sources in the IDE repository.

## Publish

Update the changed module's version in `tools/registry_src`, bump `VERSION` for the catalog, rebuild and commit the reviewed index. Push a matching `v<catalog-version>` tag. Actions verifies the generated files and publishes the module packages, catalog, offline registry and `SHA256SUMS.txt` only after validation.

## Your own module

Use the official modules as examples of the `module.json` format. A registry contains `index.json` and the module folders referenced by it. In Light's Modules settings, enter its HTTPS address or select its local folder. Third-party modules can specify commands that run with your user account; only install modules from authors you trust.
