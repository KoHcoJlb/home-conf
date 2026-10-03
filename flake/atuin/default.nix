{ atuin }:

atuin.overrideAttrs (old: {
  patches = (old.patches or [ ]) ++ [ ./preserve-selection.patch ];
})
