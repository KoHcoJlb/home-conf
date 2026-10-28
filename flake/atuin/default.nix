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
    "--skip=the_proxy_titles_the_terminal_after_the_program_in_the_foreground" # pty-proxy
    "--skip=piped_input_runs_through_the_shell_and_then_ends_it" # pty-proxy
  ];

  patches = (old.patches or [ ]) ++ [ ./preserve-selection.patch ];
})
