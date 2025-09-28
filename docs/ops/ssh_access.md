# Safe SSH access for Home Assistant host

This document explains the recommended, minimal, and safe way to SSH into the Home Assistant host for operational tasks used by developers and operators of the HA BB-8 add-on.

Important: do NOT store plaintext credentials in the repository. Use SSH keys and local OS key-agent forwarding when possible.

Recommended workflow

- Create an SSH keypair locally (if you don't already have one):

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

- Add your public key to the Home Assistant host `authorized_keys` for the appropriate user (e.g., `hass` or `root` depending on your environment). Use the Supervisor UI or the platform's recommended method.

- Create a short SSH alias in your `~/.ssh/config`:

```ssh-config
Host hass
  HostName <home-assistant-ip-or-hostname>
  User hass
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
  ForwardAgent yes
```

- Use the alias when running operational scripts that require SSH, e.g.:

```bash
./ops/diag/collect_ha_bb8_diagnostics.sh hass
```

Security notes
- Do not commit private keys to Git.
- If you need to share access, prefer adding public keys on the host and removing them when access is no longer needed.
- For automated CI-run diagnostics, use a dedicated, limited-scope credential and store it in the CI secrets manager.

Audit & revocation
- Periodically verify `authorized_keys` on the host and remove stale keys.
- Keep a log of who has shell access and for what reason.
