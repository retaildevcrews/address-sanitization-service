import time
from typing import Callable, List, Any

import concurrent.futures


class BatchExecutor:
    def __init__(self, func: Callable, num_threads: int, delay: float):
        self.func = func
        self.num_threads = num_threads
        self.delay = delay

    def execute(self, inputs: List[Any]) -> List[Any]:
        results = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.num_threads
        ) as executor:
            future_to_input = {
                executor.submit(self._delayed_execution, inp): inp for inp in inputs
            }
            for future in concurrent.futures.as_completed(future_to_input):
                result = future.result()
                results.append(result)
        return results

    def _delayed_execution(self, inp: Any) -> Any:
        time.sleep(self.delay)
        return self.func(inp)

    def execute_with_args(self, inputs: List[tuple]) -> List[Any]:
        results = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.num_threads
        ) as executor:
            future_to_input = {
                executor.submit(self._delayed_execution_with_args, *inp): inp for inp in inputs
            }
            for future in concurrent.futures.as_completed(future_to_input):
                result = future.result()
                results.append(result)
        return results

    def _delayed_execution_with_args(self, *args: Any) -> Any:
        time.sleep(self.delay)
        return self.func(*args)
