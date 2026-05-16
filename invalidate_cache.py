"""
invalidate_cache.py — Invalidates CloudFront cache after site updates.
Run: python invalidate_cache.py
"""

import boto3
import json
import uuid


def load_config():
    with open("config.json") as f:
        return json.load(f)


def invalidate(dist_id):
    cf = boto3.client("cloudfront")
    print(f"Creating invalidation for distribution: {dist_id}")
    response = cf.create_invalidation(
        DistributionId=dist_id,
        InvalidationBatch={
            "Paths": {"Quantity": 1, "Items": ["/*"]},
            "CallerReference": str(uuid.uuid4()),
        },
    )
    inv_id = response["Invalidation"]["Id"]
    status = response["Invalidation"]["Status"]
    print(f"  Invalidation ID : {inv_id}")
    print(f"  Status          : {status}")
    print("Cache invalidation submitted. Changes will propagate in ~1-2 minutes.")


def main():
    config = load_config()
    invalidate(config["distribution_id"])


if __name__ == "__main__":
    main()
