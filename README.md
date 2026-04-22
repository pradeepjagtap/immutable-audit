# Immutable File Scanner for RHEL

## Overview

This script scans all real filesystems on a system to detect files with the immutable (`+i`) attribute set and reports their RPM ownership.

It is useful during troubleshooting scenarios where files cannot be modified or deleted due to the immutable bit.

---

## Features

- Detects real mounted filesystems using `findmnt`
- Skips pseudo and network filesystems (like `proc`, `sysfs`, `nfs`, etc.)
- Recursively scans files using `lsattr`
- Identifies files with immutable (`+i`) attribute
- Checks RPM ownership for each file
- Generates:
  - List of immutable files
  - Ownership report

---

## Requirements

- RHEL / CentOS / Rocky / AlmaLinux
- Python 3
- `findmnt` (from util-linux)
- `lsattr` (from e2fsprogs)
- `rpm`

---

## Files Generated

| File Name                | Description                          |
|-------------------------|--------------------------------------|
| `immutable_list.txt`    | List of immutable files              |
| `immutable_report.txt`  | Immutable files with RPM ownership   |

---

## Usage

### 1. Make script executable

```
chmod +x immutable_scan.py
```

### 2. Run Scan Only
Scans all filesystems and lists immutable files:

```
./immutable_scan.py --scan
```

### 3. Generate Report Only
Uses existing immutable_list.txt to generate RPM ownership report:
```
./immutable_scan.py --report
```

### 4. Run Full Workflow
Performs scan + report in one go:
```
./immutable_scan.py --all
```
---

## Example Output
#### immutable_list.txt
```
/etc/passwd
/var/log/secure
```
#### immutable_report.txt
```
/etc/passwd -> immutable -> setup-2.12.2-7.el9.noarch
/var/log/secure -> immutable -> file /var/log/secure is not owned by any package
```

## How It Works
### Filesystem Detection
Uses:
```
findmnt -rn -o TARGET,FSTYPE
```

Filters out:
- Pseudo filesystems (proc, sysfs, etc.)
- Network filesystems (nfs, cifs)
- Known system mount points (/proc, /sys, /dev, /run)
---

## Immutable File Detection
- Uses:
```
lsattr -R <mountpoint>
```
- Checks for i flag in output.
---

## RPM Ownership Check
Uses:
```
rpm -qf <file>
```
Handles:
- Owned files
- Unowned files
- Errors gracefully
---
## Notes
- Script may take time on large filesystems
- Some permission errors are expected and ignored
- Run as root for best results
  
