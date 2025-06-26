from prefect import serve
from example_flow import example_workflow

if __name__ == "__main__":
    # Deploy the flow
    deployment = example_workflow.to_deployment(
        name="example-deployment",
        work_pool_name="default-pool"
    )
    
    # Serve the deployment
    serve(deployment)