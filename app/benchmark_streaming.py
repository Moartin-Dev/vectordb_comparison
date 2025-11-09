"""
Benchmark Streaming Module - SSE Support for Live Benchmarks
Provides Server-Sent Events endpoints for real-time benchmark progress
"""

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Dict, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from log import logger

# Shared state for active benchmarks
active_benchmarks: Dict[str, Dict] = {}

router = APIRouter(prefix="/benchmark", tags=["benchmark-streaming"])


def count_apis_in_categories(categories: List[str]) -> int:
    """
    Count total number of APIs across specified categories

    Args:
        categories: List of category names (e.g., ["small", "medium"])

    Returns:
        Total number of APIs in those categories
    """
    specs_file = Path("/benchmark/api_specs_list.json")

    if not specs_file.exists():
        logger.warning(f"⚠️  API specs file not found at {specs_file}, returning 0")
        return 0

    try:
        with open(specs_file, 'r') as f:
            specs_data = json.load(f)

        total_apis = 0
        for category in categories:
            if category in specs_data.get('categories', {}):
                specs = specs_data['categories'][category].get('specs', [])
                total_apis += len(specs)
                logger.info(f"📊 Category '{category}': {len(specs)} APIs")
            else:
                logger.warning(f"⚠️  Category '{category}' not found in specs file")

        logger.info(f"✅ Total APIs to benchmark: {total_apis}")
        return total_apis

    except Exception as e:
        logger.error(f"❌ Error reading API specs file: {e}")
        return 0


class BenchmarkStartRequest(BaseModel):
    """Request model for starting a benchmark"""
    runs: int = 3
    categories: List[str] = ["small"]  # small, medium, large


class BenchmarkStartResponse(BaseModel):
    """Response model after starting a benchmark"""
    benchmark_id: str
    status: str
    message: str


@router.post("/start", response_model=BenchmarkStartResponse)
async def start_benchmark(request: BenchmarkStartRequest):
    """
    Start a new benchmark run in the background

    Returns a benchmark_id that can be used to stream results via SSE
    """
    benchmark_id = str(uuid.uuid4())
    logger.info(f"🚀 Starting benchmark {benchmark_id}: {request.runs} runs, categories: {request.categories}")

    # Calculate total expected runs: runs_per_spec × number_of_apis
    api_count = count_apis_in_categories(request.categories)
    total_runs = request.runs * api_count
    logger.info(f"📊 Total expected runs: {request.runs} runs/API × {api_count} APIs = {total_runs} total runs")

    # Initialize benchmark state
    active_benchmarks[benchmark_id] = {
        "status": "running",
        "runs": request.runs,
        "categories": request.categories,
        "started_at": datetime.utcnow().isoformat(),
        "results": [],
        "current_progress": 0,
        "total_runs": total_runs
    }

    # Start benchmark in background
    asyncio.create_task(run_benchmark(benchmark_id, request.runs, request.categories))

    return BenchmarkStartResponse(
        benchmark_id=benchmark_id,
        status="started",
        message=f"Benchmark started with {request.runs} runs for categories: {', '.join(request.categories)}"
    )


