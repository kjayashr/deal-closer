#!/usr/bin/env python3
"""
Performance Benchmarking Script for DealCloser

Measures actual performance metrics:
- p50, p95, p99 latency
- Cache hit rates (exact + semantic)
- Reconcile rates
- Per-step latency breakdown

Usage:
    python benchmark_performance.py --requests 100 --url http://localhost:8000
"""
import asyncio
import aiohttp
import time
import json
import argparse
import statistics
from typing import List, Dict, Any
from collections import defaultdict


class PerformanceBenchmark:
    """Benchmark performance of DealCloser API."""
    
    def __init__(self, base_url: str, num_requests: int = 100):
        self.base_url = base_url.rstrip('/')
        self.num_requests = num_requests
        self.results: List[Dict[str, Any]] = []
        self.cache_stats = {
            "exact_hits": 0,
            "semantic_hits": 0,
            "misses": 0,
            "total": 0
        }
        self.reconcile_stats = {
            "total_requests": 0,
            "reconciles": 0,
            "reconcile_rate": 0.0
        }
    
    async def make_request(
        self, 
        session: aiohttp.ClientSession,
        message: str,
        session_id: str,
        product_context: Dict = None
    ) -> Dict[str, Any]:
        """Make a single API request and measure latency."""
        start_time = time.time()
        
        payload = {
            "session_id": session_id,
            "message": message,
            "product_context": product_context or {"name": "TestProduct", "price": 100}
        }
        
        try:
            async with session.post(
                f"{self.base_url}/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                latency_ms = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Extract metrics from response
                    agent_dashboard = data.get("agent_dashboard", {})
                    system_info = agent_dashboard.get("system", {})
                    step_latencies = system_info.get("step_latencies", {})
                    
                    # Track cache hits
                    cache_hit = agent_dashboard.get("cache_hit", False)
                    cache_type = agent_dashboard.get("cache_type")
                    if cache_hit:
                        if cache_type == "exact":
                            self.cache_stats["exact_hits"] += 1
                        elif cache_type == "semantic":
                            self.cache_stats["semantic_hits"] += 1
                    else:
                        self.cache_stats["misses"] += 1
                    self.cache_stats["total"] += 1
                    
                    return {
                        "latency_ms": latency_ms,
                        "status": "success",
                        "cache_hit": cache_hit,
                        "cache_type": cache_type,
                        "step_latencies": step_latencies,
                        "reconcile_triggered": step_latencies.get("reconcile_triggered", False)
                    }
                else:
                    return {
                        "latency_ms": latency_ms,
                        "status": "error",
                        "status_code": response.status
                    }
        except asyncio.TimeoutError:
            return {
                "latency_ms": (time.time() - start_time) * 1000,
                "status": "timeout"
            }
        except Exception as e:
            return {
                "latency_ms": (time.time() - start_time) * 1000,
                "status": "error",
                "error": str(e)
            }
    
    def generate_test_messages(self) -> List[str]:
        """Generate diverse test messages for benchmarking."""
        return [
            "This product is too expensive",
            "I need something for my back pain",
            "Can you tell me more about the warranty?",
            "I'm just browsing today",
            "What's the return policy?",
            "This looks good but I need to think about it",
            "How fast can I get this delivered?",
            "Is there a discount available?",
            "I'm comparing this with another product",
            "My budget is limited right now",
            "This seems perfect for my needs",
            "Can you show me something cheaper?",
            "I'm worried about the quality",
            "What makes this better than the competition?",
            "I'll take it! How do I pay?",
        ]
    
    async def run_benchmark(self) -> Dict[str, Any]:
        """Run the full benchmark suite."""
        print(f"🚀 Starting benchmark: {self.num_requests} requests to {self.base_url}")
        print(f"   Test messages will be reused to test caching")
        print()
        
        test_messages = self.generate_test_messages()
        request_count = 0
        
        async with aiohttp.ClientSession() as session:
            # First, warm up with a few requests (don't count these)
            print("🔥 Warming up (5 requests)...")
            for _ in range(5):
                msg = test_messages[0]
                await self.make_request(session, msg, f"warmup-{_}")
            print("   Warmup complete\n")
            
            # Run benchmark requests
            print(f"📊 Running benchmark ({self.num_requests} requests)...")
            start_time = time.time()
            
            tasks = []
            for i in range(self.num_requests):
                msg = test_messages[i % len(test_messages)]  # Cycle through messages
                session_id = f"benchmark-{i // len(test_messages)}"
                tasks.append(self.make_request(session, msg, session_id))
                
                # Batch requests to avoid overwhelming the server
                if len(tasks) >= 10:
                    results = await asyncio.gather(*tasks)
                    self.results.extend(results)
                    request_count += len(tasks)
                    print(f"   Completed {request_count}/{self.num_requests} requests...", end='\r')
                    tasks = []
            
            # Process remaining tasks
            if tasks:
                results = await asyncio.gather(*tasks)
                self.results.extend(results)
            
            total_time = time.time() - start_time
            print(f"   Completed {len(self.results)}/{self.num_requests} requests")
            print(f"   Total time: {total_time:.2f}s")
            print()
        
        # Calculate statistics
        return self.calculate_stats(total_time)
    
    def calculate_stats(self, total_time: float) -> Dict[str, Any]:
        """Calculate performance statistics."""
        successful_results = [r for r in self.results if r["status"] == "success"]
        
        if not successful_results:
            return {
                "error": "No successful requests",
                "results": self.results
            }
        
        latencies = [r["latency_ms"] for r in successful_results]
        latencies_sorted = sorted(latencies)
        
        # Percentiles
        p50 = latencies_sorted[len(latencies_sorted) // 2]
        p95 = latencies_sorted[int(len(latencies_sorted) * 0.95)]
        p99 = latencies_sorted[int(len(latencies_sorted) * 0.99)]
        
        # Cache statistics
        total_requests = len(successful_results)
        exact_hits = sum(1 for r in successful_results if r.get("cache_type") == "exact")
        semantic_hits = sum(1 for r in successful_results if r.get("cache_type") == "semantic")
        cache_misses = total_requests - exact_hits - semantic_hits
        total_hits = exact_hits + semantic_hits
        cache_hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0
        
        # Reconcile statistics
        reconcile_triggered = sum(1 for r in successful_results if r.get("reconcile_triggered", False))
        reconcile_rate = (reconcile_triggered / total_requests * 100) if total_requests > 0 else 0
        
        # Per-step latency breakdown (average)
        step_latencies_avg = defaultdict(list)
        for r in successful_results:
            step_lats = r.get("step_latencies", {})
            for step, latency in step_lats.items():
                if isinstance(latency, (int, float)):
                    step_latencies_avg[step].append(latency)
        
        step_latencies_avg = {
            step: statistics.mean(latencies) if latencies else 0
            for step, latencies in step_latencies_avg.items()
        }
        
        # Throughput
        throughput = len(successful_results) / total_time if total_time > 0 else 0
        
        return {
            "summary": {
                "total_requests": len(self.results),
                "successful_requests": len(successful_results),
                "failed_requests": len(self.results) - len(successful_results),
                "total_time_seconds": total_time,
                "throughput_req_per_sec": throughput
            },
            "latency_percentiles": {
                "p50_ms": round(p50, 2),
                "p95_ms": round(p95, 2),
                "p99_ms": round(p99, 2),
                "mean_ms": round(statistics.mean(latencies), 2),
                "min_ms": round(min(latencies), 2),
                "max_ms": round(max(latencies), 2)
            },
            "cache_statistics": {
                "exact_hits": exact_hits,
                "semantic_hits": semantic_hits,
                "cache_misses": cache_misses,
                "total_requests": total_requests,
                "cache_hit_rate_percent": round(cache_hit_rate, 2)
            },
            "reconcile_statistics": {
                "total_requests": total_requests,
                "reconciles": reconcile_triggered,
                "reconcile_rate_percent": round(reconcile_rate, 2)
            },
            "step_latencies_avg_ms": step_latencies_avg,
            "target_metrics": {
                "p95_latency_target_ms": 175,
                "cache_hit_rate_target_percent": "25-30",
                "reconcile_rate_target_percent": "15-20"
            }
    }
    
    def print_results(self, stats: Dict[str, Any]):
        """Print benchmark results in a readable format."""
        print("=" * 70)
        print("📊 PERFORMANCE BENCHMARK RESULTS")
        print("=" * 70)
        print()
        
        # Summary
        summary = stats.get("summary", {})
        print("📈 Summary:")
        print(f"   Total Requests:      {summary.get('total_requests', 0)}")
        print(f"   Successful:          {summary.get('successful_requests', 0)}")
        print(f"   Failed:              {summary.get('failed_requests', 0)}")
        print(f"   Total Time:          {summary.get('total_time_seconds', 0):.2f}s")
        print(f"   Throughput:          {summary.get('throughput_req_per_sec', 0):.2f} req/s")
        print()
        
        # Latency percentiles
        latencies = stats.get("latency_percentiles", {})
        print("⚡ Latency Percentiles:")
        print(f"   p50:                 {latencies.get('p50_ms', 0):.2f}ms")
        print(f"   p95:                 {latencies.get('p95_ms', 0):.2f}ms")
        print(f"   p99:                 {latencies.get('p99_ms', 0):.2f}ms")
        print(f"   Mean:                {latencies.get('mean_ms', 0):.2f}ms")
        print(f"   Min:                 {latencies.get('min_ms', 0):.2f}ms")
        print(f"   Max:                 {latencies.get('max_ms', 0):.2f}ms")
        print()
        
        # Cache statistics
        cache = stats.get("cache_statistics", {})
        print("💾 Cache Statistics:")
        print(f"   Exact Hits:          {cache.get('exact_hits', 0)}")
        print(f"   Semantic Hits:       {cache.get('semantic_hits', 0)}")
        print(f"   Cache Misses:        {cache.get('cache_misses', 0)}")
        print(f"   Cache Hit Rate:      {cache.get('cache_hit_rate_percent', 0):.2f}%")
        print()
        
        # Reconcile statistics
        reconcile = stats.get("reconcile_statistics", {})
        print("🔄 Reconcile Statistics:")
        print(f"   Total Requests:      {reconcile.get('total_requests', 0)}")
        print(f"   Reconciles:          {reconcile.get('reconciles', 0)}")
        print(f"   Reconcile Rate:      {reconcile.get('reconcile_rate_percent', 0):.2f}%")
        print()
        
        # Step latencies
        step_lats = stats.get("step_latencies_avg_ms", {})
        if step_lats:
            print("🔍 Average Step Latencies:")
            for step, latency in sorted(step_lats.items()):
                if step.endswith("_ms") or "ms" in step.lower():
                    print(f"   {step:<25} {latency:.2f}ms")
                else:
                    print(f"   {step:<25} {latency:.2f}ms")
            print()
        
        # Target comparison
        targets = stats.get("target_metrics", {})
        p95_actual = latencies.get('p95_ms', 0)
        p95_target = targets.get('p95_latency_target_ms', 175)
        cache_actual = cache.get('cache_hit_rate_percent', 0)
        
        print("🎯 Target Comparison:")
        print(f"   p95 Latency:         {p95_actual:.2f}ms (target: <{p95_target}ms) {'✅' if p95_actual <= p95_target else '❌'}")
        print(f"   Cache Hit Rate:      {cache_actual:.2f}% (target: {targets.get('cache_hit_rate_target_percent', 'N/A')}%)")
        print(f"   Reconcile Rate:      {reconcile.get('reconcile_rate_percent', 0):.2f}% (target: {targets.get('reconcile_rate_target_percent', 'N/A')}%)")
        print()
        
        print("=" * 70)


async def main():
    parser = argparse.ArgumentParser(description="Benchmark DealCloser API performance")
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000",
        help="Base URL of the API (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=100,
        help="Number of requests to make (default: 100)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path for JSON results (optional)"
    )
    
    args = parser.parse_args()
    
    benchmark = PerformanceBenchmark(args.url, args.requests)
    stats = await benchmark.run_benchmark()
    
    benchmark.print_results(stats)
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(stats, f, indent=2)
        print(f"📄 Results saved to: {args.output}")


if __name__ == "__main__":
    asyncio.run(main())

