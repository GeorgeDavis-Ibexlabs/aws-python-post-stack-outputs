import logging
from os import environ
import json
import cfnresponse
import traceback
import time
import boto3
from botocore.config import Config

client_config = Config(
    retries = {
        'max_attempts': 0,
        'mode': 'standard'
    }
)

from utils.utils import Utils
from cost_explorer.cost_explorer import CostExplorer
from cloudformation_stack.cloudformation_stack import CloudFormationStack
from organizations.organizations import Organizations
from account.account import Account
from config_handler.config_handler import ConfigHandler
from jira_handler.jira_handler import JiraHandler

# Setting up the logging level from the environment variable `LOGLEVEL`.
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(environ['LOGLEVEL'] if 'LOGLEVEL' in environ.keys() else 'INFO')

# Setting up logging level specific to `botocore` from the environment variable `BOTOCORE_LOGLEVEL`.
if 'BOTOCORE_LOGLEVEL' in environ.keys():
    if environ['BOTOCORE_LOGLEVEL'] == 'DEBUG':    
        logger.info('Setting boto3 logging to DEBUG')
        boto3.set_stream_logger('') # Log everything on boto3 messages to stdout
    else:
        logger.info('Setting boto3 logging to ' + environ['BOTOCORE_LOGLEVEL'])
        boto3.set_stream_logger(level=logging._nameToLevel[environ['BOTOCORE_LOGLEVEL']]) # Log boto3 messages that match BOTOCORE_LOGLEVEL to stdout

costexplorer_client = boto3.client('ce', config=client_config)
cost_explorer = CostExplorer(logger=logger, costexplorer_client=costexplorer_client)

cloudformation_stack_client = boto3.client('cloudformation', config=client_config)
cloudformation_stack = CloudFormationStack(logger=logger, cloudformation_client=cloudformation_stack_client)

organizations_client = boto3.client('organizations', config=client_config)
organizations = Organizations(logger=logger, organizations_client=organizations_client)

account_client = boto3.client('account', config=client_config)
account = Account(logger=logger, account_client=account_client)

utils = Utils(logger=logger)
config_handler = ConfigHandler(logger=logger)
config = config_handler.get_combined_config()
jira = JiraHandler(logger=logger, config=config)

# post_http_request: Send a HTTP POST request to the `api_endpoint_url`, returns the HTTP response as dict.
def post_http_request(event: dict, context: dict, api_endpoint_url: str, http_body: str) -> dict:

    try:
        if 'ENDPOINT_TYPE' in environ.keys() and 'ENDPOINT_URL' in environ.keys():
            
            if 'API' in environ['ENDPOINT_TYPE'] and environ['ENDPOINT_URL']:

                logger.debug('API Endpoint URL - ' + str(environ['ENDPOINT_URL']))
                logger.debug('HTTP Request Body - ' + str(http_body))

                import urllib3
                http = urllib3.PoolManager()

                # encoded_msg = json.dumps(http_body).encode('utf-8')

                logger.debug('HTTP POST Request Body - ' + str(json.dumps(http_body)))

                resp = http.request('POST', api_endpoint_url, body=json.dumps(http_body))

                logger.debug('HTTP API Response - ' + str(resp.data.decode('utf-8')))

                responseData = {'statusCode': 200, 'body': str(resp.data.decode('utf-8'))}
                logger.debug('HTTP Response - ' + str(responseData))

                cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
                return responseData
            
            else:
                cfnresponse.send(event, context, cfnresponse.FAILED, {})                
        else:
            cfnresponse.send(event, context, cfnresponse.FAILED, {})

    except urllib3.exceptions.MaxRetryError as max_retry_err:
        logger.error('HTTP POST API Max Retries failed - ' + str(traceback.print_tb(max_retry_err.__traceback__)))
        cfnresponse.send(event, context, cfnresponse.FAILED, {})

    except Exception as e:
        logger.error('HTTP POST API Error - ' + str(traceback.print_tb(e.__traceback__)))
        cfnresponse.send(event, context, cfnresponse.FAILED, {})

# update_payload_with_aws_metadata: This method updates the HTTP request body with local metadata from the AWS Account, such as the Onboarding Stack ID, AWS Region and AWS Account ID where the onboarding stack was deployed. Returns a `dict` with the new HTTP payload.
def update_payload_with_aws_metadata(http_payload: dict) -> dict:

    logger.debug('Current HTTP Payload - ' + str(http_payload))

    http_payload.update({ 'StackId': environ['STACK_ID'] if 'STACK_ID' in environ.keys() else '' })
    http_payload.update({ 'Region': environ['REGION'] if 'REGION' in environ.keys() else '' })
    http_payload.update({ 'AWSAccountId': environ['AWS_ACCOUNT_ID'] if 'AWS_ACCOUNT_ID' in environ.keys() else '' })

    # Check if the account is an Organizations Account
    isOrganizationsAccount = str(organizations.check_organizations_account(account_id = environ['AWS_ACCOUNT_ID'])[0]) if 'AWS_ACCOUNT_ID' in environ.keys() else 'FatalError'
    http_payload.update({ 'IsOrganizationsAccount': isOrganizationsAccount })

    if organizations.check_organizations_account(account_id = environ['AWS_ACCOUNT_ID'])[0]:
        email_address = organizations.check_organizations_account(account_id = environ['AWS_ACCOUNT_ID'])[1]
        if '@' in email_address:
            http_payload.update({ 'EmailDomain': organizations.check_organizations_account(account_id = environ['AWS_ACCOUNT_ID'])[1].split('@')[1] })
        else:
            http_payload.update({ 'EmailDomain': organizations.check_organizations_account(account_id = environ['AWS_ACCOUNT_ID'])[1] })
    else:
        http_payload.update({ 'EmailDomain': str(account.get_aws_account_information()[1]) if account.get_aws_account_information()[0] else environ['ENDUSER_DOMAIN_NAME'] if 'ENDUSER_DOMAIN_NAME' in environ.keys() else '' })

    logger.debug('Final HTTP Payload - ' + str(http_payload))

    return http_payload
    
