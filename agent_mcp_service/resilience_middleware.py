from enum import Enum
import asyncio
import random
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


class ErrorAction(Enum):
    RETRY = "retry"
    FAIL = "fail"


class ResilienceError(Exception):
    """Base exception for resilience middleware."""


class RetryableError(ResilienceError):
    """An error that may succeed if attempted again."""


class NonRetryableError(ResilienceError):
    """An error that should not be retried."""


class ToolTimeoutError(RetryableError):
    """A tool execution exceeded its allowed time."""

class OverallDeadlineExceeded(Exception):
    """The complete execution exceeded its deadline."""



class SimulatedHTTPError(Exception):

    def __init__(self, status_code, headers=None):
        super().__init__(f"HTTP {status_code}")

        self.status_code = status_code
        self.headers = headers or {}


def classify_error(error: Exception) -> ErrorAction:

    # 1. Our own custom exceptions
    if isinstance(error, RetryableError):
        return ErrorAction.RETRY

    if isinstance(error, NonRetryableError):
        return ErrorAction.FAIL

    # 2. Common network and timeout failures
    if isinstance(error, (TimeoutError, ConnectionError)):
        return ErrorAction.RETRY

    # 3. Extract HTTP status code
    status_code = getattr(error, "status_code", None)

    if status_code is None:
        response = getattr(error, "response", None)
        status_code = getattr(response, "status_code", None)

    # 4. Classify HTTP failures
    if status_code == 429:
        return ErrorAction.RETRY

    if status_code in (500, 502, 503, 504):
        return ErrorAction.RETRY

    # 5. Everything else defaults to non-retryable
    return ErrorAction.FAIL


def calculate_backoff(
    attempt: int,
    base_delay: float = 1,
    max_delay: float = 30
) -> float:

    exponential_delay = min(
        max_delay,
        base_delay * (2 ** (attempt - 1))
    )

    jitter = random.uniform(0, exponential_delay * 0.2)

    return min(max_delay, exponential_delay + jitter)


def get_retry_after(error: Exception) -> float | None:

    response = getattr(error, "response", None)

    headers = getattr(response, "headers", None)

    if headers is None:
        headers = getattr(error, "headers", None)

    if not headers:
        return None

    value = headers.get("Retry-After")

    if value is None:
        return None

    # Format 1: Retry-After: 10
    try:
        return max(0.0, float(value))
    except (ValueError, TypeError):
        pass

    # Format 2: Retry-After: HTTP date
    try:
        retry_time = parsedate_to_datetime(value)

        if retry_time.tzinfo is None:
            retry_time = retry_time.replace(tzinfo=timezone.utc)

        delay = (
            retry_time - datetime.now(timezone.utc)
        ).total_seconds()

        return max(0.0, delay)

    except (ValueError, TypeError, OverflowError):
        return None


'''
async def execute_with_retry(
    operation,
    max_retries: int = 3,
    base_delay: float = 1,
    max_delay: float = 30
):

    for attempt in range(max_retries + 1):

        try:
            logging.info(
                "Executing operation. Attempt %s",
                attempt + 1
            )

            result = await execute_with_timeout(
                operation,
                timeout=5
                )

            logging.info("Operation successful")

            return result

        except Exception as error:

            action = classify_error(error)

            # Non-retryable error
            if action == ErrorAction.FAIL:
                logging.error(
                    "Non-retryable error: %s",
                    error
                )
                raise

            # All attempts exhausted
            if attempt == max_retries:
                logging.error(
                    "Maximum retries exhausted: %s",
                    error
                )
                raise

            # Respect server Retry-After when valid
            retry_after = get_retry_after(error)

            if retry_after is not None:
                if retry_after > max_delay:
                    logging.error(
                        "Retry-After exceeds maximum allowed delay"
                    )
                    raise

                delay = retry_after

            else:
                delay = calculate_backoff(
                    attempt + 1,
                    base_delay,
                    max_delay
                )

            logging.warning(
                "Attempt %s failed: %s. Retrying in %.2f seconds",
                attempt + 1,
                error,
                delay
            )

            await asyncio.sleep(delay)
'''

