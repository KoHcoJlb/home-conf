{ atuin }:

atuin.overrideAttrs (old: {
  cargoBuildFeatures = [ "client" ];
  cargoCheckFeatures = [ "client" ];

  # Build and test only the CLI, not every workspace member.
  buildAndTestSubdir = "crates/atuin";

  # These upstream tests lack guards for features disabled in this build.
  checkFlags = (old.checkFlags or [ ]) ++ [
    "--skip=key_loads_but_never_generates" # sync
    "--skip=the_proxy_follows_its_shell_between_directories" # pty-proxy
  ];

  patches = (old.patches or [ ]) ++ [ ./preserve-selection.patch ];
})
