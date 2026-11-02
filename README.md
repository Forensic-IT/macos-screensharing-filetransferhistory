# macOS Screen Sharing FileTransferHistory

A small Python parser for `FileTransferHistory` records found in the per-user macOS Screen Sharing preference plist.

Developed by Carlos Mejia-Hernandez at Forensic IT.

Artefact path:

```text
/Users/[USERNAME]/Library/Containers/com.apple.ScreenSharing/Data/Library/Preferences/com.apple.ScreenSharing.plist
```

The script extracts the recorded `FileTransferHistory` values to JSON. It preserves undocumented `direction` and `state` values as recorded rather than assigning meanings that have not been validated.

The artefact was examined on a 14-inch MacBook Pro (2023), Apple M2 Max, running macOS 27.0.1. Behaviour has not been validated across other macOS versions.

## Usage

```bash
python3 screen_sharing_transfer_history.py "/path/to/com.apple.ScreenSharing.plist"
```

Write the output to a new JSON file:

```bash
python3 screen_sharing_transfer_history.py "/path/to/com.apple.ScreenSharing.plist" --output results.json
```

Optional path-only classification can be supplied with both a local and remote root:

```bash
python3 screen_sharing_transfer_history.py "/path/to/com.apple.ScreenSharing.plist" \
  --local-root "/Users/localuser" \
  --remote-root "/Users/remoteuser" \
  --output results.json
```

The path classification describes only where the recorded source and destination paths fall relative to the examiner-supplied roots. It is not an interpretation of Apple's undocumented numeric direction value.

## Interpretation

`FileTransferHistory` records may contain filenames, source and destination paths, byte counters, remote-computer names, and numeric direction/state values.

Paths and byte counters alone do not prove successful completion, receipt, byte identity, ownership, user identity, authorisation, or exact timing. No per-transfer timestamp was present in the examined sample. Undocumented direction and state codes are preserved raw by the parser.

## Sensitive output

The JSON output can reproduce evidentiary filenames, paths, device names and other case data from the source plist. Review generated output before sharing it. Do not publish output produced from case evidence without appropriate sanitisation.

## Existing Screen Sharing parsing

The mac_apt SCREENSHARING plugin already parses saved Screen Sharing connection information. This project focuses on the separate `FileTransferHistory` structure observed in the source plist and does not claim discovery of the existing saved-connection structure.

Public references:

[mac_apt SCREENSHARING plugin source](https://github.com/ydkhatri/mac_apt/blob/master/plugins/screensharing.py)

[mac_apt SCREENSHARING pull request #111](https://github.com/ydkhatri/mac_apt/pull/111)

## Requirements

Python 3. The parser uses Python standard-library modules only.

## Files

`screen_sharing_transfer_history.py` is the parser. No case evidence, source plist or case-derived JSON output is included in this repository.

## Citation

https://doi.org/10.5281/zenodo.23876165
