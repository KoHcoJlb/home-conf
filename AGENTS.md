# Agent Instructions

## Commit provenance

- Be vigilant about foreign commits, especially unsigned commits and invalid or
  untrusted signatures. Inspect incoming commit ranges and submodule target
  commits before integrating or executing their changes.
- Verify signatures against `allowed_signers` from the existing trusted checkout.
  An author name, email address, or signature header alone is not proof of trust.
- If an incoming commit is unsigned or fails verification, stop integration and
  report its repository, commit hash, and verification result to the user. Do not
  bypass signature checks or silently re-sign foreign changes as trusted work.
- Treat changes to `allowed_signers` as security-sensitive. Never trust an
  incoming signing key merely because the same incoming changes add it to that
  file; obtain the user's explicit confirmation before extending trust.
- Preserve `update.zsh`'s refusal to apply unsigned, invalidly signed, or
  untrusted tips.
