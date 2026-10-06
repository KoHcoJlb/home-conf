{ atuin }:

atuin.overrideAttrs (old: {
  cargoBuildFeatures = [ "client" ];
  cargoCheckFeatures = [ "client" ];

  # Build and test only the CLI, not every workspace member.
  buildAndTestSubdir = "crates/atuin";

  patches = (old.patches or [ ]) ++ [ ./preserve-selection.patch ];
})
