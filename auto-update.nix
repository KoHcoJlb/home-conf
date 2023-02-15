{ ... }:

{
  programs.zsh.initExtraFirst = ''
  if [[ -z $TMUX ]]
  then
    if ! output=$(home-manager switch 2>&1)
    then
      echo $output
    fi
  fi
  '';
}
