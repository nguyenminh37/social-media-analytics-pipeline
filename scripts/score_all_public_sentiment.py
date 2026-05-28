#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import time

DEFAULT_NAMESPACE = "social-media-analytics"
DEFAULT_DEPLOYMENT = "deploy/social-media-sentiment-enricher"


def count_unscored(namespace: str, mongo_deployment: str) -> int:
    script = """db.public_content_events.countDocuments({$or:[{sentiment_model: {$exists:false}}, {sentiment_model:null}]})"""
    result = subprocess.run(
        [
            "kubectl",
            "exec",
            "-n",
            namespace,
            mongo_deployment,
            "--",
            "mongosh",
            "analytics",
            "--quiet",
            "--eval",
            f"print({script})",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return int(result.stdout.strip().splitlines()[-1])


def run_enricher_once(namespace: str, deployment: str) -> int:
    code = "from ai_insights.sentiment_enricher import run_once; print(run_once())"
    result = subprocess.run(
        [
            "kubectl",
            "exec",
            "-n",
            namespace,
            deployment,
            "--",
            "python",
            "-c",
            code,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return int(result.stdout.strip().splitlines()[-1])


def main() -> int:
    parser = argparse.ArgumentParser(description="Score all public demo content sentiment in Kubernetes.")
    parser.add_argument("--namespace", default=DEFAULT_NAMESPACE)
    parser.add_argument("--deployment", default=DEFAULT_DEPLOYMENT)
    parser.add_argument("--mongo-deployment", default="deploy/social-media-mongodb")
    parser.add_argument("--sleep", type=float, default=0.5)
    parser.add_argument("--max-iterations", type=int, default=20)
    args = parser.parse_args()

    for iteration in range(1, args.max_iterations + 1):
        remaining = count_unscored(args.namespace, args.mongo_deployment)
        print(f"iteration={iteration} remaining={remaining}")
        if remaining == 0:
            return 0
        scored = run_enricher_once(args.namespace, args.deployment)
        print(f"iteration={iteration} scored={scored}")
        if scored == 0:
            return 1
        time.sleep(args.sleep)

    return 1 if count_unscored(args.namespace, args.mongo_deployment) else 0


if __name__ == "__main__":
    raise SystemExit(main())