async def run_benchmark(benchmark_id: str, runs: int, categories: List[str]):
    """
    Background task that runs the actual benchmark
    Simulates benchmark execution and updates state
    """
    import sys
    import subprocess
    import csv

    benchmark_state = active_benchmarks[benchmark_id]
    logger.info(f"📊 Benchmark {benchmark_id} background task started")

    try:
        # Build command - use path that works in Docker
        import os
        # Check if running in Docker (benchmark mounted at /benchmark)
        if os.path.exists("/benchmark/benchmark.py"):
            benchmark_script = "/benchmark/benchmark.py"
            logger.info(f"✅ Using Docker benchmark script: {benchmark_script}")
        else:
            # Fallback for local development
            benchmark_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "benchmark", "benchmark.py")
            logger.info(f"✅ Using local benchmark script: {benchmark_script}")

        output_file = f"/tmp/benchmark_{benchmark_id}.csv"

        cmd = [
            sys.executable,
            "-u",  # Unbuffered stdout/stderr - WICHTIG für Echtzeit-Progress!
            benchmark_script,
            "--runs", str(runs),
            "--categories", *categories,
            "--output", output_file
        ]

        logger.info(f"🔧 Command: {' '.join(cmd)}")

        # Run benchmark process
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        logger.info(f"⚙️  Subprocess started, PID: {process.pid}")

        # Collect stderr for error logging
        stderr_lines = []

        # Stream output and update progress
        async for line in process.stdout:
            line_str = line.decode().strip()
            logger.info(f"📝 [stdout] {line_str}")

            # Parse structured progress markers
            # Format: [PROGRESS] phase|current_run|total_runs|sub_progress|message
            if line_str.startswith("[PROGRESS]"):
                try:
                    # Parse: "[PROGRESS] phase|current_run|total_runs|sub_progress|message"
                    parts = line_str[10:].strip().split("|", 4)  # Skip "[PROGRESS]"
                    if len(parts) == 5:
                        phase, current_run_str, total_runs_str, sub_progress_str, message = parts
                        current_run = int(current_run_str)
                        total_runs_int = int(total_runs_str)
                        sub_progress = float(sub_progress_str)

                        # Calculate overall progress: (completed_runs + sub_progress_of_current) / total_runs
                        # completed_runs = current_run - 1 (da current_run noch läuft)
                        # overall_progress = (current_run - 1 + sub_progress) / total_runs
                        if total_runs_int > 0:
                            overall_progress_pct = ((current_run - 1 + sub_progress) / total_runs_int) * 100
                        else:
                            overall_progress_pct = 0

                        # Update state
                        benchmark_state["current_progress"] = current_run
                        benchmark_state["sub_progress"] = sub_progress
                        benchmark_state["overall_progress_pct"] = round(overall_progress_pct, 1)
                        benchmark_state["phase"] = phase
                        benchmark_state["last_update"] = datetime.utcnow().isoformat()
                        benchmark_state["last_message"] = message

                        logger.info(f"✅ Progress: {current_run}/{total_runs_int} ({overall_progress_pct:.1f}%) - {phase} - {message}")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to parse progress marker: {line_str} - Error: {e}")

            # Fallback: Legacy marker for backward compatibility
            elif "🔄 Run " in line_str:
                benchmark_state["current_progress"] += 1
                benchmark_state["last_update"] = datetime.utcnow().isoformat()
                benchmark_state["last_message"] = line_str
                logger.info(f"✅ Legacy progress updated: {benchmark_state['current_progress']}/{benchmark_state.get('total_runs', 0)}")

        # Wait for completion and capture stderr
        await process.wait()

        # Read stderr
        stderr_data = await process.stderr.read()
        if stderr_data:
            stderr_text = stderr_data.decode().strip()
            logger.error(f"❌ [stderr] {stderr_text}")
            stderr_lines.append(stderr_text)

        exit_code = process.returncode
        logger.info(f"🏁 Process finished with exit code: {exit_code}")

        if exit_code != 0:
            error_msg = f"Benchmark process exited with code {exit_code}"
            if stderr_lines:
                error_msg += f": {' '.join(stderr_lines)}"
            logger.error(f"❌ {error_msg}")
            benchmark_state["status"] = "failed"
            benchmark_state["error"] = error_msg
            return

        # Load results from CSV
        logger.info(f"📂 Looking for results at: {output_file}")
        if os.path.exists(output_file):
            logger.info(f"✅ Results file found, loading...")
            with open(output_file, 'r') as f:
                reader = csv.DictReader(f)
                results = []
                for row in reader:
                    results.append({
                        'api_name': row['api_name'],
                        'api_category': row['api_category'],
                        'run_number': int(row['run_number']),
                        'num_chunks': int(row['num_chunks']),
                        'embed_ms': float(row['embed_ms']),
                        'pg_write_ms': float(row['pg_write_ms']),
                        'chroma_write_ms': float(row['chroma_write_ms']),
                        'pg_query_ms': float(row['pg_query_ms']),
                        'chroma_query_ms': float(row['chroma_query_ms']),
                        'pg_result_count': int(row['pg_num_results']),  # CSV uses pg_num_results
                        'chroma_result_count': int(row['chroma_num_results']),  # CSV uses chroma_num_results
                        'db_size_pg_mb': float(row['db_size_pg_mb']),
                        'db_size_chroma_mb': float(row['db_size_chroma_mb'])
                    })
                benchmark_state["results"] = results
                logger.info(f"✅ Loaded {len(results)} result rows")
        else:
            logger.error(f"❌ Results file not found at {output_file}")
            benchmark_state["status"] = "failed"
            benchmark_state["error"] = f"Results file not found: {output_file}"
            return

        # Mark as completed
        benchmark_state["status"] = "completed"
        benchmark_state["completed_at"] = datetime.utcnow().isoformat()
        logger.info(f"✅ Benchmark {benchmark_id} completed successfully")

    except Exception as e:
        logger.exception(f"❌ Benchmark {benchmark_id} failed with exception:")
        benchmark_state["status"] = "failed"
        benchmark_state["error"] = str(e)


