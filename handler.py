import logging
import os
import boto3
import json
import cfnresponse
import time

logger = logging.getLogger(__name__)
logger.setLevel(os.environ['LOG_LEVEL'] if 'LOG_LEVEL' in os.environ.keys() else 'INFO')

cloudformation_client = boto3.client('cloudformation')

def get_stack_outputs(stack_physical_resource_id: str) -> dict:
    describe_stacks_response = cloudformation_client.describe_stacks(
        StackName=stack_physical_resource_id
    )

    logger.debug("Describe Stack Response - " + str(describe_stacks_response))

    stack_output = {}

    logger.debug(type(describe_stacks_response["Stacks"][0]))

    if "Outputs" in describe_stacks_response["Stacks"][0]:

        for output in describe_stacks_response["Stacks"][0]["Outputs"]:

            stack_output.update({ 
                output["OutputKey"]: output["OutputValue"]
            })

    logger.debug("Stack Output - " + str(stack_output))

    return { stack_physical_resource_id: stack_output }  

def postApi(api_endpoint_url: str, http_body: str) -> dict:

    import urllib3
    http = urllib3.PoolManager()

    # encoded_msg = json.dumps(http_body).encode("utf-8")

    logger.debug("HTTP POST Request Body - " + str(json.dumps(http_body)))

    resp = http.request("POST", api_endpoint_url, body=json.dumps(http_body))

    logger.debug("HTTP API Response - " + str(resp.data.decode('utf-8')))
    return str(resp.data.decode('utf-8'))

def lambda_handler(event, context):

    logger.debug("Event - " + str(event))
    logger.debug("Environment variables - " + str(os.environ))

    if 'STACK_ID' in os.environ.keys():

        describe_stack_resources_response = cloudformation_client.describe_stack_resources(
            StackName=os.environ['STACK_ID']
        )

        logger.debug("Describe Stack Resources Response - " + str(describe_stack_resources_response))

        nested_stack_creation_in_progress = True
        nested_stack_creation_status_list = []
        nested_cloudformation_stack_count = 0

        # Loop to wait for all Nested CloudFormation Stacks to be created
        describe_stack_resources_response = cloudformation_client.describe_stack_resources(
                StackName=os.environ['STACK_ID'] 
            )
        
        for nested_stack in describe_stack_resources_response["StackResources"]:

            if nested_stack["ResourceType"] == "AWS::CloudFormation::Stack":

                nested_cloudformation_stack_count += 1
        
        while nested_stack_creation_in_progress:

            for nested_stack in describe_stack_resources_response["StackResources"]:

                if nested_stack["ResourceType"] == "AWS::CloudFormation::Stack" and nested_stack["ResourceStatus"] == "CREATE_COMPLETE":

                    nested_stack_creation_status_list.append(True)

            if len(nested_stack_creation_status_list) == nested_cloudformation_stack_count:
                nested_stack_creation_in_progress = False
            else:
                logger.debug("Retrying in 5 seconds...")
                time.sleep(5)

        stack_outputs = {}

        for nested_stack in describe_stack_resources_response["StackResources"]:

            if nested_stack["ResourceType"] == "AWS::CloudFormation::Stack":
                
                stack_outputs.update(get_stack_outputs(stack_physical_resource_id = nested_stack["PhysicalResourceId"]))

                logger.debug("CloudFormation Stack Output - " + str(stack_outputs))

        stack_outputs.update({ 'StackId': os.environ['STACK_ID'] if 'STACK_ID' in os.environ.keys() else '' })
        stack_outputs.update({ 'Region': os.environ['REGION']if 'REGION' in os.environ.keys() else '' })
        stack_outputs.update({ 'AWSAccountId': os.environ['AWS_ACCOUNT_ID'] if 'AWS_ACCOUNT_ID' in os.environ.keys() else '' })

        logger.debug("Nested CloudFormation Stack Outputs - " + str(stack_outputs))
    
        if 'ENDPOINT_TYPE' in os.environ.keys() and 'ENDPOINT_URL' in os.environ.keys():
        
            if 'API' in os.environ['ENDPOINT_TYPE'] and os.environ['ENDPOINT_URL']:

                api_endpoint_url = os.environ['ENDPOINT_URL']

                logger.debug("API Endpoint URL - " + str(os.environ['ENDPOINT_URL']))
                logger.debug("HTTP Request Body - " + str(stack_outputs))
                
                body = postApi(
                    api_endpoint_url = api_endpoint_url,
                    http_body = stack_outputs,
                )

                responseData = {'statusCode': 200, 'body': str(body)}
                logger.debug("HTTP Response - " + str(responseData))

                cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
                return responseData
            
            else:
                cfnresponse.send(event, context, cfnresponse.FAILED, {})                
        else:
            cfnresponse.send(event, context, cfnresponse.FAILED, {})
    else:
        cfnresponse.send(event, context, cfnresponse.FAILED, {})