#!/usr/bin/env python3
"""Three unchanged solver lanes, official validation, atomic best-feasible output.

New portfolio orchestration by TokenJunkieLabs contributors. Solvers retain their
own attribution. The independent official checker supplies the ranked objective.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

from compare_checker import compare, load_result


def number(name, default, minimum):
    value = float(os.environ.get(name, default))
    if not math.isfinite(value) or value < minimum:
        raise ValueError(f"{name} must be finite and >= {minimum}")
    return value


def atomic_write(path, data):
    # Same-directory replacement means a killed process leaves the old complete
    # solution or the new complete solution, never a partially overwritten one.
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def launch(command, env, stdout, stderr):
    options = {"env": env, "stdout": stdout, "stderr": stderr, "stdin": subprocess.DEVNULL}
    if os.name == "posix":
        options["start_new_session"] = True
    elif os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    return subprocess.Popen(command, **options)


def stop_process(process, force=False):
    if process is None:
        return
    try:
        if os.name == "posix":
            # launch() owns a new session/group, not only its leader. A leader
            # may exit before its descendants or during the TERM grace period.
            if getattr(process, "_portfolio_group_closed", False):
                return
            os.killpg(process.pid, signal.SIGKILL if force else signal.SIGTERM)
            if force:
                process._portfolio_group_closed = True
        elif process.poll() is None:
            if force:
                process.kill()
            else:
                # Windows is a development harness. TerminateProcess cannot
                # emulate the C++ SIGTERM checkpoint or POSIX group cleanup.
                process.terminate()
    except ProcessLookupError:
        # Do not later signal a new group that reuses this retired group ID.
        if os.name == "posix":
            process._portfolio_group_closed = True


class Supervisor:
    def __init__(self, inputs, output):
        self.start = time.monotonic()
        self.inputs = inputs
        self.output = output
        self.root = Path(__file__).resolve().parent
        self.total = number("PORTFOLIO_SECONDS", 585, 2)
        self.reserve = min(20.0, self.total * 0.12)
        self.search_seconds = self.total - self.reserve
        self.deadline = self.start + self.total
        self.search_deadline = self.start + self.search_seconds
        self.stop_grace = min(2.0, self.reserve / 4)
        self.interval = number("PORTFOLIO_CHECK_INTERVAL", min(15.0, self.total / 10), 0.05)
        self.check_timeout = number("PORTFOLIO_CHECK_TIMEOUT", min(90.0, self.total), 0.1)
        self.work = Path(tempfile.mkdtemp(prefix="roadef-portfolio-", dir=os.environ.get("PORTFOLIO_ARTIFACTS")))
        self.receipt = Path(os.environ.get("PORTFOLIO_RECEIPT", str(output) + ".portfolio.json")).resolve()
        if self.receipt == output or self.receipt in inputs:
            raise ValueError("Receipt must not overwrite the solution or an input")
        self.lanes = []
        self.check = None
        # Retain only digests of previously judged solutions. Keeping every full
        # Decimal vector would grow memory with run duration on large instances.
        self.cache = set()
        self.failed_checks = {}
        self.exhausted_checks = set()
        self.best = None
        self.best_digest = None
        self.pending_baseline = self.work / "baseline.json"
        self.pending_baseline.write_bytes(b'{"srpaths":[]}\n')
        self.next_lane = 0
        self.stopping_at = None
        self.signal_received = None
        self.signal_deadline_applied = False
        self.events = []
        self.checker = self.executable("CHECKER", "checker")
        self.checker_sha256 = None
        self.input_hashes = None
        self.peak_sampled_rss_kib = None
        self.next_rss_sample = self.start

    def executable(self, setting, name):
        default = self.root / "bin" / (name + (".exe" if os.name == "nt" else ""))
        return Path(os.environ.get("PORTFOLIO_" + setting, default)).resolve()

    def emit(self, event, **fields):
        record = {"event": event, "elapsed_seconds": round(time.monotonic() - self.start, 4), **fields}
        self.events.append(record)
        print(json.dumps(record, default=str), file=sys.stderr, flush=True)

    def save_receipt(self, status):
        record = {"status": status, "validated": self.best is not None,
                  "solution_sha256": self.best_digest,
                  "comparison": "official checker six-decimal descending saturation vector",
                  "cost_used_in_ranking": False, "checker_sha256": self.checker_sha256,
                  "input_sha256": self.input_hashes,
                  "peak_sampled_process_rss_kib": self.peak_sampled_rss_kib,
                  "memory_measurement": "Linux /proc RSS sum sampled every 0.5s; excludes page cache; not a hard bound",
                  "wall_seconds": round(time.monotonic() - self.start, 4),
                  "search_allowance_seconds": self.search_seconds,
                  "deadline_seconds": self.total, "signal_received": self.signal_received,
                  "artifacts": str(self.work), "events": self.events,
                  "lanes": [{"name": lane["name"], "executable": str(lane["executable"]),
                             "source_binary_sha256": lane.get("binary_sha256"),
                             "returncode": lane["process"].poll() if lane.get("process") else None}
                            for lane in self.lanes]}
        if self.best is not None:
            record.update(selected_lane=self.best["lane"],
                          selected_checker_sha256=self.best["sha256"],
                          load_count=len(self.best["vector"]),
                          maximum_load=str(self.best["vector"][0]),
                          total_cost_diagnostic=self.best.get("total_cost"))
        atomic_write(self.receipt, (json.dumps(record, indent=2, default=str) + "\n").encode())

    def sample_rss(self):
        if not sys.platform.startswith("linux") or time.monotonic() < self.next_rss_sample:
            return
        self.next_rss_sample = time.monotonic() + 0.5
        pids = [os.getpid()]
        pids.extend(lane["process"].pid for lane in self.lanes
                    if lane.get("process") is not None and lane["process"].poll() is None)
        if self.check is not None and self.check["process"].poll() is None:
            pids.append(self.check["process"].pid)
        total = 0
        for pid in pids:
            try:
                for line in Path(f"/proc/{pid}/status").read_text().splitlines():
                    if line.startswith("VmRSS:"):
                        total += int(line.split()[1])
                        break
            except (OSError, ValueError):
                pass  # A child may exit between the poll and status read.
        self.peak_sampled_rss_kib = max(total, self.peak_sampled_rss_kib or 0)

    def signal_handler(self, signum, frame):
        # No file or process work inside the signal handler. The polling loop
        # notices this within 0.1 seconds even while a checker is running.
        self.signal_received = signum

    def begin_stop(self, reason):
        if self.signal_received is not None and not self.signal_deadline_applied:
            # Apply an external signal's deadline even if normal budget draining
            # has already begun. Repeated signals never extend that deadline.
            self.deadline = min(self.deadline, time.monotonic() + 7)
            self.signal_deadline_applied = True
        if self.stopping_at is not None:
            return
        self.stopping_at = time.monotonic()
        for lane in self.lanes:
            stop_process(lane.get("process"))
        self.emit("stopping", reason=reason)

    def start_lanes(self):
        base_env = dict(os.environ)
        for key in ("SEDGE_STATS", "SEDGE_MAX_ROUNDS", "CLOUD_INITIAL_SOLUTION"):
            base_env.pop(key, None)
        # Do not inherit an unrelated diagnostic budget or threading setting.
        base_env.update(SEDGE_SECONDS=str(self.search_seconds), OMP_NUM_THREADS="1",
                        OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
        for name in ("sedge", "flora", "candidate"):
            executable = self.executable(name.upper(), name)
            lane = {"name": name, "executable": executable, "process": None,
                    "solution": self.work / (name + ".json"), "last_digest": None,
                    "next_check": self.start, "log": None, "final_checked": False,
                    "retry_snapshot": None, "read_failures": 0}
            self.lanes.append(lane)
            try:
                lane["binary_sha256"] = hashlib.sha256(executable.read_bytes()).hexdigest()
                lane["log"] = (self.work / (name + ".log")).open("wb")
                lane["process"] = launch([str(executable), *map(str, self.inputs), str(lane["solution"])],
                                         base_env, lane["log"], lane["log"])
                self.emit("lane_started", lane=name, pid=lane["process"].pid)
            except OSError as error:
                self.emit("lane_start_failed", lane=name, error=str(error))

    def accept(self, result, snapshot, digest, lane):
        if not result["valid"]:
            self.emit("candidate_invalid", lane=lane, solution_sha256=digest)
            return
        if self.best is not None and compare(result, self.best)["winner"] != "left":
            return
        # Strictly improving validated vectors only. Equal vectors keep the
        # incumbent regardless of total_cost, source lane, or file size.
        atomic_write(self.output, snapshot.read_bytes())
        self.best = dict(result, lane=lane)
        self.best_digest = digest
        self.emit("incumbent_improved", lane=lane, solution_sha256=digest,
                  maximum_load=str(result["vector"][0]), load_count=len(result["vector"]))
        self.save_receipt("running")

    def enqueue(self, path, lane):
        try:
            raw = path.read_bytes()
        except (OSError, ValueError) as error:
            if isinstance(lane, dict):
                ended = lane["process"] is None or lane["process"].poll() is not None
                if ended:
                    lane["read_failures"] += 1
                    if lane["read_failures"] >= 2:
                        lane["final_checked"] = True
                        self.emit("final_checkpoint_unreadable", lane=lane["name"], error=str(error), attempts=2)
            return False
        digest = hashlib.sha256(raw).hexdigest()
        if isinstance(lane, dict):
            lane["read_failures"] = 0
            lane_name = lane["name"]
        else:
            lane_name = lane
        snapshot = self.work / (digest + ".solution.json")
        if digest in self.cache or digest in self.exhausted_checks:
            # The public incumbent only improves, so a previously evaluated
            # solution cannot newly outrank it. No score-vector cache is needed.
            if isinstance(lane, dict):
                lane["last_digest"] = digest
                lane["retry_snapshot"] = None
                ended = lane["process"] is None or lane["process"].poll() is not None
                # An old retried snapshot is not necessarily the lane's final
                # output. Read the live output in the next scheduling pass.
                if ended and path == lane["solution"]:
                    lane["final_checked"] = True
            return False
        # Solvers atomically rename their own output. Read its complete inode,
        # then freeze those exact bytes so validation cannot race with updates.
        snapshot.write_bytes(raw)
        stdout_path = self.work / (digest + ".checker-6.json")
        stderr_path = self.work / (digest + ".checker.log")
        stdout, stderr = stdout_path.open("wb"), stderr_path.open("wb")
        check = {"stdout": stdout, "stderr": stderr,
                 "result": stdout_path, "snapshot": snapshot, "digest": digest,
                 "lane": lane_name, "lane_ref": lane if isinstance(lane, dict) else None,
                 "started": time.monotonic()}
        try:
            command = [str(self.checker), "--net", str(self.inputs[0]), "--tm", str(self.inputs[1]),
                       "--scenario", str(self.inputs[2]), "--srpaths", str(snapshot),
                       "--max-decimal-places", "6"]
            process = launch(command, dict(os.environ, OMP_NUM_THREADS="1"), stdout, stderr)
        except OSError as error:
            stdout.close()
            stderr.close()
            self.retry_check(check, str(error), 0)
            return False
        self.check = dict(check, process=process)
        return True

    def retry_check(self, check, error, elapsed):
        digest = check["digest"]
        failures = self.failed_checks.get(digest, 0) + 1
        self.failed_checks[digest] = failures
        lane = check["lane_ref"]
        self.emit("check_rejected", lane=check["lane"], error=error,
                  checker_seconds=round(elapsed, 4), attempts=failures,
                  solution_sha256=digest)
        if failures < 2:
            # Retry the same frozen bytes once, independent of whether the lane
            # has exited or already produced a different live checkpoint.
            if lane is None:
                self.pending_baseline = check["snapshot"]
            else:
                lane["retry_snapshot"] = check["snapshot"]
                lane["next_check"] = time.monotonic()
            self.emit("check_retry_queued", lane=check["lane"], solution_sha256=digest)
        else:
            self.exhausted_checks.add(digest)
            if lane is not None:
                lane["retry_snapshot"] = None
                lane["next_check"] = time.monotonic()
            self.emit("check_retries_exhausted", lane=check["lane"], solution_sha256=digest)

    def poll_checker(self):
        if self.check is None:
            return
        check = self.check
        elapsed = time.monotonic() - check["started"]
        if check["process"].poll() is None and elapsed < self.check_timeout:
            return
        timed_out = check["process"].poll() is None
        # Retire the checker group before dropping its handle, including when
        # its leader has returned but a descendant still holds the log files.
        stop_process(check["process"], force=True)
        if timed_out:
            check["process"].wait(timeout=1)
        check["stdout"].close()
        check["stderr"].close()
        self.check = None
        try:
            if timed_out:
                raise ValueError("checker timeout")
            result = load_result(check["result"])
            # The official checker returns a nonzero status for infeasibility.
            # A well-formed valid:false report is a conclusive rejection, while
            # a crash/malformed result or inconsistent valid:true gets a retry.
            if check["process"].returncode != 0 and result["valid"]:
                raise ValueError(f"checker exit {check['process'].returncode} with valid:true")
            self.accept(result, check["snapshot"], check["digest"], check["lane"])
            self.cache.add(check["digest"])
            if check["lane_ref"] is not None:
                check["lane_ref"]["last_digest"] = check["digest"]
                check["lane_ref"]["retry_snapshot"] = None
            self.emit("check_completed", lane=check["lane"], valid=result["valid"],
                      checker_seconds=round(elapsed, 4), solution_sha256=check["digest"])
        except (ValueError, KeyError, TypeError, OSError) as error:
            self.retry_check(check, str(error), elapsed)

    def schedule_check(self):
        if self.check is not None:
            return
        if self.pending_baseline is not None:
            path, self.pending_baseline = self.pending_baseline, None
            if self.enqueue(path, "zero_change_baseline"):
                return
        now = time.monotonic()
        for offset in range(len(self.lanes)):
            i = (self.next_lane + offset) % len(self.lanes)
            lane = self.lanes[i]
            ended = lane["process"] is None or lane["process"].poll() is not None
            if lane["final_checked"] or (not ended and now < lane["next_check"]):
                continue
            lane["next_check"] = now + self.interval
            if self.enqueue(lane["retry_snapshot"] or lane["solution"], lane):
                self.next_lane = (i + 1) % len(self.lanes)
                return

    def run(self):
        # The empty solution has no route changes. Reachability still requires
        # the official check; receipt never labels this provisional file valid.
        atomic_write(self.output, self.pending_baseline.read_bytes())
        self.emit("provisional_zero_change_checkpoint")
        self.save_receipt("unvalidated_fallback")
        self.checker_sha256 = hashlib.sha256(self.checker.read_bytes()).hexdigest()
        self.input_hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in self.inputs}
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self.signal_handler)
        run_error = None
        try:
            self.start_lanes()
            while time.monotonic() < self.deadline:
                now = time.monotonic()
                if self.signal_received is not None:
                    self.begin_stop("signal")
                elif now >= self.search_deadline:
                    self.begin_stop("search_budget")
                if self.stopping_at is not None and now >= self.stopping_at + self.stop_grace:
                    for lane in self.lanes:
                        stop_process(lane.get("process"), force=True)
                self.poll_checker()
                self.schedule_check()
                self.sample_rss()
                if (self.pending_baseline is None and self.check is None and
                        all(lane["final_checked"] for lane in self.lanes)):
                    break
                time.sleep(0.1)
        except BaseException as error:
            run_error = error
            raise
        finally:
            for lane in self.lanes:
                stop_process(lane.get("process"), force=True)
            if self.check is not None:
                stop_process(self.check["process"], force=True)
            # One shared, bounded reap window; never multiply the deadline by
            # the number of lanes. All child groups have already been killed.
            reap_deadline = time.monotonic() + 0.5
            processes = [lane.get("process") for lane in self.lanes]
            if self.check is not None:
                processes.append(self.check["process"])
            for process in processes:
                if process is not None:
                    try:
                        process.wait(timeout=max(0, reap_deadline - time.monotonic()))
                    except subprocess.TimeoutExpired:
                        pass
            if self.check is not None:
                self.check["stdout"].close()
                self.check["stderr"].close()
            for lane in self.lanes:
                if lane.get("log"):
                    lane["log"].close()
            if run_error is None:
                self.save_receipt("complete" if self.best is not None else "no_validated_solution")
            else:
                # A feasible incumbent and a successfully finished search are
                # different facts. Preserve the former without asserting both.
                # Diagnostics must not replace the exception already escaping.
                try:
                    self.emit("supervisor_failed", error_type=type(run_error).__name__)
                except BaseException:
                    pass
                try:
                    self.save_receipt("error")
                except BaseException:
                    pass  # The last atomic receipt remains, not a completed run.
        return 0 if self.best is not None else 1


def main():
    if len(sys.argv) != 5:
        print("Usage: supervisor.py network.json traffic.json scenario.json output.json", file=sys.stderr)
        return 2
    inputs = [Path(value).resolve(strict=True) for value in sys.argv[1:4]]
    output = Path(sys.argv[4]).resolve()
    if output in inputs:
        raise ValueError("Output must not overwrite an input")
    if not output.parent.is_dir():
        raise ValueError("Output directory must exist")
    return Supervisor(inputs, output).run()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        print(f"Portfolio error: {error}", file=sys.stderr)
        sys.exit(1)