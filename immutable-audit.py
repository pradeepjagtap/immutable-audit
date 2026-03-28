#!/usr/bin/env python3

import argparse
import subprocess
import os
import sys

IMMUTABLE_LIST = "immutable_list.txt"
REPORT_FILE = "immutable_report.txt"
SKIP_FS_TYPES = {
    "proc", "sysfs", "tmpfs", "devtmpfs", "devpts", "overlay", "autofs", "mqueue", "rpc_pipefs", "cgroup", "cgroup2", 
    "pstore", "debugfs", "securityfs", "hugetlbfs", "fusectl", "configfs", "binfmt_misc", "fuse.lxcfs", "fuse.snapd", 
    "fuse.gvfsd-fuse", "tracefs", "nfs", "nfs4","cifs", "smb3"
}

SKIP_MOUNTPOINTS = {"/proc", "/sys", "/dev", "/run"}

def get_filesystems():
    """
    Get all real filesystems from findmnt, skipping pseudo filesystems and unwanted mount points.
    Returns a list of unique mount points.
    """
    try:
        result = subprocess.run([
            "findmnt", "-rn", "-o", "TARGET,FSTYPE"
        ], capture_output=True, check=True, encoding="utf-8")
        mount_points = set()
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            try:
                target, fstype = line.strip().split()
            except ValueError:
                continue  # skip malformed lines
            if (fstype in SKIP_FS_TYPES) or (target in SKIP_MOUNTPOINTS):
                continue
            mount_points.add(target)
        return sorted(mount_points)
    except Exception as e:
        print(f"Error getting filesystems: {e}", file=sys.stderr)
        return []

def scan_immutable_files(mount_points, output_file):
    """
    Scan given mount points with lsattr recursively to find files with +i (immutable) bit set.
    Write full paths to output_file.
    """
    found = set()
    with open(output_file, "w") as outf:
        for mp in mount_points:
            # Use lsattr -dR
            try:
                # Note: lsattr prints errors on stderr per unreadable files, which is fine
                proc = subprocess.Popen(
                    ["lsattr", "-R", mp],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    universal_newlines=True
                )
                for line in proc.stdout:
                    parts = line.strip().split(maxsplit=1)
                    if len(parts) != 2:
                        continue
                    attrs, path = parts
                    if 'i' in attrs:
                        # The colon is for directories when recursively descending
                        abs_path = path
                        if not os.path.isabs(abs_path):
                            try:
                                abs_path = os.path.abspath(abs_path)
                            except Exception:
                                pass
                        if abs_path not in found:
                            # Confirm the file exists (it might have been deleted since lsattr output)
                            if os.path.exists(abs_path):
                                outf.write(f"{abs_path}\n")
                                found.add(abs_path)
                proc.stdout.close()
                proc.wait()
            except Exception:
                # ignore and continue on error
                continue

def check_rpm_ownership(immutable_file, report_file):
    """
    Given a file with a list of immutable files, check which RPM owns each, writing results to report_file.
    """
    if not os.path.exists(immutable_file):
        print(f"Cannot find {immutable_file}!", file=sys.stderr)
        return

    with open(immutable_file, "r") as inf, open(report_file, "w") as outf:
        for line in inf:
            path = line.strip()
            if not path: continue
            try:
                rpm_proc = subprocess.run(
                    ["rpm", "-qf", path],
                    capture_output=True,
                    encoding="utf-8"
                )
                if rpm_proc.returncode == 0:
                    rpm_pkg = rpm_proc.stdout.strip()
                else:
                    # Example output: "file <file> is not owned by any package"
                    rpm_pkg = (
                        rpm_proc.stdout.strip() 
                        or rpm_proc.stderr.strip()
                        or "Unknown error"
                    )
            except Exception:
                rpm_pkg = "Not owned by RPM"
            outf.write(f"{path} -> immutable -> {rpm_pkg}\n")

def main():
    parser = argparse.ArgumentParser(
        description="Scan system for files with the immutable bit set and report their RPM ownership."
    )
    parser.add_argument("--scan", action="store_true", help="Scan all filesystems for immutable files.")
    parser.add_argument("--report", action="store_true", help="Generate RPM ownership report for immutable files.")
    parser.add_argument("--all", action="store_true", help="Run full workflow: scan and then report.")

    args = parser.parse_args()

    if not (args.scan or args.report or args.all):
        parser.print_help()
        sys.exit(1)

    if args.scan or args.all:
        print("[*] Detecting real filesystems...")
        mps = get_filesystems()
        print(f"[*] Found {len(mps)} real mount points.")
        print(f"[*] Scanning for immutable files (this may take a while)...")
        scan_immutable_files(mps, IMMUTABLE_LIST)
        print(f"[*] List of immutable files written to {IMMUTABLE_LIST}")

    if args.report or args.all:
        print(f"[*] Generating RPM ownership report in {REPORT_FILE} ...")
        check_rpm_ownership(IMMUTABLE_LIST, REPORT_FILE)
        print(f"[*] Complete. See {REPORT_FILE} for results.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)