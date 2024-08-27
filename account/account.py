import logging
import traceback
from boto3 import client

class Account:

    # Account Constructor
    # logger: Logger object
    #
    # Returns: Account object
    # Raises: None
    def __init__(self, logger: logging.Logger, account_client: client):
        
        self.logger = logger
        self.account_client = account_client

    # get_aws_account_information: Retrieves email address(es) mentioned in the AWS Account Settings as alternate contacts. Alternatively, it works double time as an FTR check, `ACOM-001: Configure AWS account contacts`. Returns a tuple of (bool, list), True if the request was successful and the list contains the unique email address(es) retrieved from the AWS Account.
    def get_aws_account_information(self) -> tuple[bool, list]:

        try:

            alternate_contact_type = ['BILLING', 'OPERATIONS', 'SECURITY']
            email_domains = []

            for contact_type in alternate_contact_type:

                alternate_contact_response = self.account_client.get_alternate_contact(
                    AlternateContactType=contact_type
                )

                if 'AlternateContact' not in alternate_contact_response.keys():
                    return False, []

                if 'EmailAddress' not in alternate_contact_response['AlternateContact'].keys():
                    return False, []

                email_domains.append(alternate_contact_response['AlternateContact']['EmailAddress'].split('@')[1])

            return True, list(set(email_domains))
        
        except self.account_client.exceptions.ResourceNotFoundException as ResourceNotFoundException:
            self.logger.error('Resource Not Found Exception - ' + str(traceback.print_tb(ResourceNotFoundException.__traceback__)))
            return False, []
        
        except self.account_client.exceptions.AccessDeniedException as AccessDeniedException:
            self.logger.error('Access Denied Exception - ' + str(traceback.print_tb(AccessDeniedException.__traceback__)))
            return False, []