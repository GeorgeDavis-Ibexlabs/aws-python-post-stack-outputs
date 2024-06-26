import logging
from os import environ
import boto3
import json
import cfnresponse
import time
import traceback

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

cloudformation_client = boto3.client('cloudformation')

# get_stack_outputs: Retrieve CloudFormation Stack outputs from a specific stack using the stack physical resource ID, returns the specific stack outputs as `dict`.
def get_stack_outputs(stack_physical_resource_id: str) -> dict:
    describe_stacks_response = cloudformation_client.describe_stacks(
        StackName=stack_physical_resource_id
    )

    logger.debug('Describe Stack Response - ' + str(describe_stacks_response))

    stack_output = {}

    logger.debug(type(describe_stacks_response['Stacks'][0]))

    if 'Outputs' in describe_stacks_response['Stacks'][0]:

        for output in describe_stacks_response['Stacks'][0]['Outputs']:

            stack_output.update({ 
                output['OutputKey']: output['OutputValue']
            })

    logger.debug('Stack Output - ' + str(stack_output))

    return { stack_physical_resource_id: stack_output }  

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

# get_aws_account_information: Retrieves email address(es) mentioned in the AWS Account Settings as alternate contacts. Alternatively, it works double time as an FTR check, `ACOM-001: Configure AWS account contacts`. Returns a tuple of (bool, list), True if the request was successful and the list contains the unique email address(es) retrieved from the AWS Account.
def get_aws_account_information() -> tuple[bool, list]:

    try:
        account_client = boto3.client('account')

        alternate_contact_type = ['BILLING', 'OPERATIONS', 'SECURITY']
        email_addresses = []

        for contact_type in alternate_contact_type:

            alternate_contact_response = account_client.get_alternate_contact(
                AlternateContactType=contact_type
            )

            if 'AlternateContact' not in alternate_contact_response.keys():
                return False, None

            if 'EmailAddress' not in alternate_contact_response['AlternateContact'].keys():
                return False, None

            email_addresses.append(alternate_contact_response['AlternateContact']['EmailAddress'].split('@')[1])

        return True, list(set(email_addresses))
    
    except account_client.exceptions.ResourceNotFoundException as ResourceNotFoundException:
        logger.error('Resource Not Found Exception - ' + str(traceback.print_tb(ResourceNotFoundException.__traceback__)))
        return False, None
    
    except account_client.exceptions.AccessDeniedException as AccessDeniedException:
        logger.error('Access Denied Exception - ' + str(traceback.print_tb(AccessDeniedException.__traceback__)))
        return False, None

# check_organizations_account: Checks to see if the AWS Account is part of AWS Organizations. This is a recommended best practice in the Well-Architected Framework Review assessment. Returns a tuple (bool, str), True if the AWS account is part of AWS Organizations and the `str` would be the email address associated with the AWS Org account.
def check_organizations_account(account_id: str) -> tuple[bool, str]:

    try:
        organizations_client = boto3.client('organizations')

        response = organizations_client.describe_account(
            AccountId=account_id
        )

        if 'Account' not in response.keys():
            return False, None

        if 'Email' not in response['Account'].keys():
            return False, None

        return True, response['Account']['Email']
    
    except organizations_client.exceptions.AWSOrganizationsNotInUseException:
        return False, None
    