async def execute_with_retry(
    operation,
    max_retries=3,
    base_delay=1,
    max_delay=30,
    per_attempt_timeout=5,
    deadline=None
):

    loop = asyncio.get_running_loop()

    for attempt in range(max_retries + 1):

        try:
            # Check the remaining overall execution time.
            if deadline is not None:
                remaining = deadline - loop.time()

                if remaining <= 0:
                    raise OverallDeadlineExceeded(
                        "Overall execution deadline exceeded"
                    )

                attempt_timeout = min(
                    per_attempt_timeout,
                    remaining
                )
            else:
                attempt_timeout = per_attempt_timeout

            logging.info(
                "Executing operation. Attempt %s",
                attempt + 1
            )

            result = await execute_with_timeout(
                operation,
                timeout=attempt_timeout
            )

            logging.info("Operation successful")
            return result

        except OverallDeadlineExceeded:
            # Do not retry or switch providers after the global deadline.
            raise

        except Exception as error:

            action = classify_error(error)

            if action == ErrorAction.FAIL:
                logging.error("Non-retryable error: %s", error)
                raise

            if attempt == max_retries:
                logging.error("Maximum retries exhausted: %s", error)
                raise

            retry_after = get_retry_after(error)

            if retry_after is not None:
                if retry_after > max_delay:
                    logging.error(
                        "Retry-After exceeds maximum allowed delay"
                    )
                    raise

                delay = retry_after
            else:
                delay = calculate_backoff(
                    attempt + 1,
                    base_delay,
                    max_delay
                )

            # Check whether the retry delay fits within the deadline.
            if deadline is not None:
                remaining = deadline - loop.time()

                if delay >= remaining:
                    raise OverallDeadlineExceeded(
                        "Insufficient time remaining for another retry"
                    ) from error

            logging.warning(
                "Attempt %s failed: %s. Retrying in %.2f seconds",
                attempt + 1,
                error,
                delay
            )

            await asyncio.sleep(delay)


async def execute_with_fallback(
    primary_operation,
    secondary_operation,
    primary_max_retries=2,
    secondary_max_retries=2,
    overall_timeout=20,
    per_attempt_timeout=5,
    base_delay=1,
    max_delay=30
):

    loop = asyncio.get_running_loop()
    deadline = loop.time() + overall_timeout

    try:
        async with asyncio.timeout_at(deadline):

            # =================================
            # PRIMARY MODEL
            # =================================

            try:
                logging.info("Trying primary model")

                return await execute_with_retry(
                    primary_operation,
                    max_retries=primary_max_retries,
                    base_delay=base_delay,
                    max_delay=max_delay,
                    per_attempt_timeout=per_attempt_timeout,
                    deadline=deadline
                )

            except OverallDeadlineExceeded:
                raise

            except Exception as primary_error:

                action = classify_error(primary_error)

                if action == ErrorAction.FAIL:
                    raise

                logging.warning(
                    "Primary model exhausted its retries. "
                    "Switching to secondary model."
                )

            # =================================
            # SECONDARY MODEL
            # =================================

            return await execute_with_retry(
                secondary_operation,
                max_retries=secondary_max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                per_attempt_timeout=per_attempt_timeout,
                deadline=deadline
            )

    except TimeoutError as error:

        logging.error(
            "Overall execution deadline exceeded: %s seconds",
            overall_timeout
        )

        raise TimeoutError(
            f"Model execution exceeded {overall_timeout} seconds"
        ) from error

async def execute_with_timeout(
    operation,
    timeout: float = 5
):
    try:
        return await asyncio.wait_for(
            operation(),
            timeout=timeout
        )

    except TimeoutError as error:
        logging.error(
            "Operation timed out after %s seconds",
            timeout
        )

        raise ToolTimeoutError(
            f"Tool execution exceeded {timeout} seconds"
        ) from error


