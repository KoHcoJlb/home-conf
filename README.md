`sh <(curl https://igor.kiev.ua/chezmoi.sh)`

## Updates

`update.zsh` applies `origin/master` only when its tip has a valid SSH
signature from a key in the local checkout's `allowed_signers`. Unsigned tips
and invalid or untrusted signatures fail the update.

## Hydra

The flake exposes `hydraJobs.aarch64-linux.homeEnv` and
`hydraJobs.x86_64-linux.homeEnv`, covering the home environment and its
dependencies from `packages.nix`.

The existing Hydra instance must have `use-substitutes = 1` and
`https://cache.nixos.org` configured as a substituter to reuse cached outputs
and build only missing ones. Cache availability is checked at build time.

Create an enabled Hydra jobset with:

- **Type:** Flake
- **Flake URI:** `github:KoHcoJlb/home-conf?dir=flake`
- **Check interval:** 300 seconds
- **Scheduling shares:** 1

Hydra reads `hydraJobs` automatically. Machine-local `flake/local.nix`
customizations are only included if available in the jobset's source.

Evaluate the Linux jobs locally without building:

```sh
nix eval --json ./flake#hydraJobs --apply 'builtins.mapAttrs (_: jobs: builtins.mapAttrs (_: drv: drv.drvPath) jobs)'
```