# update_payload_with_aws_metadata: This method updates the HTTP request body with local metadata from the AWS Account, such as the Onboarding Stack ID, AWS Region and AWS Account ID where the onboarding stack was deployed. Returns a `dict` with the new HTTP payload.
def update_payload_with_aws_metadata(http_payload: dict) -> dict:

    logger.debug('Current HTTP Payload - ' + str(http_payload))

    http_payload.update({ 'StackId': environ['STACK_ID'] if 'STACK_ID' in environ.keys() else '' })
    http_payload.update({ 'Region': environ['REGION'] if 'REGION' in environ.keys() else '' })
    http_payload.update({ 'AWSAccountId': environ['AWS_ACCOUNT_ID'] if 'AWS_ACCOUNT_ID' in environ.keys() else '' })

    # Check if the account is an Organizations Account
    isOrganizationsAccount = check_organizations_account(account_id = environ['AWS_ACCOUNT_ID'])[0] if 'AWS_ACCOUNT_ID' in environ.keys() else False
    http_payload.update({ 'IsOrganizationsAccount': isOrganizationsAccount })

    if check_organizations_account(account_id = environ['AWS_ACCOUNT_ID'])[0]:
        http_payload.update({ 'EmailDomain': check_organizations_account(account_id = environ['AWS_ACCOUNT_ID'])[1].split('@')[1] })
    else:
        http_payload.update({ 'EmailDomain': str(get_aws_account_information()[1]) if get_aws_account_information()[0] else environ['ENDUSER_DOMAIN_NAME'] if 'ENDUSER_DOMAIN_NAME' in environ.keys() else '' })

    logger.debug('Final HTTP Payload - ' + str(http_payload))

    return http_payload

# get_active_regions_from_last_90_day_billing: This method retrieves the active AWS regions from the last 90 days billing. Returns a `list` of active AWS regions.
def get_active_regions_from_last_90_day_billing() -> list:

    try:

        from datetime import datetime, timedelta
        costexplorer_client = boto3.client('ce')

        # query_start_date = datetime.now() - timedelta(days=14) # Gets the date from 14 days ago. The start date is inclusive in the query.
        query_start_date = (datetime.now().replace(day=1) - timedelta(days=88)).replace(day=1) # Gets the first date of the previous month. End date is exclusive of the query period.
        query_end_date = datetime.now() # Gets the last date of the previous month. End date is exclusive.

        billing_by_aws_region_response = costexplorer_client.get_cost_and_usage(
            TimePeriod={
                'Start': query_start_date.strftime('%Y-%m-%d'),
                'End': query_end_date.strftime('%Y-%m-%d')
            },
            Granularity='MONTHLY',
            Metrics=[
                'UnblendedCost',
            ],
            GroupBy=[
                {
                    'Type': 'DIMENSION',
                    'Key': 'REGION'
                },
            ]
        )

        logger.debug('Billing by AWS Region Response - ' + str(billing_by_aws_region_response))

        active_aws_regions = []
        excluded_billing_regions = ['global', 'NoRegion']

        for aws_region_results in billing_by_aws_region_response['ResultsByTime']:

            for aws_region_group in aws_region_results['Groups']:

                if float(aws_region_group['Metrics']['UnblendedCost']['Amount']).__ceil__() > 0:

                    logger.debug('Region-wise spend in ' + aws_region_group['Keys'][0] + ' is $' + aws_region_group['Metrics']['UnblendedCost']['Amount'] + aws_region_group['Metrics']['UnblendedCost']['Unit'])

                    if aws_region_group['Keys'][0] not in active_aws_regions:

                        active_aws_regions.append(aws_region_group['Keys'][0])

        for excluded_region in excluded_billing_regions:

            if excluded_region in active_aws_regions:

                logger.debug('Removed excluded billing region - ' + excluded_region + '.')
                active_aws_regions.remove(excluded_region)

        return active_aws_regions
    
    except Exception as e:
        logger.error('CUR grouped by AWS Region Results Error - ' + str(traceback.print_tb(e.__traceback__)))
        return []

