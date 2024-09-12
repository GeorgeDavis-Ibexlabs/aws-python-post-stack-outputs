import logging
import traceback
from boto3 import client

class Organizations:

    # Organizations Constructor
    # logger: Logger object
    #
    # Returns: Organizations object
    # Raises: None
    def __init__(self, logger: logging.Logger, organizations_client: client):
        
        self.logger = logger
        self.organizations_client = organizations_client

    # check_organizations_account: Checks to see if the AWS Account is part of AWS Organizations. This is a recommended best practice in the Well-Architected Framework Review assessment. Returns a tuple (bool, str), True if the AWS account is part of AWS Organizations and the `str` would be the email address associated with the AWS Org account.
    def check_organizations_account(self, account_id: str) -> tuple[bool, str]:

        try:
            response = self.organizations_client.describe_account(
                AccountId=account_id
            )

            if 'Account' not in response.keys():
                return False, ''

            if 'Email' not in response['Account'].keys():
                return False, ''

            return True, response['Account']['Email']
        
        except self.organizations_client.exceptions.AccessDeniedException as AccessDeniedException:
            self.logger.error('Access Denied Exception - ' + str(traceback.print_tb(AccessDeniedException.__traceback__)))
            return True, "Access Denied"
        except self.organizations_client.exceptions.AWSOrganizationsNotInUseException as AWSOrganizationsNotInUseException:
            self.logger.error('AWS Organizations Not In Use Exception - ' + str(traceback.print_tb(AWSOrganizationsNotInUseException.__traceback__)))
            return False, ''