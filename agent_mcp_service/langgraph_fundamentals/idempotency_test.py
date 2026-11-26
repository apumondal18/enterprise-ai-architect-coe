import hashlib
import json

processed_payments = {}


def get_payload_hash(order_id, amount):
    payload = {
        "order_id": order_id,
        "amount": amount
    }

    serialized = json.dumps(
        payload,
        sort_keys=True
    )

    return hashlib.sha256(
        serialized.encode()
    ).hexdigest()


def process_payment(order_id, amount, idempotency_key):

    payload_hash = get_payload_hash(order_id, amount)

    if idempotency_key in processed_payments:

        existing = processed_payments[idempotency_key]

        if existing["payload_hash"] != payload_hash:
            raise ValueError(
                "Idempotency key reused with different parameters"
            )

        print("Duplicate request. Returning original result.")
        return existing["result"]

    print(f"Processing payment: ₹{amount}")

    result = {
        "order_id": order_id,
        "amount": amount,
        "status": "success"
    }

    processed_payments[idempotency_key] = {
        "payload_hash": payload_hash,
        "result": result
    }

    return result


key = "payment-ORDER-1001"

print(process_payment("ORDER-1001", 5000, key))

# Same key, same payload
print(process_payment("ORDER-1001", 5000, key))

# Same key, different payload
print(process_payment("ORDER-1001", 8000, key))