'''
async def execute_with_fallback(
    primary_operation,
    secondary_operation,
    max_retries=2
):
    try:
        return await execute_with_retry(
            primary_operation,
            max_retries=max_retries
        )

    except Exception as primary_error:

        action = classify_error(primary_error)

        if action == ErrorAction.FAIL:
            raise

        logging.warning(
            "Primary model failed. Switching to secondary model."
        )

        return await execute_with_retry(
            secondary_operation,
            max_retries=max_retries
        )
'''
#simulations
'''        
attempt_count = 0


async def simulated_api_call():

    global attempt_count
    attempt_count += 1

    print(f"API attempt: {attempt_count}")

    if attempt_count <= 2:
        raise SimulatedHTTPError(500)

    return {
        "status": "success",
        "message": "API operation completed"
    }


async def test_http_500():

    global attempt_count
    attempt_count = 0

    result = await execute_with_retry(
        simulated_api_call,
        max_retries=3,
        base_delay=1,
        max_delay=5
    )

    print("Final result:", result)


#simulation2

attempt_count = 0


async def simulated_rate_limited_call():

    global attempt_count
    attempt_count += 1

    print(f"API attempt: {attempt_count}")

    if attempt_count == 1:
        raise SimulatedHTTPError(
            429,
            headers={"Retry-After": "4"}
        )

    return {
        "status": "success",
        "message": "Rate limit cleared"
    }


async def test_http_429():

    global attempt_count
    attempt_count = 0

    result = await execute_with_retry(
        simulated_rate_limited_call,
        max_retries=3,
        base_delay=1,
        max_delay=5
    )

    print("Final result:", result)
'''

primary_count = 0
secondary_count = 0


async def simulated_model_a():
    global primary_count
    primary_count += 1

    print(f"Model A attempt: {primary_count}")

    raise SimulatedHTTPError(503)


async def simulated_model_b():
    global secondary_count
    secondary_count += 1

    print(f"Model B attempt: {secondary_count}")

    return {
        "model": "B",
        "status": "success",
        "response": "Fallback model succeeded"
    }


async def test_fallback_success():

    global primary_count, secondary_count

    primary_count = 0
    secondary_count = 0

    result = await execute_with_fallback(
        primary_operation=simulated_model_a,
        secondary_operation=simulated_model_b,
        primary_max_retries=2,
        secondary_max_retries=2,
        overall_timeout=20,
        per_attempt_timeout=5
    )

    print("Final result:", result)

async def simulated_model_b_failure():
    global secondary_count
    secondary_count += 1

    print(f"Model B attempt: {secondary_count}")

    raise SimulatedHTTPError(503)


async def test_both_models_fail():

    global primary_count, secondary_count

    primary_count = 0
    secondary_count = 0

    try:
        await execute_with_fallback(
            primary_operation=simulated_model_a,
            secondary_operation=simulated_model_b_failure,
            primary_max_retries=2,
            secondary_max_retries=2,
            overall_timeout=20,
            per_attempt_timeout=5
        )

    except Exception as error:
        print("Final execution failed:", error)


async def slow_model_a():
    print("Model A started")
    await asyncio.sleep(10)
    return "Model A succeeded"


async def slow_model_b():
    print("Model B started")
    await asyncio.sleep(10)
    return "Model B succeeded"


async def test_overall_deadline():

    try:
        await execute_with_fallback(
            primary_operation=slow_model_a,
            secondary_operation=slow_model_b,
            primary_max_retries=2,
            secondary_max_retries=2,
            overall_timeout=3,
            per_attempt_timeout=5
        )

    except Exception as error:
        print("Final execution failed:", type(error).__name__, error)

async def simulated_invalid_model_a():
    print("Model A called")
    raise SimulatedHTTPError(400)


async def simulated_invalid_model_b():
    print("Model B called")
    return "Fallback success"


async def test_non_retryable_fallback():

    try:
        await execute_with_fallback(
            primary_operation=simulated_invalid_model_a,
            secondary_operation=simulated_invalid_model_b,
            primary_max_retries=2,
            secondary_max_retries=2,
            overall_timeout=20,
            per_attempt_timeout=5
        )

    except Exception as error:
        print("Final error:", error)

async def main():

    print("\n========== SCENARIO 1 ==========")
    await test_fallback_success()

    print("\n========== SCENARIO 2 ==========")
    await test_both_models_fail()

    print("\n========== SCENARIO 3 ==========")
    await test_overall_deadline()

    print("\n========== SCENARIO 4 ==========")
    await test_non_retryable_fallback()

#    print("\n========== HTTP 500 TEST ==========")
#    await test_http_500()

#    print("\n========== HTTP 429 TEST ==========")
#    await test_http_429()


if __name__ == "__main__":
    asyncio.run(main())