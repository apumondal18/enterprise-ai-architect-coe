import sqlite3
import json
from datetime import datetime, timezone
import time
import threading
from concurrent.futures import ThreadPoolExecutor


DB_NAME = "payment_operations.db"


def get_connection():
    return sqlite3.connect(
        DB_NAME,
        timeout=10
    )


def run_concurrent_test():
    print("\n--- Concurrent idempotency test ---")

    gateway = SimulatedPaymentGateway()

    barrier = threading.Barrier(2)

    def make_request(request_name):
        print(f"{request_name}: Ready")

        # Both threads wait here until both are ready
        #barrier.wait()

        print(f"{request_name}: Sending payment request")

        try:
            result = create_payment(
                gateway,
                "PAY-ORD-5001",
                "ORD-5001",
                7500,
                test_barrier=barrier
            )

            return result

        except Exception as e:
            return {"error": str(e)}

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(make_request, "Request A")
        future_b = executor.submit(make_request, "Request B")

        result_a = future_a.result()
        result_b = future_b.result()

    print("\nRequest A result:", result_a)
    print("Request B result:", result_b)

    print(
        "\nGateway transaction count:",
        gateway.get_charge_count()
    )

def initialize_database():

    with get_connection() as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS payment_operations (

                idempotency_key TEXT PRIMARY KEY,

                order_id TEXT NOT NULL,

                amount REAL NOT NULL,

                status TEXT NOT NULL,

                gateway_payment_id TEXT,

                response TEXT,

                created_at TEXT NOT NULL,

                updated_at TEXT NOT NULL

            )
        """)

    print("Payment database initialized.")

'''
class SimulatedPaymentGateway:

    def __init__(self):
        self.transactions = {}
        self.charge_count = 0

    def charge(self, idempotency_key, order_id, amount):

        # Gateway-side duplicate protection
        if idempotency_key in self.transactions:
            print("Gateway: Existing transaction found.")
            return self.transactions[idempotency_key]

        self.charge_count += 1

        payment_result = {
            "payment_id": f"TXN-{self.charge_count}",
            "order_id": order_id,
            "amount": amount,
            "status": "SUCCESS"
        }

        self.transactions[idempotency_key] = payment_result

        print("Gateway: Payment successfully processed.")

        return payment_result

    def get_payment_status(self, idempotency_key):

        return self.transactions.get(idempotency_key)
'''


class SimulatedPaymentGateway:

    def __init__(self):
        self.db_name = "gateway_transactions.db"

        with sqlite3.connect(self.db_name) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS gateway_transactions (
                    idempotency_key TEXT PRIMARY KEY,
                    payment_id TEXT NOT NULL,
                    order_id TEXT NOT NULL,
                    amount REAL NOT NULL,
                    status TEXT NOT NULL
                )
            """)

    def charge(self, idempotency_key, order_id, amount):

        with sqlite3.connect(self.db_name) as conn:

            existing = conn.execute("""
                SELECT payment_id, order_id, amount, status
                FROM gateway_transactions
                WHERE idempotency_key = ?
            """, (idempotency_key,)).fetchone()

            if existing:
                print("Gateway: Existing transaction found.")

                return {
                    "payment_id": existing[0],
                    "order_id": existing[1],
                    "amount": existing[2],
                    "status": existing[3]
                }

            payment_id = f"TXN-{datetime.now(timezone.utc).timestamp()}"

            conn.execute("""
                INSERT INTO gateway_transactions
                VALUES (?, ?, ?, ?, ?)
            """, (
                idempotency_key,
                payment_id,
                order_id,
                amount,
                "SUCCESS"
            ))

            print("Gateway: Payment successfully processed.")

            return {
                "payment_id": payment_id,
                "order_id": order_id,
                "amount": amount,
                "status": "SUCCESS"
            }

    def get_payment_status(self, idempotency_key):

        with sqlite3.connect(self.db_name) as conn:

            result = conn.execute("""
                SELECT payment_id, order_id, amount, status
                FROM gateway_transactions
                WHERE idempotency_key = ?
            """, (idempotency_key,)).fetchone()

        if result is None:
            return None

        return {
            "payment_id": result[0],
            "order_id": result[1],
            "amount": result[2],
            "status": result[3]
        }

    def get_charge_count(self):
        with sqlite3.connect(self.db_name) as conn:
            result = conn.execute("""SELECT COUNT(*) FROM gateway_transactions""").fetchone()
        return result[0]

