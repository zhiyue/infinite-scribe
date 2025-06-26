from prefect import flow, task
import time
from datetime import datetime

@task
def say_hello(name: str) -> str:
    message = f"Hello {name}! Current time: {datetime.now()}"
    print(message)
    return message

@task
def process_data(data: str) -> str:
    time.sleep(2)  # Simulate processing
    result = f"Processed: {data.upper()}"
    print(result)
    return result

@flow(name="example-flow")
def example_workflow(name: str = "InfiniteScribe"):
    # Task 1: Greeting
    greeting = say_hello(name)
    
    # Task 2: Process the greeting
    processed = process_data(greeting)
    
    return processed

if __name__ == "__main__":
    # Local test
    result = example_workflow()
    print(f"Flow completed with result: {result}")