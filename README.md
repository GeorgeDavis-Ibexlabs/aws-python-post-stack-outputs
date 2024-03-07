# aws-python-post-stack-outputs

This project deploys an AWS CloudFormation template with an AWS Lambda Function, retrieving the `Outputs` of the parent stack and nested stacks within the parent stack and POST them as an HTTP Request to a pre-configured API Endpoint.

## Usage

#### Configuration

The `AWS::Lambda::Function` environment variables provide a way to pass the `ENDPOINT_TYPE` and `ENDPOINT_URL` parameters to the Python script.

#### Deployment

- Deploy the `main.yml` CloudFormation template.

#### Invocation

After successful deployment, the `AWS::CloudFormation::CustomResource` triggers the `PostCFNOutputToAPIEndpointLambda` AWS Lambda Function to fetch the `Outputs` of the parent stack and the nested stacks within the parent stack and post it to an API Endpoint, as an HTTP POST request.

### Re-use

- Copy the **Resources** section on the `main.yml` file into your CloudFormation template
- Deploy your CloudFormation template and watch your HTTP API requests log for the stack outputs in a `JSON` format

#### Sample HTTP Request Body:

```json
{
    "arn:aws:cloudformation:us-east-1:01234567890:stack/OriginalStack-NestedStack1-I3JAJ2163PJH/ed19d490-dcad-11ee-ba09-1218a851e869": {
        "NestedStackSampleOutput1": "ThisIsASampleOutput",
    },
    "arn:aws:cloudformation:us-east-1:01234567890:stack/OriginalStack-NestedStack2-W0MIFPUN0NMR/ed323e90-dcad-11ee-a73f-0a5494653c59": {
        "NestedStackSampleOutput2": "ThisIsASampleOutput"
    },
    "arn:aws:cloudformation:us-east-1:01234567890:stack/OriginalStack-NestedStack3-1JM5QKSXZDK19/ecfe5d50-dcad-11ee-aa87-0abb47055c87": {
        "NestedStackSampleOutput3": "ThisIsASampleOutput"
    },
    "StackId": "arn:aws:cloudformation:us-east-1:01234567890:stack/OriginalStack/eb30c940-dcad-11ee-b10c-0a7d03698b25",
    "Region": "us-east-1",
    "AWSAccountId": "01234567890"
}
```