'''
def create_payment(
    gateway,
    idempotency_key,
    order_id,
    amount,
    simulate_crash=False,
    simulate_timeout=False,
    test_barrier=None
):
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:

        # Step 1: Check for an existing operation
        existing = conn.execute(
            """
            SELECT order_id, amount, status, response
            FROM payment_operations
            WHERE idempotency_key = ?
            """,
            (idempotency_key,)
        ).fetchone()

        if existing:

            existing_order, existing_amount, status, response = existing

            # Step 2: Validate that the key is not reused
            # for a different logical operation
            if existing_order != order_id or existing_amount != amount:
                raise ValueError(
                    "Idempotency key reused with different payment details"
                )

            # Step 3: Return the previous successful result
            if status == "SUCCESS":
                print("Application: Returning stored payment result.")
                return json.loads(response)

            print(f"Application: Existing operation status: {status}")
            return {"status": status}


        # Step 4: Create the operation record
        conn.execute(
            """
            INSERT INTO payment_operations (
                idempotency_key,
                order_id,
                amount,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                idempotency_key,
                order_id,
                amount,
                "PENDING",
                now,
                now
            )
        )

    # Step 5: Call the external payment gateway
    result = gateway.charge(
        idempotency_key,
        order_id,
        amount
    )

    if simulate_crash:
        raise RuntimeError(
            "Simulated application crash after gateway success"
        )

    if simulate_timeout:
        raise TimeoutError(
            "Gateway response timed out after payment processing"
        )

    # Step 6: Persist the successful result
    with get_connection() as conn:

        conn.execute(
            """
            UPDATE payment_operations
            SET status = ?,
                gateway_payment_id = ?,
                response = ?,
                updated_at = ?
            WHERE idempotency_key = ?
            """,
            (
                result["status"],
                result["payment_id"],
                json.dumps(result),
                datetime.now(timezone.utc).isoformat(),
                idempotency_key
            )
        )

    return result
'''


