from sbm.utils.tracker import _read_tracker, _write_tracker, process_pending_syncs


def force_sync():
    data = _read_tracker()
    runs = data.get("runs", [])
    count = 0
    for run in runs:
        # Reset sync_status if it was invalid_slug or pending and command is backfill_recovery
        if run.get("command") == "backfill_recovery":
            if run.get("sync_status") in ["invalid_slug", "validation_unavailable", "pending_sync"]:
                run["sync_status"] = "pending_sync"  # Ensure it's pending
                count += 1

    if count > 0:
        _write_tracker(data)
        print(f"Reset {count} backfill runs to pending_sync. Processing...")
        process_pending_syncs()
        print("Sync complete.")
    else:
        print("No runs needed reset.")


if __name__ == "__main__":
    force_sync()
