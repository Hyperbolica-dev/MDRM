# Private remote access

The supported first deployment is a single owner using a service running on their own computer. GitHub Pages is a static entry point, not the Python host. The companion blog entry at `/tools/mrdm/` accepts a private HTTPS Tailscale address, stores it only in the current browser, and embeds the app without replacing the blog page.

## Connection boundary

- Verify the existing MRDM port and service working directory before forwarding it.
- Use Tailscale Serve over HTTPS, accessible only inside the private tailnet. Do not use public Funnel.
- All accessing devices must be authenticated to the owner's tailnet. Restrict tailnet access before adding other users; this version does not isolate data between people sharing the service.
- Keep CSV records, SQLite medication journals, UI settings, keys, backups and private study outputs on the service computer, outside Git.
- The computer must remain awake, connected and running MRDM. A blog link cannot start an offline computer.

For an existing MRDM instance at localhost port 8501, after account-side HTTPS Serve is enabled:

```sh
tailscale serve --bg --https=8443 http://127.0.0.1:8501
tailscale serve status
```

Enter the resulting HTTPS address once in the blog entry. Public source code must not contain the actual private hostname. A separate-window fallback is available if browser embedding policy blocks the frame. Local startup should bind loopback when reverse-proxied; this does not imply a restart of an existing running service.

## Login and network switching

If Tailscale login requires a proxy, keep the original login page open and obtain the verification code through another trusted device or network that has proxy access. Do not put personal account or network details in public documentation.

For proxy-first use on iOS, see [manual Shortcuts switching](../ios_shortcuts_network_switching.md).

## Future multi-user service

Before allowing multiple people, add application authentication, owner checks on every data operation, per-user storage, restricted exports and backup separation. A shared personal CSV plus a login screen is insufficient. No public registration or multi-user access is enabled by this release.

## Release boundary

Code and generic documentation can be pushed after review. Personal records, private addresses, keys, local statistics and pre-redaction history bundles remain ignored. Rewriting historical emails changes commit and annotated tag hashes; publishing rewritten main and historical tags requires an explicit coordinated force-with-lease push, separate from an ordinary release push.