# lambda_handler: This script executes as a Custom Resource on the Onboarding CloudFormation stack, gathering required information related to the deployed stack and additional information required for the Well-Architected Framework Review (WAFR) and Foundational Technical Review (FTR). The script is executed if the stack was created, updated or removed.
def lambda_handler(event, context):

    logger.debug('Environment variables - ' + str(environ))

    # Create or Update Stack - The following section gets executed when the deployed stack is created or updated using AWS CloudFormation.
    if event['RequestType'] == 'Create' or event['RequestType'] == 'Update':

        logger.debug(str(event['RequestType']) + ' Stack Event - ' + str(event))

        if 'STACK_ID' in environ.keys():

            describe_stack_resources_response = cloudformation_stack_client.describe_stack_resources(
                StackName=environ['STACK_ID']
            )

            logger.debug('Describe Stack Resources Response - ' + str(describe_stack_resources_response))

            nested_stack_creation_in_progress = True
            nested_stack_creation_status_list = []
            nested_cloudformation_stack_count = 0

            # Loop to wait for all Nested CloudFormation Stacks to be created
            describe_stack_resources_response = cloudformation_stack_client.describe_stack_resources(
                StackName=environ['STACK_ID']
            )
            
            for nested_stack in describe_stack_resources_response['StackResources']:

                if nested_stack['ResourceType'] == 'AWS::CloudFormation::Stack':

                    nested_cloudformation_stack_count += 1
            
            logger.debug('Nested CloudFormation Total Stack(s) Count - ' + str(nested_cloudformation_stack_count))

            while nested_stack_creation_in_progress:

                for nested_stack in describe_stack_resources_response['StackResources']:

                    if nested_stack['ResourceType'] == 'AWS::CloudFormation::Stack' and nested_stack['ResourceStatus'] == 'CREATE_COMPLETE':

                        nested_stack_creation_status_list.append(True)

                logger.debug('Nested Stack(s) Creation Status List - ' + str(nested_cloudformation_stack_count))

                if len(nested_stack_creation_status_list) == nested_cloudformation_stack_count:
                    nested_stack_creation_in_progress = False
                else:
                    logger.debug('Retrying in 5 seconds...')
                    time.sleep(5)

            stack_outputs = {}
            stack_outputs.update({'Action': event['RequestType']})
            stack_outputs.update(update_payload_with_aws_metadata(http_payload = stack_outputs))
            stack_outputs.update({'ActiveAWSRegions': str(utils.convert_region_ids_to_region_names(regions_list=cost_explorer.get_active_regions_from_last_90_day_billing()))})
            stack_outputs.update({'ActiveAWSServices': str(cost_explorer.get_active_services_from_last_90_day_billing())})
            stack_outputs.update({'Monthly Recurring Revenue': str(cost_explorer.get_monthly_recurring_revenue_from_last_90_day_billing())})

            for nested_stack in describe_stack_resources_response['StackResources']:

                if nested_stack['ResourceType'] == 'AWS::CloudFormation::Stack':

                    logger.debug('Initial Stack Output(s) Dictionary - ' + str(stack_outputs))
                    
                    stack_outputs.update(cloudformation_stack.get_stack_outputs(stack_physical_resource_id = nested_stack['PhysicalResourceId']))

                    logger.debug('Final Stack Output(s) Dictionary - ' + str(stack_outputs))

            logger.debug('Nested CloudFormation Stack Outputs - ' + str(stack_outputs))
        
            # Calling `post_http_request` to share the HTTP payload with the hosted API.
            post_http_request(
                event=event,
                context=context,
                api_endpoint_url=environ['ENDPOINT_URL'],
                http_body=stack_outputs
            )

            if config["jira"]["enabled"]:

                jira.jira_create_issue(
                    issue_summary=str(stack_outputs["AWSAccountId"]) + " - " + str(stack_outputs["EmailDomain"]),
                    issue_desc=str(stack_outputs)
                )
            
        # Handling `cfnresponse` error response when `STACK_ID` for the nested parent stack cannot be found within the runtime environment variables. 
        else:
            logger.error(str(event['RequestType']) + '  Stack HTTP API Error - Environment variable `STACK_ID` not present.')
            cfnresponse.send(event, context, cfnresponse.FAILED, {})

    # Delete Stack - The following section gets executed when the deployed stack is deleted from AWS CloudFormation.
    elif event['RequestType'] == 'Delete':

        try:
            logger.debug('Delete Stack Event - ' + str(event))

            stack_outputs = {}
            stack_outputs.update({'Action': event['RequestType']})
            stack_outputs = update_payload_with_aws_metadata(http_payload = stack_outputs)
        
            post_http_request(
                event=event,
                context=context,
                api_endpoint_url=environ['ENDPOINT_URL'],
                http_body=stack_outputs
            )

        # Handling `cfnresponse` error response when the stack is deleted but there is an exception in calling the API. 
        except Exception as e:
            logger.error('Delete Stack HTTP API Error - ' + str(traceback.print_tb(e.__traceback__)))
            cfnresponse.send(event, context, cfnresponse.FAILED, {})