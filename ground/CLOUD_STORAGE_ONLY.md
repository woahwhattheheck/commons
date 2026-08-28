# Commons cloud-storage-only route

Owner directive: Slack `1787859008.848189` and `1787859050.913049`.

GitHub and connected cloud storage are the Commons control plane. The owner's
machine is not a mirror, build farm, post archive, clone farm, or agent-worktree
cache. Do not create a new local Commons clone, worktree, transcript mirror,
post mirror, build tree, package cache, generated archive, or duplicate object
store there. Run new agent work in ephemeral cloud environments and land unique
results through GitHub.

Existing local bytes are source evidence. They are frozen against destructive
cleanup until their exact contents have completed this sequence:

1. `LOCAL_PRESENT`
2. `MANIFESTED` with byte count and SHA-256
3. `CLOUD_PRESENT`
4. `HASH_VERIFIED` by cloud readback
5. `LOCAL_RELEASE_ELIGIBLE`

Eligibility is not deletion. No Commons agent may delete, move, prune, garbage
collect, overwrite, or dehydrate the owner's local copy under this procedure.
Only the owner may perform a later local release after reviewing the verified
receipt. A missing, unreadable, interrupted, or mismatched object remains local.

The copy-only tool is `host/commons_cloud_evacuation.py`. It hashes files in
place, maps identical content to one cloud object, uploads with `rclone copyto
--immutable`, reads every object back, and publishes the manifest last. It has
no deletion command.

The connected Google Drive destination for this recovery is:

- folder: `Commons no-loss cloud evacuation 2026-08-27`
- object id: `1-JRV7orDPtr0_vXZwwodFGh8da02o0eF`
- parent cloud substrate: `1c-0rFoyVvGwOSjLLlVrPRphRvaAFtkSY`

An Oracle Always Free expansion carrier is integrated at
`infra/oracle_always_free/`. It encodes Oracle's current 2-OCPU / 12-GB Arm
shape and documented 50-GB boot + 150-GB attached-volume layout. Its current
truth state is `READY_NOT_PROVISIONED`: the stack and tests are landed, but no
OCI tenancy is connected to this session and no Oracle VM or cloud byte is
claimed. When provisioned, `/srv/commons-cloud/evacuation` is an additional
copy target; it does not replace the connected Drive destination or relax any
hash-readback requirement.

Example for an already configured Google Drive `rclone` remote:

```powershell
python host/commons_cloud_evacuation.py stage `
  C:\Users\lucys\.cursor\worktrees `
  C:\Users\lucys\.claude\worktrees `
  C:\Users\lucys\Desktop\commons `
  --remote "gdrive:Commons no-loss cloud evacuation 2026-08-27" `
  --output -
```

The receipt is valid only when `cloud_complete=true`, every object state is
`HASH_VERIFIED`, and `local_release_performed=false`. Do not redirect the
receipt to the full local disk; stream it to a cloud carrier or the caller.

Ephemeral cloud-current working copies (new agent work, not owner-disk
mirrors) are opened with `python3 host/cloud_current_worktree.py open`.
That road composes with this freeze; it does not create clones on Bryce's
machine and it does not replace this copy-only evacuation.
[CLOUD_CURRENT.md](./CLOUD_CURRENT.md).