def create_payment(
    gateway,
    idempotency_key,
    order_id,
    amount,
    simulate_crash=False,
    simulate_timeout=False,
    test_barrier=None
):
    now = datetime.now(timezone.utc).isoformat()

    # Test-only synchronization: make both requests arrive together
    if test_barrier is not None:
        test_barrier.wait()

    # Step 1: Atomically check and claim the operation
    with get_connection() as conn:

        conn.execute("BEGIN IMMEDIATE")

        existing = conn.execute(
            """
            SELECT order_id, amount, status, response
            FROM payment_operations
            WHERE idempotency_key = ?
            """,
            (idempotency_key,)
        ).fetchone()

        if existing:

            existing_order, existing_amount, status, response = existing

            if existing_order != order_id or existing_amount != amount:
                raise ValueError(
                    "Idempotency key reused with different payment details"
                )

            if status == "SUCCESS":
                print("Application: Returning stored payment result.")
                return json.loads(response)

            # Another request owns this PENDING operation
            print("Application: Another request is processing this payment.")

            is_owner = False

        else:

            conn.execute(
                """
                INSERT INTO payment_operations (
                    idempotency_key,
                    order_id,
                    amount,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    idempotency_key,
                    order_id,
                    amount,
                    "PENDING",
                    now,
                    now
                )
            )

            print("Application: Payment operation created.")
            is_owner = True

    # Step 2: Non-owner waits for the owner to finish
    if not is_owner:

        for _ in range(100):
            with get_connection() as conn:
                row = conn.execute(
                    """
                    SELECT status, response
                    FROM payment_operations
                    WHERE idempotency_key = ?
                    """,
                    (idempotency_key,)
                ).fetchone()

            if row and row[0] == "SUCCESS":
                print("Application: Returning completed concurrent result.")
                return json.loads(row[1])

            time.sleep(0.1)

        return {"status": "PENDING"}

    # Step 3: Only the owner calls the gateway
    result = gateway.charge(
        idempotency_key,
        order_id,
        amount
    )

    if simulate_crash:
        raise RuntimeError(
            "Simulated application crash after gateway success"
        )

    if simulate_timeout:
        raise TimeoutError(
            "Gateway response timed out after payment processing"
        )

    # Step 4: Persist the successful result
    with get_connection() as conn:

        conn.execute(
            """
            UPDATE payment_operations
            SET status = ?,
                gateway_payment_id = ?,
                response = ?,
                updated_at = ?
            WHERE idempotency_key = ?
            """,
            (
                result["status"],
                result["payment_id"],
                json.dumps(result),
                datetime.now(timezone.utc).isoformat(),
                idempotency_key
            )
        )

    return result


def recover_pending_payment(gateway, idempotency_key):

    # Step 1: Read the existing operation from SQLite
    with get_connection() as conn:

        record = conn.execute(
            """
            SELECT status
            FROM payment_operations
            WHERE idempotency_key = ?
            """,
            (idempotency_key,)
        ).fetchone()

    if record is None:
        raise ValueError("Payment operation not found")

    if record[0] == "SUCCESS":
        print("Recovery: Payment already completed.")
        return

    # Step 2: Query the original payment at the gateway
    print("Recovery: Checking gateway for original payment.")

    result = gateway.get_payment_status(idempotency_key)

    if result is None:
        print("Recovery: Gateway has no matching transaction.")
        return

    # Step 3: Update the local database
    with get_connection() as conn:

        conn.execute(
            """
            UPDATE payment_operations
            SET status = ?,
                gateway_payment_id = ?,
                response = ?,
                updated_at = ?
            WHERE idempotency_key = ?
            """,
            (
                result["status"],
                result["payment_id"],
                json.dumps(result),
                datetime.now(timezone.utc).isoformat(),
                idempotency_key
            )
        )

    print("Recovery: SQLite payment status updated.")


'''
#1
if __name__ == "__main__":

    initialize_database()

    gateway = SimulatedPaymentGateway()

    print("\n--- First payment request ---")

    result1 = create_payment(
        gateway,
        "PAY-ORD-1002",
        "ORD-1002",
        5001
    )

    print(result1)

    print("\n--- Duplicate payment request ---")

    result2 = create_payment(
        gateway,
        "PAY-ORD-1002",
        "ORD-1002",
        5001
    )

    print(result2)

    print("\nTotal gateway charges:", gateway.charge_count)

'''
'''
#2
if __name__ == "__main__":

    initialize_database()

    gateway = SimulatedPaymentGateway()

    print("\n--- First request: simulate crash ---")

    try:
        create_payment(
            gateway,
            "PAY-ORD-2001",
            "ORD-2001",
            7500,
            simulate_crash=True
        )
    except RuntimeError as error:
        print("Application crashed:", error)

    print("\nGateway status:")
    print(gateway.get_payment_status("PAY-ORD-2001"))

    print("\nSQLite status:")

    with get_connection() as conn:
        record = conn.execute(
            """
            SELECT idempotency_key, status
            FROM payment_operations
            WHERE idempotency_key = ?
            """,
            ("PAY-ORD-2001",)
        ).fetchone()

        print(record)

    print("\nTotal gateway charges:", gateway.charge_count)
'''

if __name__ == "__main__":

    initialize_database()

    gateway = SimulatedPaymentGateway()

    print("\n--- First request: simulate crash ---")
    
    try:
        create_payment(
                gateway,
                "PAY-ORD-2002",
                "ORD-2002",
                7500,
                simulate_crash=True
            )
    except RuntimeError as error:
        print("Application crashed:", error)

    print("\n--- Recovery worker ---")

    recover_pending_payment(
        gateway,
        "PAY-ORD-2002"
    )

    print("\n--- Final SQLite status ---")

    with get_connection() as conn:
        record = conn.execute(
            """
            SELECT idempotency_key, status, gateway_payment_id
            FROM payment_operations
            WHERE idempotency_key = ?
            """,
            ("PAY-ORD-2002",)
        ).fetchone()

        print(record)

    print("\nTotal gateway charges:", gateway.get_charge_count())

    print("\n--- Gateway-level idempotency test ---")

    gateway = SimulatedPaymentGateway()

    result = gateway.charge(
        idempotency_key="PAY-ORD-2002",
        order_id="ORD-2002",
        amount=7500
    )

    print("Gateway response:", result)
    print("Total gateway transactions:", gateway.get_charge_count())

    print("\n--- Timeout simulation ---")

    gateway = SimulatedPaymentGateway()

    try:
        create_payment(
            gateway,
            "PAY-ORD-3001",
            "ORD-3001",
            7500,
            simulate_timeout=True
        )

    except TimeoutError as e:
        print("Application:", e)


    print("\n--- Application DB status after timeout ---")

    # Check the application database for PAY-ORD-3001
    with get_connection() as conn:
        row = conn.execute("""
            SELECT idempotency_key, status, gateway_payment_id
            FROM payment_operations
            WHERE idempotency_key = ?
        """, ("PAY-ORD-3001",)).fetchone()

    print(row)


    print("\n--- Recovery after timeout ---")

    recover_pending_payment(
        gateway,
        "PAY-ORD-3001"
    )


    print("\n--- Client retry with same key ---")

    retry_result = create_payment(
        gateway,
        "PAY-ORD-3001",
        "ORD-3001",
        7500
    )

    print("Retry result:", retry_result)
    print("Gateway transaction:", gateway.get_payment_status("PAY-ORD-3001"))

    run_concurrent_test()