# get_active_services_from_last_90_day_billing: This method retrieves the active AWS services from the last 90 days billing. Returns a `list` of active AWS services.
def get_active_services_from_last_90_day_billing() -> list:
        
    try:

        from datetime import datetime, timedelta
        costexplorer_client = boto3.client('ce')

        # query_start_date = datetime.now() - timedelta(days=14) # Gets the date from 14 days ago. The start date is inclusive in the query.
        query_start_date = (datetime.now().replace(day=1) - timedelta(days=88)).replace(day=1) # Gets the first date of the previous month. End date is exclusive of the query period.
        query_end_date = datetime.now() # Gets the last date of the previous month. End date is exclusive.

        billing_by_aws_service_response = costexplorer_client.get_cost_and_usage(
            TimePeriod={
                'Start': query_start_date.strftime('%Y-%m-%d'),
                'End': query_end_date.strftime('%Y-%m-%d')
            },
            Granularity='MONTHLY',
            Metrics=[
                'UnblendedCost',
            ],
            GroupBy=[
                {
                    'Type': 'DIMENSION',
                    'Key': 'SERVICE'
                },
            ]
        )

        logger.debug('Billing by AWS Service Response - ' + str(billing_by_aws_service_response))

        active_aws_services = []

        for aws_service_results in billing_by_aws_service_response['ResultsByTime']:

            for aws_service_group in aws_service_results['Groups']:

                if float(aws_service_group['Metrics']['UnblendedCost']['Amount']).__ceil__() > 0:

                    logger.debug('Service-wise spend in ' + aws_service_group['Keys'][0] + ' is $' + aws_service_group['Metrics']['UnblendedCost']['Amount'] + aws_service_group['Metrics']['UnblendedCost']['Unit'])

                    if aws_service_group['Keys'][0] not in active_aws_services:

                        active_aws_services.append(aws_service_group['Keys'][0])

        return active_aws_services

    except Exception as e:
        logger.error('CUR grouped by AWS Service Results Error - ' + str(traceback.print_tb(e.__traceback__)))
        return []

# lambda_handler: This script executes as a Custom Resource on the Onboarding CloudFormation stack, gathering required information related to the deployed stack and additional information required for the Well-Architected Framework Review (WAFR) and Foundational Technical Review (FTR). The script is executed if the stack was created, updated or removed.
def lambda_handler(event, context):

    logger.debug('Environment variables - ' + str(environ))

    # Create or Update Stack - The following section gets executed when the deployed stack is created or updated using AWS CloudFormation.
    if event['RequestType'] == 'Create' or event['RequestType'] == 'Update':

        logger.debug(str(event['RequestType']) + ' Stack Event - ' + str(event))

        if 'STACK_ID' in environ.keys():

            describe_stack_resources_response = cloudformation_client.describe_stack_resources(
                StackName=environ['STACK_ID']
            )

            logger.debug('Describe Stack Resources Response - ' + str(describe_stack_resources_response))

            nested_stack_creation_in_progress = True
            nested_stack_creation_status_list = []
            nested_cloudformation_stack_count = 0

            # Loop to wait for all Nested CloudFormation Stacks to be created
            describe_stack_resources_response = cloudformation_client.describe_stack_resources(
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
            stack_outputs.update({'ActiveAWSRegions': str(get_active_regions_from_last_90_day_billing())})
            stack_outputs.update({'ActiveAWSServices': str(get_active_services_from_last_90_day_billing())})

            for nested_stack in describe_stack_resources_response['StackResources']:

                if nested_stack['ResourceType'] == 'AWS::CloudFormation::Stack':

                    logger.debug('Initial Stack Output(s) Dictionary - ' + str(stack_outputs))
                    
                    stack_outputs.update(get_stack_outputs(stack_physical_resource_id = nested_stack['PhysicalResourceId']))

                    logger.debug('Final Stack Output(s) Dictionary - ' + str(stack_outputs))

            logger.debug('Nested CloudFormation Stack Outputs - ' + str(stack_outputs))
        
            # Calling `post_http_request` to share the HTTP payload with the hosted API.
            post_http_request(
                event=event,
                context=context,
                api_endpoint_url=environ['ENDPOINT_URL'],
                http_body=stack_outputs
            )
            
        # Handling `cfnresponse` error response when `STACK_ID` for the nested parent stack cannot be found within the runtime environment variables. 
        else:
            logger.error(str(event['RequestType']) + '  Stack HTTP API Error - ' + str(traceback.print_tb(e.__traceback__)))
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