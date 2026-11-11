# Roadmap

## Next
- Track the harness figure over time and fail on regression (REPO_RULES
  section 9): a `conformance.json` baseline.
- More of the client in the harness: chat rooms (join, say, part), the hot
  list, instant messages between A and B, browsing a user's files, an upload
  queue with several downloads, a cancelled and a resumed transfer.
- The firewalled path: B behind "I am behind a firewall" (message 500, A
  connects out to B).
- Screenshots: `PrintWindow` hangs on the client's dialogs on a hidden
  desktop; capture from a thread with a timeout, or on offstage at the
  console.

## Then
- Lift the DLLs the client loads at run time: `napgo.dll`, `runwma.dll`,
  `cleanap.dll` and the `vmp3.nvm` / `vwma.nvm` validators (they run natively
  today), and play a generated file through `amp.dll`.
- The 20 instructions `amp.dll`'s decoder uses that lift32 does not
  implement (`int`, `fnstenv`, `fldenv`), before the player is exercised.
- Earlier betas (2.0 beta 7, 1.x) for comparison: the protocol changed (this
  client frames big-endian; the documented protocol is little-endian).

## Out of scope
- Fixing Napster's bugs, security ones included. The point is the original's
  behavior; [SECURITY.md](SECURITY.md) says how it is kept on this machine.
- Connecting to public OpenNap networks, or any server not on `127.0.0.1`.