@router.get("/stream/{benchmark_id}")
async def stream_benchmark(benchmark_id: str):
    """
    SSE endpoint that streams benchmark progress in real-time

    Clients connect to this endpoint to receive live updates
    """
    logger.info(f"📡 SSE stream requested for benchmark {benchmark_id}")
    if benchmark_id not in active_benchmarks:
        logger.warning(f"⚠️  Benchmark {benchmark_id} not found")
        raise HTTPException(status_code=404, detail="Benchmark not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generator that yields SSE events"""
        last_progress = -1
        last_sub_progress = -1.0
        last_message = ""
        first_event = True

        while True:
            benchmark_state = active_benchmarks.get(benchmark_id)

            if not benchmark_state:
                break

            # Send update if progress or sub-progress changed
            current_progress = benchmark_state.get("current_progress", 0)
            current_sub_progress = benchmark_state.get("sub_progress", 0.0)
            current_message = benchmark_state.get("last_message", "")

            # WICHTIG: Sende sofort den aktuellen State beim ersten Connect (auch wenn 0)
            # oder wenn sich Progress, Sub-Progress oder Message geändert hat
            if (first_event or
                current_progress != last_progress or
                current_sub_progress != last_sub_progress or
                current_message != last_message):

                first_event = False

                data = {
                    "benchmark_id": benchmark_id,
                    "status": benchmark_state["status"],
                    "progress": current_progress,
                    "total": benchmark_state.get("total_runs", 0),
                    "sub_progress": current_sub_progress,
                    "overall_progress_pct": benchmark_state.get("overall_progress_pct", 0),
                    "phase": benchmark_state.get("phase", ""),
                    "last_message": current_message,
                    "timestamp": datetime.utcnow().isoformat()
                }

                yield f"data: {json.dumps(data)}\n\n"
                last_progress = current_progress
                last_sub_progress = current_sub_progress
                last_message = current_message

            # Check if completed
            if benchmark_state["status"] in ["completed", "failed"]:
                # Send final event WITHOUT results (results are fetched via /status endpoint)
                # This prevents SSE messages from becoming too large with big APIs
                final_data = {
                    'benchmark_id': benchmark_id,
                    'status': benchmark_state['status'],
                    'progress': benchmark_state.get('current_progress', 0),
                    'total': benchmark_state.get('total_runs', 0),
                    'last_message': 'Benchmark finished',
                    'timestamp': datetime.utcnow().isoformat(),
                    'message': 'Benchmark finished'
                    # results NOT included - client should fetch via GET /status/{benchmark_id}
                }
                yield f"data: {json.dumps(final_data)}\n\n"
                break

            # Wait before next check
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get("/status/{benchmark_id}")
async def get_benchmark_status(benchmark_id: str):
    """Get current status of a benchmark"""
    if benchmark_id not in active_benchmarks:
        raise HTTPException(status_code=404, detail="Benchmark not found")

    return active_benchmarks[benchmark_id]
